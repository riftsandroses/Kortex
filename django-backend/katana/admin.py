from django.contrib import admin
from .models import (
    IntegratedApplication,
    ResponseCategory,
    LLMResponse,
    ModelVersion,
    TrainingJob,
    AnalyticsSnapshot,
    Alert
)


@admin.register(IntegratedApplication)
class IntegratedApplicationAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'is_active', 'model_version', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'owner__email', 'api_key']
    readonly_fields = ['id', 'api_key', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'description', 'owner', 'is_active')
        }),
        ('Configuration', {
            'fields': ('model_version', 'confidence_threshold', 'auto_block_enabled')
        }),
        ('API Access', {
            'fields': ('api_key',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ResponseCategory)
class ResponseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_type', 'severity_level', 'should_block', 'application', 'is_global']
    list_filter = ['category_type', 'should_block', 'is_global', 'severity_level']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(LLMResponse)
class LLMResponseAdmin(admin.ModelAdmin):
    list_display = ['id', 'application', 'status', 'confidence_score', 'predicted_category', 'labeled_category', 'created_at']
    list_filter = ['status', 'is_training_data', 'requires_review', 'created_at']
    search_fields = ['prompt', 'response_text', 'session_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Response Data', {
            'fields': ('id', 'application', 'prompt', 'response_text', 'llm_model', 'session_id')
        }),
        ('Analysis', {
            'fields': ('predicted_category', 'confidence_score', 'status')
        }),
        ('Labeling', {
            'fields': ('labeled_category', 'labeled_by', 'labeled_at', 'is_training_data', 'review_notes')
        }),
        ('Metadata', {
            'fields': ('requires_review', 'user_feedback', 'response_time_ms', 'ip_address', 'user_agent')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ModelVersion)
class ModelVersionAdmin(admin.ModelAdmin):
    list_display = ['version_name', 'application', 'accuracy', 'f1_score', 'is_active', 'training_samples', 'created_at']
    list_filter = ['is_active', 'is_baseline', 'model_type', 'created_at']
    search_fields = ['version_name', 'application__name']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Model Information', {
            'fields': ('id', 'application', 'version_name', 'model_type', 'is_active', 'is_baseline')
        }),
        ('Performance Metrics', {
            'fields': ('accuracy', 'precision', 'recall', 'f1_score', 'training_samples')
        }),
        ('Files & Configuration', {
            'fields': ('model_file_path', 'vectorizer_file_path', 'hyperparameters', 'training_duration_seconds')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at')
        }),
    )


@admin.register(TrainingJob)
class TrainingJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'application', 'status', 'training_samples_count', 'started_at', 'completed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['application__name', 'error_message']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'


@admin.register(AnalyticsSnapshot)
class AnalyticsSnapshotAdmin(admin.ModelAdmin):
    list_display = ['application', 'snapshot_date', 'snapshot_hour', 'total_requests', 'blocked_requests', 'avg_confidence_score']
    list_filter = ['snapshot_date', 'application']
    search_fields = ['application__name']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'snapshot_date'


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'application', 'severity', 'alert_type', 'is_acknowledged', 'created_at']
    list_filter = ['severity', 'alert_type', 'is_acknowledged', 'created_at']
    search_fields = ['title', 'message', 'application__name']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('id', 'application', 'title', 'message', 'severity', 'alert_type')
        }),
        ('Acknowledgement', {
            'fields': ('is_acknowledged', 'acknowledged_by', 'acknowledged_at')
        }),
        ('Additional Data', {
            'fields': ('metadata',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )