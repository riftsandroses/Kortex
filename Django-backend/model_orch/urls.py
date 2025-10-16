from django.urls import path
from .views import (
    ModelVersionListAPIView,
    ModelCategoriesAPIView,
    AssignModelAPIView,
    ModelAssignmentListAPIView,
    # ModelDebugAPIView
)

urlpatterns = [
    path('models/', ModelVersionListAPIView.as_view(), name='model-list'),
    path('models/<uuid:model_id>/categories/', ModelCategoriesAPIView.as_view(), name='model-categories'),
    path('models/<uuid:model_id>/assign/', AssignModelAPIView.as_view(), name='assign-model'),
    path('assignments/', ModelAssignmentListAPIView.as_view(), name='assignment-list'),
    
    
    # Categories Debugger
    # path('models/<uuid:model_id>/debug/', ModelDebugAPIView.as_view(), name='model-debug'),
]
