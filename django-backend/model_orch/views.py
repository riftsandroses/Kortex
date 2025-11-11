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
import json

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
        
        # Try multiple possible locations for label_mapping.json
        possible_paths = [
            # # Path from your example - adjust based on your actual model version
            # f"/home/utkarsh/Kortex/Django-backend/models/{mv.app.slug}/{mv.version}/model/label_mapping.json",
            # # Alternative path pattern
            # f"/home/utkarsh/Kortex/Django-backend/models/{mv.app.slug}/latest/model/label_mapping.json",
            # # Standard path structure
            os.path.join(MODEL_ROOT, mv.app.slug, 'latest', 'model', 'label_mapping.json'),
            os.path.join(MODEL_ROOT, mv.app.slug, mv.version, 'model', 'label_mapping.json'),
            os.path.join(MODEL_ROOT, mv.app.slug, 'latest', 'label_mapping.json'),
            os.path.join(MODEL_ROOT, mv.app.slug, mv.version, 'label_mapping.json'),
        ]
        
        categories = []
        found_path = None
        
        for path in possible_paths:
            try:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        label_mapping = json.load(f)
                    
                    # Extract categories based on the structure
                    if 'id2label' in label_mapping:
                        # Structure: {"id2label": {"0": "testing"}, "label2id": {"testing": 0}}
                        categories = list(label_mapping['id2label'].values())
                    elif 'label_mapping' in label_mapping:
                        # Alternative structure with label_mapping key
                        categories = list(label_mapping['label_mapping'].keys())
                    elif isinstance(label_mapping, dict):
                        # Flat structure: {"category1": "label1", "category2": "label2"}
                        categories = list(label_mapping.keys())
                    
                    found_path = path
                    logger.info(f"Found {len(categories)} categories from file: {path}")
                    break
                    
            except Exception as e:
                logger.warning(f"Failed to read label mapping from {path}: {str(e)}")
                continue
        
        # If no file found, fall back to database metrics field
        if not categories and mv.metrics:
            metrics = mv.metrics
            if metrics.get('id2label'):
                categories = list(metrics['id2label'].values())
            elif metrics.get('label_mapping'):
                categories = list(metrics['label_mapping'].keys())
            elif isinstance(metrics, dict):
                categories = list(metrics.keys())
            
            if categories:
                logger.info(f"Found {len(categories)} categories from database metrics field")
        
        return Response({
            'model_id': mv.id,
            'model_version': mv.version,
            'app_slug': mv.app.slug,
            'categories': categories,
            'categories_count': len(categories),
            'source': 'file' if found_path else 'database' if categories else 'none',
            'file_path': found_path
        })


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


# Category Debugger Code
# class ModelDebugAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request, model_id):
#         mv = get_object_or_404(ModelVersion, pk=model_id)
        
#         return Response({
#             'model_id': mv.id,
#             'version': mv.version,
#             'app_slug': mv.app.slug,
#             'metrics': mv.metrics,
#             'metrics_type': str(type(mv.metrics)),
#             'has_metrics': bool(mv.metrics),
#             'all_metrics_keys': list(mv.metrics.keys()) if mv.metrics else []
#         })