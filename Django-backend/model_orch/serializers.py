from rest_framework import serializers
from guardrails.models import ModelVersion
from .models import ModelAssignment

class ModelVersionSerializer(serializers.ModelSerializer):
    app_name = serializers.CharField(source='app.name', read_only=True)
    app_slug = serializers.CharField(source='app.slug', read_only=True)

    class Meta:
        model = ModelVersion
        fields = ['id', 'version', 'app_name', 'app_slug', 'metrics', 'model_files', 'created_at']

class AssignModelSerializer(serializers.Serializer):
    target_app_slug = serializers.SlugField()

class ModelAssignmentSerializer(serializers.ModelSerializer):
    source_model_version = serializers.CharField(source='source_model.version', read_only=True)
    source_app_slug = serializers.CharField(source='source_model.app.slug', read_only=True)
    target_app_slug = serializers.CharField(source='target_app.slug', read_only=True)
    assigned_by_username = serializers.CharField(source='assigned_by.username', read_only=True)

    class Meta:
        model = ModelAssignment
        fields = [
            'id', 'source_model_version', 'source_app_slug',
            'target_app_slug', 'assigned_by_username', 'assigned_at'
        ]
