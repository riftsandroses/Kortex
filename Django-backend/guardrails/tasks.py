import os
import json
import logging
from celery import shared_task
from django.utils import timezone
from django.conf import settings

from .models import CapturedResponse, TrainingJob, ModelVersion, GuardrailApp
from .ml.trainer import train_model_for_app
from .ml.inference import evaluate_text_with_model, load_model_for_app

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def async_evaluate_and_store(self, captured_id):
    """
    Called when a new CapturedResponse is created. Attempts to run inference
    using the app's current model. If model missing, falls back to a base rule.
    """
    try:
        cr = CapturedResponse.objects.get(pk=captured_id)
    except CapturedResponse.DoesNotExist:
        logger.warning("CapturedResponse not found %s", captured_id)
        return

    try:
        label, score, action = evaluate_text_with_model(cr.app.slug, cr.response_text)
        cr.predicted_label = label
        cr.predicted_score = score
        cr.action = action
        cr.evaluated = True
        cr.save()
    except Exception:
        logger.exception("Async evaluation failed for %s", captured_id)
        # leave unevaluated; UI can show fallback

@shared_task(bind=True)
def launch_training_job(self, training_job_id):
    """
    Launch the training pipeline for the given TrainingJob record.
    This calls the train_model_for_app function in ml/trainer.py which runs HF training.
    """
    tj = TrainingJob.objects.get(pk=training_job_id)
    tj.status = 'running'
    tj.started_at = timezone.now()
    tj.save()

    try:
        app = tj.app
        params = tj.params or {}

        # Train and return metadata: {version, model_files, metrics}
        result = train_model_for_app(app_slug=app.slug, initiated_by=str(tj.initiated_by.id if tj.initiated_by else None), params=params)

        version = result['version']
        metrics = result.get('metrics', {})
        model_files = result.get('model_files', [])

        mv, _ = ModelVersion.objects.get_or_create(app=app, version=version, defaults={
            'metrics': metrics,
            'model_files': model_files,
            'trained_by': tj.initiated_by,
        })
        mv.metrics = metrics
        mv.model_files = model_files
        mv.save()

        app.current_model_version = mv.version
        app.save()

        tj.model_version = mv
        tj.status = 'done'
        tj.finished_at = timezone.now()
        tj.logs += "\nTraining finished OK\n"
        tj.save()
    except Exception as e:
        logger.exception("Training failed for job %s", training_job_id)
        tj.status = 'failed'
        tj.logs += f"\nTraining failed: {str(e)}\n"
        tj.finished_at = timezone.now()
        tj.save()
        raise
