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
    list_display = ['version', 'app', 'categories_preview', 'created_at']
    list_filter = ['app', 'created_at']
    search_fields = ['version', 'app__name']
    
    def categories_preview(self, obj):
        return ", ".join(obj.categories[:3]) + ("..." if len(obj.categories) > 3 else "")
    categories_preview.short_description = 'Categories'

@admin.register(TrainingJob)
class TrainingJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'app', 'status', 'created_at', 'started_at', 'finished_at')
