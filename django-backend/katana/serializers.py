from rest_framework import serializers
from .models import (
    IntegratedApplication,
    ResponseCategory,
    LLMResponse,
    ModelVersion,
    TrainingJob,
    AnalyticsSnapshot,
    Alert
)
from django.contrib.auth import get_user_model

User = get_user_model()


class ResponseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponseCategory
        fields = [
            'id', 'name', 'category_type', 'description',
            'severity_level', 'should_block', 'is_global',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class IntegratedApplicationSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    total_responses = serializers.SerializerMethodField()
    categories_count = serializers.SerializerMethodField()

    class Meta:
        model = IntegratedApplication
        fields = [
            'id', 'name', 'description', 'api_key', 'owner', 'owner_email',
            'is_active', 'model_version', 'confidence_threshold',
            'auto_block_enabled', 'total_responses', 'categories_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'api_key', 'created_at', 'updated_at']
        extra_kwargs = {
            'owner': {'write_only': True}
        }

    def get_total_responses(self, obj):
        return obj.responses.count()

    def get_categories_count(self, obj):
        return obj.categories.count()


class IntegratedApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegratedApplication
        fields = [
            'name', 'description', 'confidence_threshold',
            'auto_block_enabled'
        ]

    def create(self, validated_data):
        import secrets
        validated_data['api_key'] = secrets.token_urlsafe(32)
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class LLMResponseSerializer(serializers.ModelSerializer):
    predicted_category_name = serializers.CharField(
        source='predicted_category.name',
        read_only=True
    )
    labeled_category_name = serializers.CharField(
        source='labeled_category.name',
        read_only=True
    )
    labeled_by_email = serializers.EmailField(
        source='labeled_by.email',
        read_only=True
    )

    class Meta:
        model = LLMResponse
        fields = [
            'id', 'application', 'prompt', 'response_text', 'llm_model',
            'predicted_category', 'predicted_category_name', 'confidence_score',
            'status', 'labeled_category', 'labeled_category_name',
            'labeled_by', 'labeled_by_email', 'labeled_at',
            'is_training_data', 'requires_review', 'review_notes',
            'user_feedback', 'response_time_ms', 'session_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'predicted_category', 'confidence_score', 'status',
            'labeled_by', 'labeled_at', 'created_at', 'updated_at'
        ]


class LLMResponseAnalysisRequestSerializer(serializers.Serializer):
    prompt = serializers.CharField(required=True)
    response_text = serializers.CharField(required=True)
    llm_model = serializers.CharField(required=False, allow_blank=True)
    session_id = serializers.CharField(required=False, allow_blank=True)


class LLMResponseAnalysisResponseSerializer(serializers.Serializer):
    response_id = serializers.UUIDField()
    status = serializers.CharField()
    predicted_category = serializers.CharField(allow_null=True)
    confidence_score = serializers.FloatField(allow_null=True)
    should_block = serializers.BooleanField()
    message = serializers.CharField()


class LLMResponseLabelSerializer(serializers.Serializer):
    labeled_category = serializers.UUIDField(required=True)
    review_notes = serializers.CharField(required=False, allow_blank=True)
    is_training_data = serializers.BooleanField(default=True)


class ModelVersionSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(
        source='created_by.email',
        read_only=True
    )

    class Meta:
        model = ModelVersion
        fields = [
            'id', 'application', 'version_name', 'training_samples',
            'accuracy', 'precision', 'recall', 'f1_score',
            'model_type', 'hyperparameters', 'training_duration_seconds',
            'is_active', 'is_baseline', 'created_at', 'created_by',
            'created_by_email'
        ]
        read_only_fields = [
            'id', 'training_samples', 'accuracy', 'precision', 'recall',
            'f1_score', 'training_duration_seconds', 'created_at', 'created_by'
        ]


class TrainingJobSerializer(serializers.ModelSerializer):
    initiated_by_email = serializers.EmailField(
        source='initiated_by.email',
        read_only=True
    )
    model_version_name = serializers.CharField(
        source='model_version.version_name',
        read_only=True
    )

    class Meta:
        model = TrainingJob
        fields = [
            'id', 'application', 'model_version', 'model_version_name',
            'status', 'training_samples_count', 'started_at',
            'completed_at', 'error_message', 'logs',
            'initiated_by', 'initiated_by_email', 'created_at'
        ]
        read_only_fields = [
            'id', 'model_version', 'status', 'training_samples_count',
            'started_at', 'completed_at', 'error_message', 'logs',
            'initiated_by', 'created_at'
        ]


class TrainingJobCreateSerializer(serializers.Serializer):
    application_id = serializers.UUIDField(required=True)
    version_name = serializers.CharField(required=True, max_length=100)
    hyperparameters = serializers.JSONField(required=False)


class AnalyticsSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsSnapshot
        fields = [
            'id', 'application', 'snapshot_date', 'snapshot_hour',
            'total_requests', 'blocked_requests', 'flagged_requests',
            'allowed_requests', 'avg_confidence_score', 'avg_response_time_ms',
            'category_distribution', 'hourly_distribution', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AlertSerializer(serializers.ModelSerializer):
    acknowledged_by_email = serializers.EmailField(
        source='acknowledged_by.email',
        read_only=True
    )

    class Meta:
        model = Alert
        fields = [
            'id', 'application', 'title', 'message', 'severity',
            'alert_type', 'is_acknowledged', 'acknowledged_by',
            'acknowledged_by_email', 'acknowledged_at', 'metadata',
            'created_at'
        ]
        read_only_fields = [
            'id', 'acknowledged_by', 'acknowledged_at', 'created_at'
        ]


class DashboardOverviewSerializer(serializers.Serializer):
    total_applications = serializers.IntegerField()
    total_responses = serializers.IntegerField()
    blocked_responses = serializers.IntegerField()
    flagged_responses = serializers.IntegerField()
    allowed_responses = serializers.IntegerField()
    avg_confidence_score = serializers.FloatField()
    active_alerts = serializers.IntegerField()
    pending_reviews = serializers.IntegerField()
    training_data_count = serializers.IntegerField()


class ResponseTrendSerializer(serializers.Serializer):
    date = serializers.DateField()
    total = serializers.IntegerField()
    blocked = serializers.IntegerField()
    flagged = serializers.IntegerField()
    allowed = serializers.IntegerField()


class CategoryDistributionSerializer(serializers.Serializer):
    category_name = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class ApplicationMetricsSerializer(serializers.Serializer):
    application_id = serializers.UUIDField()
    application_name = serializers.CharField()
    total_responses = serializers.IntegerField()
    blocked_rate = serializers.FloatField()
    avg_confidence = serializers.FloatField()
    model_version = serializers.CharField()
    last_trained = serializers.DateTimeField(allow_null=True)


class RealtimeMetricsSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    requests_last_hour = serializers.IntegerField()
    requests_last_5min = serializers.IntegerField()
    blocked_last_hour = serializers.IntegerField()
    avg_response_time_ms = serializers.FloatField()
    current_qps = serializers.FloatField()


class ModelPerformanceSerializer(serializers.Serializer):
    model_version = serializers.CharField()
    accuracy = serializers.FloatField()
    precision = serializers.FloatField()
    recall = serializers.FloatField()
    f1_score = serializers.FloatField()
    training_samples = serializers.IntegerField()
    is_active = serializers.BooleanField()