from django.contrib import admin
from .models import GuardrailApp, CapturedResponse, ModelVersion, TrainingJob

@admin.register(GuardrailApp)
class GuardrailAppAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'owner', 'current_model_version', 'created_at')
    search_fields = ('name', 'slug')

@admin.register(CapturedResponse)
class CapturedResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'app', 'captured_at', 'predicted_label', 'label', 'evaluated', 'labeled')
    list_filter = ('app', 'predicted_label', 'label', 'evaluated', 'labeled')
    search_fields = ('response_text', 'prompt', 'request_id')

@admin.register(ModelVersion)
class ModelVersionAdmin(admin.ModelAdmin):
    list_display = ('app', 'version', 'created_at')

@admin.register(TrainingJob)
class TrainingJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'app', 'status', 'created_at', 'started_at', 'finished_at')
