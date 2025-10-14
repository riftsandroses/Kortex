import logging
from django.shortcuts import get_object_or_404
from django.db.models import Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from django.utils import timezone

from .models import GuardrailApp, CapturedResponse, ModelVersion, TrainingJob
from .serializers import (
    GuardrailAppSerializer, CapturedResponseCreateSerializer, CapturedResponseSerializer,
    LabelResponseSerializer, ModelVersionSerializer, TrainingJobSerializer
)
from .tasks import async_evaluate_and_store, launch_training_job
from .permissions import IsOwnerOrReadOnly

logger = logging.getLogger(__name__)

# --- App management endpoints ---

class GuardrailAppListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = GuardrailApp.objects.all()
        serializer = GuardrailAppSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = GuardrailAppSerializer(data=request.data)
        if serializer.is_valid():
            app = serializer.save(owner=request.user)
            return Response(GuardrailAppSerializer(app).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GuardrailAppDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_object(self, slug):
        return get_object_or_404(GuardrailApp, slug=slug)

    def get(self, request, slug):
        app = self.get_object(slug)
        serializer = GuardrailAppSerializer(app)
        return Response(serializer.data)

    def patch(self, request, slug):
        app = self.get_object(slug)
        self.check_object_permissions(request, app)
        serializer = GuardrailAppSerializer(app, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- Ingest endpoint: capture LLM response before showing to user ---
class CaptureResponseAPIView(APIView):
    """
    Endpoint for LLM-integrated apps to POST response text before showing to end-user.
    This will store the response and trigger evaluation asynchronously (low-latency).
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = CapturedResponseCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        captured = serializer.save()
        # Kick off async evaluation (attempt low-latency inference)
        try:
            async_evaluate_and_store.delay(str(captured.id))
        except Exception as e:
            logger.exception("Failed to queue eval task")
        return Response(CapturedResponseSerializer(captured).data, status=status.HTTP_201_CREATED)

# --- Retrieve responses + labeling ---
class CapturedResponseListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CapturedResponseSerializer

    def get(self, request):
        qs = CapturedResponse.objects.select_related('app').all()
        # filtering
        app_slug = request.query_params.get('app')
        labeled = request.query_params.get('labeled')
        if app_slug:
            qs = qs.filter(app__slug=app_slug)
        if labeled in ('true', 'false'):
            qs = qs.filter(labeled=(labeled == 'true'))
        return qs

class CapturedResponseDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        obj = get_object_or_404(CapturedResponse, pk=pk)
        return Response(CapturedResponseSerializer(obj).data)

class LabelCapturedResponseAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        obj = get_object_or_404(CapturedResponse, pk=pk)
        ser = LabelResponseSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        data = ser.validated_data
        obj.label = data['label']
        obj.labeled = True
        obj.labeled_by = request.user
        obj.labeled_at = timezone.now()
        obj.action = data.get('action', obj.action)
        obj.save()
        return Response(CapturedResponseSerializer(obj).data)

# --- Training endpoints ---
class LaunchTrainingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        app = get_object_or_404(GuardrailApp, slug=slug)
        # create TrainingJob record
        tj = TrainingJob.objects.create(
            app=app,
            status='pending',
            initiated_by=request.user,
            params=request.data or {}
        )
        # enqueue training
        try:
            launch_training_job.delay(str(tj.id))
        except Exception:
            logger.exception("Failed to enqueue training job")
            tj.status = 'failed'
            tj.logs += '\nFailed to queue training task'
            tj.save()
            return Response({'detail': 'failed to queue training job'}, status=500)
        return Response(TrainingJobSerializer(tj).data, status=status.HTTP_202_ACCEPTED)

class TrainingJobListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = TrainingJob.objects.all().order_by('-created_at')
        serializer = TrainingJobSerializer(qs, many=True)
        return Response(serializer.data)

class TrainingJobDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        tj = get_object_or_404(TrainingJob, pk=pk)
        return Response(TrainingJobSerializer(tj).data)

# --- Dashboard / insights ---
class DashboardOverviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # aggregated metrics
        total_responses = CapturedResponse.objects.count()
        pending_labels = CapturedResponse.objects.filter(labeled=False).count()
        per_app = GuardrailApp.objects.annotate(total=Count('responses')).values('slug','name','total')
        latest_alerts = CapturedResponse.objects.filter(action='block').order_by('-captured_at')[:10]
        latest_alerts_ser = CapturedResponseSerializer(latest_alerts, many=True)
        return Response({
            'total_responses': total_responses,
            'pending_labels': pending_labels,
            'apps': list(per_app),
            'latest_blocked': latest_alerts_ser.data,
        })

class LabelDistributionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = CapturedResponse.objects.values('label').annotate(count=Count('label')).order_by('-count')
        return Response(list(qs))

class ModelPerformanceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        app = get_object_or_404(GuardrailApp, slug=slug)
        latest_version = app.model_versions.order_by('-created_at').first()
        if not latest_version:
            return Response({'detail': 'no model versions'}, status=404)
        return Response(latest_version.metrics or {})

# --- Endpoint to force-evaluate a stored response synchronously (admin use only) ---
class EvaluateCapturedResponseAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        obj = get_object_or_404(CapturedResponse, pk=pk)
        # synchronous evaluation (useful for manual testing / admin)
        from .ml.inference import evaluate_text_with_model
        try:
            label, score, action = evaluate_text_with_model(obj.app.slug, obj.response_text)
            obj.predicted_label = label
            obj.predicted_score = score
            obj.action = action
            obj.evaluated = True
            obj.save()
            return Response(CapturedResponseSerializer(obj).data)
        except Exception as e:
            logger.exception("Evaluation failed")
            return Response({'detail': 'evaluation failed'}, status=500)
