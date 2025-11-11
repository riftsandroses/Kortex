import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL

def guardrail_model_upload_path(instance, filename):
    # e.g. guardrails/models/<app_slug>/<version>/model.bin
    return f"guardrails/models/{instance.app.slug}/{instance.version}/{filename}"

class GuardrailApp(models.Model):
    """
    Represents an external AI-integrated application that wants guardrails.
    Each GuardrailApp has its own model (or model versions) and settings.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    base_model_name = models.CharField(
        max_length=200, default='distilbert-base-uncased', 
        help_text="HuggingFace model id used as base"
    )
    current_model_version = models.CharField(max_length=100, blank=True, null=True)
    config = models.JSONField(default=dict, blank=True)  # to store thresholds etc.

    def __str__(self):
        return self.name

class ModelVersion(models.Model):
    """
    Tracks versions for a GuardrailApp's trained models.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app = models.ForeignKey(GuardrailApp, related_name='model_versions', on_delete=models.CASCADE)
    version = models.CharField(max_length=64)  # e.g. v1-20251013-...
    created_at = models.DateTimeField(auto_now_add=True)
    metrics = models.JSONField(default=dict, blank=True)  # e.g. accuracy, f1 per label
    model_files = models.JSONField(default=list, blank=True)  # stores paths/URIs
    trained_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True)
    categories = models.JSONField(default=list, blank=True, help_text="List of categories/labels that this model can classify")

    class Meta:
        unique_together = ('app', 'version')

    def __str__(self):
        return f"{self.app.slug}:{self.version}"

class CapturedResponse(models.Model):
    """
    A single LLM response captured before being shown to end-user.
    """
    LEVEL_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('block', 'Block'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app = models.ForeignKey(GuardrailApp, related_name='responses', on_delete=models.CASCADE)
    request_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    prompt = models.TextField(blank=True)
    response_text = models.TextField()
    captured_at = models.DateTimeField(default=timezone.now)
    evaluated = models.BooleanField(default=False)
    predicted_label = models.CharField(max_length=64, blank=True)  # e.g. safe/toxic/pii
    predicted_score = models.FloatField(null=True, blank=True)  # probability/confidence
    action = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='info')
    # human labeling
    labeled = models.BooleanField(default=False)
    label = models.CharField(max_length=64, blank=True)  # human label
    labeled_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    labeled_at = models.DateTimeField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)  # extra info (llm model name, etc.)

    class Meta:
        ordering = ['-captured_at']

    def __str__(self):
        return f"{self.app.slug} | {self.id}"

class TrainingJob(models.Model):
    """
    Records a training job launched for an app.
    """
    STATUS = [('pending','pending'), ('running','running'), ('failed','failed'), ('done','done')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app = models.ForeignKey(GuardrailApp, related_name='training_jobs', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    logs = models.TextField(blank=True)
    model_version = models.ForeignKey(ModelVersion, null=True, blank=True, on_delete=models.SET_NULL)
    initiated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    params = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
