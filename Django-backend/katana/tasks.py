import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Avg
from .models import (
    TrainingJob,
    IntegratedApplication,
    ModelVersion,
    LLMResponse,
    AnalyticsSnapshot,
    Alert
)
from .ml_service import ml_service

logger = logging.getLogger(__name__)


def train_model_task(job_id, application_id, version_name, hyperparameters=None):
    """
    Background task for model training
    In production, use Celery or similar task queue
    """
    try:
        job = TrainingJob.objects.get(id=job_id)
        application = IntegratedApplication.objects.get(id=application_id)

        job.status = 'running'
        job.started_at = timezone.now()
        job.save()

        # Train the model
        model_version = ml_service.train_model(
            application=application,
            version_name=version_name,
            hyperparameters=hyperparameters
        )

        # Update job
        job.status = 'completed'
        job.completed_at = timezone.now()
        job.model_version = model_version
        job.save()

        # Create success alert
        Alert.objects.create(
            application=application,
            title='Model Training Completed',
            message=f'Model {version_name} trained successfully with {model_version.training_samples} samples',
            severity='low',
            alert_type='training_completed',
            metadata={
                'model_version': version_name,
                'accuracy': model_version.accuracy,
                'training_samples': model_version.training_samples
            }
        )

        logger.info(f"Training job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Training job {job_id} failed: {str(e)}")
        
        try:
            job = TrainingJob.objects.get(id=job_id)
            job.status = 'failed'
            job.completed_at = timezone.now()
            job.error_message = str(e)
            job.save()

            # Create failure alert
            Alert.objects.create(
                application=application,
                title='Model Training Failed',
                message=f'Training failed for {version_name}: {str(e)[:200]}',
                severity='high',
                alert_type='training_failed',
                metadata={'error': str(e)}
            )
        except Exception as inner_e:
            logger.error(f"Failed to update job status: {str(inner_e)}")


def generate_analytics_snapshot(application_id=None, date=None):
    """
    Generate analytics snapshots for dashboard performance
    Should be run hourly via cron/celery beat
    """
    if date is None:
        date = timezone.now().date()

    try:
        if application_id:
            applications = [IntegratedApplication.objects.get(id=application_id)]
        else:
            applications = IntegratedApplication.objects.filter(is_active=True)

        for app in applications:
            current_hour = timezone.now().hour

            # Get responses for current hour
            responses = LLMResponse.objects.filter(
                application=app,
                created_at__date=date,
                created_at__hour=current_hour
            )

            total_requests = responses.count()
            
            if total_requests == 0:
                continue

            blocked = responses.filter(status='blocked').count()
            flagged = responses.filter(status='flagged').count()
            allowed = responses.filter(status='allowed').count()

            avg_confidence = responses.aggregate(
                avg=Avg('confidence_score')
            )['avg'] or 0.0

            avg_response_time = responses.aggregate(
                avg=Avg('response_time_ms')
            )['avg'] or 0.0

            # Category distribution
            category_dist = {}
            cat_counts = responses.values(
                'predicted_category__name'
            ).annotate(count=Count('id'))
            
            for item in cat_counts:
                if item['predicted_category__name']:
                    category_dist[item['predicted_category__name']] = item['count']

            # Update or create snapshot
            AnalyticsSnapshot.objects.update_or_create(
                application=app,
                snapshot_date=date,
                snapshot_hour=current_hour,
                defaults={
                    'total_requests': total_requests,
                    'blocked_requests': blocked,
                    'flagged_requests': flagged,
                    'allowed_requests': allowed,
                    'avg_confidence_score': avg_confidence,
                    'avg_response_time_ms': avg_response_time,
                    'category_distribution': category_dist
                }
            )

        logger.info(f"Analytics snapshots generated for {len(applications)} applications")

    except Exception as e:
        logger.error(f"Failed to generate analytics snapshot: {str(e)}")


