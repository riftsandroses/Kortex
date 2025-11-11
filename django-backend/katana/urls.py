from django.urls import path
from .views import (
    # Application Management
    ApplicationListCreateAPIView,
    ApplicationDetailAPIView,
    RegenerateAPIKeyView,
    
    # Category Management
    CategoryListCreateAPIView,
    CategoryDetailAPIView,
    
    # Response Analysis (External)
    AnalyzeResponseAPIView,
    
    # Response Management
    ResponseListAPIView,
    ResponseDetailAPIView,
    LabelResponseAPIView,
    BulkLabelResponseAPIView,
    
    # Model Training
    ModelVersionListAPIView,
    TrainModelAPIView,
    TrainingJobListAPIView,
    TrainingJobDetailAPIView,
    ActivateModelAPIView,
    EvaluateModelAPIView,
    
    # Alert Management
    AlertListAPIView,
    AcknowledgeAlertAPIView,
    BulkAcknowledgeAlertsAPIView,
    
    # Dashboard & Analytics
    DashboardOverviewAPIView,
    ResponseTrendsAPIView,
    CategoryDistributionAPIView,
    ApplicationMetricsAPIView,
    RealtimeMetricsAPIView,
    ModelPerformanceAPIView,
    HourlyDistributionAPIView,
    ConfidenceScoreDistributionAPIView,
    TopBlockedCategoriesAPIView,
)

app_name = 'guardrails'

urlpatterns = [
    # ==================== Application Management ====================
    path('applications/', ApplicationListCreateAPIView.as_view(), name='application-list-create'),
    path('applications/<uuid:pk>/', ApplicationDetailAPIView.as_view(), name='application-detail'),
    path('applications/<uuid:pk>/regenerate-key/', RegenerateAPIKeyView.as_view(), name='regenerate-api-key'),
    
    # ==================== Category Management ====================
    path('applications/<uuid:app_id>/categories/', CategoryListCreateAPIView.as_view(), name='category-list-create'),
    path('categories/<uuid:pk>/', CategoryDetailAPIView.as_view(), name='category-detail'),
    
    # ==================== Response Analysis (External API) ====================
    path('analyze/', AnalyzeResponseAPIView.as_view(), name='analyze-response'),
    
    # ==================== Response Management ====================
    path('applications/<uuid:app_id>/responses/', ResponseListAPIView.as_view(), name='response-list'),
    path('responses/<uuid:pk>/', ResponseDetailAPIView.as_view(), name='response-detail'),
    path('responses/<uuid:pk>/label/', LabelResponseAPIView.as_view(), name='label-response'),
    path('responses/bulk-label/', BulkLabelResponseAPIView.as_view(), name='bulk-label-responses'),
    
    # ==================== Model Training ====================
    path('applications/<uuid:app_id>/models/', ModelVersionListAPIView.as_view(), name='model-version-list'),
    path('train/', TrainModelAPIView.as_view(), name='train-model'),
    path('applications/<uuid:app_id>/training-jobs/', TrainingJobListAPIView.as_view(), name='training-job-list'),
    path('training-jobs/<uuid:pk>/', TrainingJobDetailAPIView.as_view(), name='training-job-detail'),
    path('models/<uuid:pk>/activate/', ActivateModelAPIView.as_view(), name='activate-model'),
    path('models/<uuid:pk>/evaluate/', EvaluateModelAPIView.as_view(), name='evaluate-model'),
    
    # ==================== Alert Management ====================
    path('alerts/', AlertListAPIView.as_view(), name='alert-list'),
    path('alerts/<uuid:pk>/acknowledge/', AcknowledgeAlertAPIView.as_view(), name='acknowledge-alert'),
    path('alerts/bulk-acknowledge/', BulkAcknowledgeAlertsAPIView.as_view(), name='bulk-acknowledge-alerts'),
    
    # ==================== Dashboard & Analytics ====================
    path('dashboard/overview/', DashboardOverviewAPIView.as_view(), name='dashboard-overview'),
    path('analytics/response-trends/', ResponseTrendsAPIView.as_view(), name='response-trends'),
    path('analytics/category-distribution/', CategoryDistributionAPIView.as_view(), name='category-distribution'),
    path('analytics/application-metrics/', ApplicationMetricsAPIView.as_view(), name='application-metrics'),
    path('analytics/realtime-metrics/', RealtimeMetricsAPIView.as_view(), name='realtime-metrics'),
    path('analytics/applications/<uuid:app_id>/model-performance/', ModelPerformanceAPIView.as_view(), name='model-performance'),
    path('analytics/hourly-distribution/', HourlyDistributionAPIView.as_view(), name='hourly-distribution'),
    path('analytics/confidence-distribution/', ConfidenceScoreDistributionAPIView.as_view(), name='confidence-distribution'),
    path('analytics/top-blocked-categories/', TopBlockedCategoriesAPIView.as_view(), name='top-blocked-categories'),
]