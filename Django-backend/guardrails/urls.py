from django.urls import path
from .views import (
    GuardrailAppListCreateAPIView, GuardrailAppDetailAPIView,
    CaptureResponseAPIView, CapturedResponseListAPIView, CapturedResponseDetailAPIView, LabelCapturedResponseAPIView,
    LaunchTrainingAPIView, TrainingJobListAPIView, TrainingJobDetailAPIView,
    DashboardOverviewAPIView, LabelDistributionAPIView, ModelPerformanceAPIView,
    EvaluateCapturedResponseAPIView
)

urlpatterns = [
    path('apps/', GuardrailAppListCreateAPIView.as_view(), name='guardrail-app-list'),
    path('apps/<slug:slug>/', GuardrailAppDetailAPIView.as_view(), name='guardrail-app-detail'),

    path('capture/', CaptureResponseAPIView.as_view(), name='capture-response'),
    path('responses/', CapturedResponseListAPIView.as_view(), name='responses-list'),
    path('responses/<uuid:pk>/', CapturedResponseDetailAPIView.as_view(), name='response-detail'),
    path('responses/<uuid:pk>/label/', LabelCapturedResponseAPIView.as_view(), name='response-label'),
    path('responses/<uuid:pk>/evaluate/', EvaluateCapturedResponseAPIView.as_view(), name='response-evaluate'),

    path('apps/<slug:slug>/train/', LaunchTrainingAPIView.as_view(), name='launch-training'),
    path('training/', TrainingJobListAPIView.as_view(), name='training-list'),
    path('training/<uuid:pk>/', TrainingJobDetailAPIView.as_view(), name='training-detail'),

    path('dashboard/overview/', DashboardOverviewAPIView.as_view(), name='dashboard-overview'),
    path('dashboard/label-distribution/', LabelDistributionAPIView.as_view(), name='dashboard-label-dist'),
    path('apps/<slug:slug>/performance/', ModelPerformanceAPIView.as_view(), name='model-performance'),
]
