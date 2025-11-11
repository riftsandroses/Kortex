from django.db import models
from django.contrib.auth import get_user_model
from guardrails.models import GuardrailApp, ModelVersion

User = get_user_model()

class ModelAssignment(models.Model):
    source_model = models.ForeignKey(ModelVersion, on_delete=models.CASCADE, related_name='assignments')
    target_app = models.ForeignKey(GuardrailApp, on_delete=models.CASCADE, related_name='assigned_models')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='model_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-assigned_at']
        unique_together = ('source_model', 'target_app')
        verbose_name = "Model Assignment"
        verbose_name_plural = "Model Assignments"

    def __str__(self):
        return f"{self.source_model.version} → {self.target_app.name}"
