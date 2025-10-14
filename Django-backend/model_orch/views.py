from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.conf import settings
from guardrails.models import ModelVersion, GuardrailApp
from .models import ModelAssignment
from .serializers import (
    ModelVersionSerializer,
    AssignModelSerializer,
    ModelAssignmentSerializer
)
import shutil
import os
import logging

logger = logging.getLogger(__name__)
MODEL_ROOT = getattr(settings, 'GUARDRAILS_MODEL_ROOT', '/var/lib/kortex/guardrails_models')

class ModelVersionListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = ModelVersion.objects.select_related('app').all().order_by('-created_at')
        serializer = ModelVersionSerializer(qs, many=True)
        return Response(serializer.data)


class ModelCategoriesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, model_id):
        mv = get_object_or_404(ModelVersion, pk=model_id)
        categories = list(mv.metrics.get('label_mapping', {}).keys()) if mv.metrics.get('label_mapping') else []
        return Response({'model_id': mv.id, 'categories': categories})


class AssignModelAPIView(APIView):
    """
    Assign an existing trained model to another app and record the assignment.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, model_id):
        mv = get_object_or_404(ModelVersion, pk=model_id)
        serializer = AssignModelSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        target_app_slug = serializer.validated_data['target_app_slug']
        target_app = get_object_or_404(GuardrailApp, slug=target_app_slug)

        try:
            src_dir = os.path.join(MODEL_ROOT, mv.app.slug, 'latest')
            dst_dir = os.path.join(MODEL_ROOT, target_app.slug, 'latest')
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)

            target_app.current_model_version = mv.version
            target_app.save()

            assignment, created = ModelAssignment.objects.get_or_create(
                source_model=mv, target_app=target_app,
                defaults={'assigned_by': request.user}
            )

            return Response({
                'detail': f'Model {mv.version} assigned to app {target_app.slug}',
                'already_existed': not created
            })

        except Exception as e:
            logger.exception("Failed to assign model")
            return Response({'detail': str(e)}, status=500)


class ModelAssignmentListAPIView(APIView):
    """
    List all model assignments (history of which model was used where)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = ModelAssignment.objects.select_related('source_model', 'target_app', 'assigned_by')
        serializer = ModelAssignmentSerializer(qs, many=True)
        return Response(serializer.data)