def check_anomalies_and_create_alerts():
    """
    Check for anomalies and create alerts
    Should be run periodically (e.g., every 15 minutes)
    """
    try:
        applications = IntegratedApplication.objects.filter(is_active=True)

        for app in applications:
            now = timezone.now()
            one_hour_ago = now - timedelta(hours=1)
            one_day_ago = now - timedelta(days=1)

            # Check for high block rate in last hour
            recent_responses = LLMResponse.objects.filter(
                application=app,
                created_at__gte=one_hour_ago
            )

            total = recent_responses.count()
            
            if total > 50:  # Only check if significant traffic
                blocked = recent_responses.filter(status='blocked').count()
                block_rate = (blocked / total) * 100

                if block_rate > 30:  # Alert if more than 30% blocked
                    # Check if alert already exists
                    existing_alert = Alert.objects.filter(
                        application=app,
                        alert_type='high_block_rate',
                        created_at__gte=one_hour_ago,
                        is_acknowledged=False
                    ).exists()

                    if not existing_alert:
                        Alert.objects.create(
                            application=app,
                            title='High Block Rate Detected',
                            message=f'Block rate is {block_rate:.1f}% in the last hour ({blocked}/{total} requests)',
                            severity='high',
                            alert_type='high_block_rate',
                            metadata={
                                'block_rate': block_rate,
                                'blocked_count': blocked,
                                'total_count': total
                            }
                        )

            # Check for low confidence scores
            low_confidence = recent_responses.filter(
                confidence_score__lt=0.5,
                confidence_score__isnull=False
            ).count()

            if low_confidence > total * 0.4 and total > 20:
                existing_alert = Alert.objects.filter(
                    application=app,
                    alert_type='low_confidence',
                    created_at__gte=one_hour_ago,
                    is_acknowledged=False
                ).exists()

                if not existing_alert:
                    Alert.objects.create(
                        application=app,
                        title='Low Confidence Scores Detected',
                        message=f'{low_confidence} responses with confidence < 0.5 in the last hour',
                        severity='medium',
                        alert_type='low_confidence',
                        metadata={
                            'low_confidence_count': low_confidence,
                            'total_count': total
                        }
                    )

            # Check for spike in requests
            recent_count = recent_responses.count()
            previous_hour = LLMResponse.objects.filter(
                application=app,
                created_at__gte=one_hour_ago - timedelta(hours=1),
                created_at__lt=one_hour_ago
            ).count()

            if previous_hour > 0 and recent_count > previous_hour * 3:
                existing_alert = Alert.objects.filter(
                    application=app,
                    alert_type='traffic_spike',
                    created_at__gte=one_hour_ago,
                    is_acknowledged=False
                ).exists()

                if not existing_alert:
                    Alert.objects.create(
                        application=app,
                        title='Traffic Spike Detected',
                        message=f'Request volume increased {recent_count/previous_hour:.1f}x compared to previous hour',
                        severity='medium',
                        alert_type='traffic_spike',
                        metadata={
                            'current_count': recent_count,
                            'previous_count': previous_hour
                        }
                    )

        logger.info(f"Anomaly check completed for {applications.count()} applications")

    except Exception as e:
        logger.error(f"Failed to check anomalies: {str(e)}")


def cleanup_old_data():
    """
    Clean up old data to manage database size
    Run daily via cron
    """
    try:
        # Delete responses older than 90 days that aren't training data
        ninety_days_ago = timezone.now() - timedelta(days=90)
        
        deleted_responses = LLMResponse.objects.filter(
            created_at__lt=ninety_days_ago,
            is_training_data=False,
            labeled_category__isnull=True
        ).delete()

        # Delete old analytics snapshots (keep 1 year)
        # Delete old analytics snapshots (keep 1 year)
        one_year_ago = timezone.now() - timedelta(days=365)
        
        deleted_snapshots = AnalyticsSnapshot.objects.filter(
            snapshot_date__lt=one_year_ago.date()
        ).delete()

        # Delete acknowledged alerts older than 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        deleted_alerts = Alert.objects.filter(
            created_at__lt=thirty_days_ago,
            is_acknowledged=True
        ).delete()

        logger.info(
            f"Cleanup completed: {deleted_responses[0]} responses, "
            f"{deleted_snapshots[0]} snapshots, {deleted_alerts[0]} alerts deleted"
        )

    except Exception as e:
        logger.error(f"Failed to cleanup old data: {str(e)}")


def auto_retrain_models():
    """
    Automatically retrain models when sufficient new labeled data is available
    Run daily via cron
    """
    try:
        applications = IntegratedApplication.objects.filter(is_active=True)

        for app in applications:
            # Get active model
            active_model = ModelVersion.objects.filter(
                application=app,
                is_active=True
            ).first()

            if not active_model:
                continue

            # Count new labeled data since last training
            new_labeled_data = LLMResponse.objects.filter(
                application=app,
                labeled_category__isnull=False,
                labeled_at__gt=active_model.created_at
            ).count()

            # Retrain if we have 100+ new labeled samples
            if new_labeled_data >= 100:
                # Check if there's no ongoing training
                ongoing_training = TrainingJob.objects.filter(
                    application=app,
                    status__in=['queued', 'running']
                ).exists()

                if not ongoing_training:
                    # Create new version name
                    from datetime import datetime
                    version_name = f"auto_v{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                    # Create training job
                    training_job = TrainingJob.objects.create(
                        application=app,
                        status='queued',
                        training_samples_count=new_labeled_data,
                        initiated_by=None  # Automatic training
                    )

                    # Start training
                    train_model_task(
                        training_job.id,
                        app.id,
                        version_name
                    )

                    logger.info(
                        f"Auto-retraining initiated for {app.name} "
                        f"with {new_labeled_data} new samples"
                    )

        logger.info(f"Auto-retrain check completed for {applications.count()} applications")

    except Exception as e:
        logger.error(f"Failed to auto-retrain models: {str(e)}")