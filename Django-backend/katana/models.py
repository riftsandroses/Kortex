from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

User = get_user_model()


class IntegratedApplication(models.Model):
    """Represents an AI-integrated application using katana"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    api_key = models.CharField(max_length=255, unique=True, db_index=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    is_active = models.BooleanField(default=True)
    model_version = models.CharField(max_length=50, default='base_v1')
    confidence_threshold = models.FloatField(
        default=0.85,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    auto_block_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'katana_integrated_application'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['api_key']),
            models.Index(fields=['owner', 'is_active']),
        ]

    def __str__(self):
        return self.name


class ResponseCategory(models.Model):
    """Categories for classifying LLM responses"""
    CATEGORY_TYPES = [
        ('safe', 'Safe'),
        ('unsafe', 'Unsafe'),
        ('toxic', 'Toxic'),
        ('harmful', 'Harmful'),
        ('biased', 'Biased'),
        ('pii', 'Contains PII'),
        ('offensive', 'Offensive'),
        ('malicious', 'Malicious'),
        ('prompt_injection', 'Prompt Injection'),
        ('jailbreak', 'Jailbreak Attempt'),
        ('sensitive', 'Sensitive Content'),
        ('misinformation', 'Misinformation'),
        ('custom', 'Custom'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        IntegratedApplication,
        on_delete=models.CASCADE,
        related_name='categories',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=50, choices=CATEGORY_TYPES)
    description = models.TextField(blank=True)
    severity_level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    should_block = models.BooleanField(default=False)
    is_global = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'katana_response_category'
        ordering = ['-severity_level', 'name']
        indexes = [
            models.Index(fields=['application', 'category_type']),
            models.Index(fields=['is_global']),
        ]
        unique_together = [['application', 'name']]

    def __str__(self):
        return f"{self.name} ({self.category_type})"


class LLMResponse(models.Model):
    """Captured LLM responses for monitoring and training"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('allowed', 'Allowed'),
        ('blocked', 'Blocked'),
        ('flagged', 'Flagged for Review'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        IntegratedApplication,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    
    # Request/Response data
    prompt = models.TextField()
    response_text = models.TextField()
    llm_model = models.CharField(max_length=100, blank=True)
    
    # Analysis results
    predicted_category = models.ForeignKey(
        ResponseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='predicted_responses'
    )
    confidence_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Manual labeling
    labeled_category = models.ForeignKey(
        ResponseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='labeled_responses'
    )
    labeled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='labeled_responses'
    )
    labeled_at = models.DateTimeField(null=True, blank=True)
    
    # Additional flags
    is_training_data = models.BooleanField(default=False)
    requires_review = models.BooleanField(default=False)
    review_notes = models.TextField(blank=True)
    
    # Metadata
    user_feedback = models.CharField(
        max_length=20,
        choices=[('positive', 'Positive'), ('negative', 'Negative'), ('neutral', 'Neutral')],
        null=True,
        blank=True
    )
    response_time_ms = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_id = models.CharField(max_length=255, blank=True, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'katana_llm_response'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['application', 'status']),
            models.Index(fields=['application', 'created_at']),
            models.Index(fields=['is_training_data']),
            models.Index(fields=['labeled_category']),
            models.Index(fields=['requires_review']),
            models.Index(fields=['session_id']),
        ]

    def __str__(self):
        return f"Response {self.id} - {self.status}"


class ModelVersion(models.Model):
    """Track different versions of trained models"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        IntegratedApplication,
        on_delete=models.CASCADE,
        related_name='model_versions'
    )
    version_name = models.CharField(max_length=100)
    model_file_path = models.CharField(max_length=500)
    vectorizer_file_path = models.CharField(max_length=500, blank=True)
    
    # Training metrics
    training_samples = models.IntegerField(default=0)
    accuracy = models.FloatField(null=True, blank=True)
    precision = models.FloatField(null=True, blank=True)
    recall = models.FloatField(null=True, blank=True)
    f1_score = models.FloatField(null=True, blank=True)
    
    # Model details
    model_type = models.CharField(max_length=100, default='neural_network')
    hyperparameters = models.JSONField(default=dict)
    training_duration_seconds = models.IntegerField(null=True, blank=True)
    
    is_active = models.BooleanField(default=False)
    is_baseline = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_models'
    )

    class Meta:
        db_table = 'katana_model_version'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['application', 'is_active']),
        ]
        unique_together = [['application', 'version_name']]

    def __str__(self):
        return f"{self.application.name} - {self.version_name}"


class TrainingJob(models.Model):
    """Track training jobs"""
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        IntegratedApplication,
        on_delete=models.CASCADE,
        related_name='training_jobs'
    )
    model_version = models.ForeignKey(
        ModelVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='training_jobs'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    training_samples_count = models.IntegerField(default=0)
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    error_message = models.TextField(blank=True)
    logs = models.TextField(blank=True)
    
    initiated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='initiated_training_jobs'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'katana_training_job'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['application', 'status']),
        ]

    def __str__(self):
        return f"Training Job {self.id} - {self.status}"


class AnalyticsSnapshot(models.Model):
    """Pre-computed analytics for dashboard performance"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        IntegratedApplication,
        on_delete=models.CASCADE,
        related_name='analytics_snapshots'
    )
    
    snapshot_date = models.DateField(db_index=True)
    snapshot_hour = models.IntegerField(null=True, blank=True)
    
    # Aggregated metrics
    total_requests = models.IntegerField(default=0)
    blocked_requests = models.IntegerField(default=0)
    flagged_requests = models.IntegerField(default=0)
    allowed_requests = models.IntegerField(default=0)
    
    avg_confidence_score = models.FloatField(null=True, blank=True)
    avg_response_time_ms = models.FloatField(null=True, blank=True)
    
    category_distribution = models.JSONField(default=dict)
    hourly_distribution = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'katana_analytics_snapshot'
        ordering = ['-snapshot_date', '-snapshot_hour']
        indexes = [
            models.Index(fields=['application', 'snapshot_date']),
        ]
        unique_together = [['application', 'snapshot_date', 'snapshot_hour']]

    def __str__(self):
        return f"Analytics {self.application.name} - {self.snapshot_date}"


class Alert(models.Model):
    """Alerts for suspicious activity or threshold breaches"""
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        IntegratedApplication,
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    alert_type = models.CharField(max_length=100)
    
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    metadata = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'katana_alert'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['application', 'is_acknowledged']),
            models.Index(fields=['severity', 'created_at']),
        ]

    def __str__(self):
        return f"{self.severity.upper()}: {self.title}"