from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta, datetime
from django.shortcuts import get_object_or_404
import logging

from .models import (
    IntegratedApplication,
    ResponseCategory,
    LLMResponse,
    ModelVersion,
    TrainingJob,
    AnalyticsSnapshot,
    Alert
)
from .serializers import (
    IntegratedApplicationSerializer,
    IntegratedApplicationCreateSerializer,
    ResponseCategorySerializer,
    LLMResponseSerializer,
    LLMResponseAnalysisRequestSerializer,
    LLMResponseAnalysisResponseSerializer,
    LLMResponseLabelSerializer,
    ModelVersionSerializer,
    TrainingJobSerializer,
    TrainingJobCreateSerializer,
    AlertSerializer,
    DashboardOverviewSerializer,
    ResponseTrendSerializer,
    CategoryDistributionSerializer,
    ApplicationMetricsSerializer,
    RealtimeMetricsSerializer,
    ModelPerformanceSerializer,
)
from .permissions import IsApplicationOwner, HasValidAPIKey
from .ml_service import ml_service
from .tasks import train_model_task, generate_analytics_snapshot

logger = logging.getLogger(__name__)


# ==================== Application Management ====================

class ApplicationListCreateAPIView(APIView):
    """List all applications or create a new one"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        applications = IntegratedApplication.objects.filter(
            owner=request.user
        ).select_related('owner')
        
        serializer = IntegratedApplicationSerializer(applications, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def post(self, request):
        serializer = IntegratedApplicationCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            application = serializer.save()
            
            # Create default categories for new application
            default_categories = [
                {
                    'name': 'Safe Content',
                    'category_type': 'safe',
                    'severity_level': 1,
                    'should_block': False
                },
                {
                    'name': 'Toxic Language',
                    'category_type': 'toxic',
                    'severity_level': 7,
                    'should_block': True
                },
                {
                    'name': 'Harmful Content',
                    'category_type': 'harmful',
                    'severity_level': 9,
                    'should_block': True
                },
                {
                    'name': 'PII Detected',
                    'category_type': 'pii',
                    'severity_level': 8,
                    'should_block': True
                },
                {
                    'name': 'Prompt Injection',
                    'category_type': 'prompt_injection',
                    'severity_level': 10,
                    'should_block': True
                },
            ]
            
            for cat_data in default_categories:
                ResponseCategory.objects.create(
                    application=application,
                    **cat_data
                )
            
            response_serializer = IntegratedApplicationSerializer(application)
            return Response({
                'success': True,
                'message': 'Application created successfully',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ApplicationDetailAPIView(APIView):
    """Retrieve, update or delete an application"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationOwner]

    def get_object(self, pk, user):
        return get_object_or_404(IntegratedApplication, pk=pk, owner=user)

    def get(self, request, pk):
        application = self.get_object(pk, request.user)
        self.check_object_permissions(request, application)
        
        serializer = IntegratedApplicationSerializer(application)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def patch(self, request, pk):
        application = self.get_object(pk, request.user)
        self.check_object_permissions(request, application)
        
        serializer = IntegratedApplicationSerializer(
            application,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Application updated successfully',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        application = self.get_object(pk, request.user)
        self.check_object_permissions(request, application)
        
        application.delete()
        return Response({
            'success': True,
            'message': 'Application deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


class RegenerateAPIKeyView(APIView):
    """Regenerate API key for an application"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsApplicationOwner]

    def post(self, request, pk):
        application = get_object_or_404(IntegratedApplication, pk=pk, owner=request.user)
        self.check_object_permissions(request, application)
        
        import secrets
        application.api_key = secrets.token_urlsafe(32)
        application.save()
        
        serializer = IntegratedApplicationSerializer(application)
        return Response({
            'success': True,
            'message': 'API key regenerated successfully',
            'data': serializer.data
        })


# ==================== Category Management ====================

class CategoryListCreateAPIView(APIView):
    """List and create categories for an application"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, app_id):
        application = get_object_or_404(IntegratedApplication, pk=app_id, owner=request.user)
        
        categories = ResponseCategory.objects.filter(
            Q(application=application) | Q(is_global=True)
        )
        
        serializer = ResponseCategorySerializer(categories, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def post(self, request, app_id):
        application = get_object_or_404(IntegratedApplication, pk=app_id, owner=request.user)
        
        serializer = ResponseCategorySerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(application=application)
            return Response({
                'success': True,
                'message': 'Category created successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class CategoryDetailAPIView(APIView):
    """Retrieve, update or delete a category"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        return get_object_or_404(
            ResponseCategory,
            pk=pk,
            application__owner=user
        )

    def get(self, request, pk):
        category = self.get_object(pk, request.user)
        serializer = ResponseCategorySerializer(category)
        return Response({
            'success': True,
            'data': serializer.data
        })

    def patch(self, request, pk):
        category = self.get_object(pk, request.user)
        
        serializer = ResponseCategorySerializer(
            category,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Category updated successfully',
                'data': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        category = self.get_object(pk, request.user)
        category.delete()
        return Response({
            'success': True,
            'message': 'Category deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


# ==================== Response Analysis (External API) ====================

class AnalyzeResponseAPIView(APIView):
    """
    External API endpoint for LLM-integrated applications to analyze responses
    Uses API Key authentication
    """
    authentication_classes = []
    permission_classes = [HasValidAPIKey]

    def post(self, request):
        serializer = LLMResponseAnalysisRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        application = request.integrated_app
        data = serializer.validated_data

        try:
            # Predict using ML model
            category_id, confidence, should_block = ml_service.predict(
                application=application,
                prompt=data['prompt'],
                response_text=data['response_text']
            )

            # Determine status
            if should_block and application.auto_block_enabled:
                response_status = 'blocked'
            elif confidence and confidence < application.confidence_threshold:
                response_status = 'flagged'
            else:
                response_status = 'allowed'

            # Save response for monitoring
            llm_response = LLMResponse.objects.create(
                application=application,
                prompt=data['prompt'],
                response_text=data['response_text'],
                llm_model=data.get('llm_model', ''),
                predicted_category_id=category_id if category_id else None,
                confidence_score=confidence,
                status=response_status,
                session_id=data.get('session_id', ''),
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

            # Get category name
            category_name = None
            if category_id:
                category = ResponseCategory.objects.filter(id=category_id).first()
                if category:
                    category_name = category.name

            # Create alert if blocked
            if response_status == 'blocked':
                Alert.objects.create(
                    application=application,
                    title='Response Blocked',
                    message=f'Response blocked due to {category_name or "policy violation"}',
                    severity='high',
                    alert_type='blocked_response',
                    metadata={
                        'response_id': str(llm_response.id),
                        'category': category_name,
                        'confidence': confidence
                    }
                )

            response_serializer = LLMResponseAnalysisResponseSerializer({
                'response_id': llm_response.id,
                'status': response_status,
                'predicted_category': category_name,
                'confidence_score': confidence,
                'should_block': should_block and application.auto_block_enabled,
                'message': self.get_status_message(response_status, category_name)
            })

            return Response({
                'success': True,
                'data': response_serializer.data
            })

        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Internal server error during analysis'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def get_status_message(self, status, category):
        messages = {
            'blocked': f'Response blocked due to {category or "policy violation"}',
            'flagged': f'Response flagged for review - {category or "potential issue"}',
            'allowed': 'Response passed all guardrails'
        }
        return messages.get(status, 'Response processed')
    

# ==================== Response Management ====================

class ResponseListAPIView(APIView):
    """List all responses for an application with filtering"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, app_id):
        application = get_object_or_404(IntegratedApplication, pk=app_id, owner=request.user)
        
        responses = LLMResponse.objects.filter(
            application=application
        ).select_related(
            'predicted_category',
            'labeled_category',
            'labeled_by'
        ).order_by('-created_at')

        # Filtering
        status_filter = request.query_params.get('status')
        if status_filter:
            responses = responses.filter(status=status_filter)

        requires_review = request.query_params.get('requires_review')
        if requires_review:
            responses = responses.filter(requires_review=True)

        is_labeled = request.query_params.get('is_labeled')
        if is_labeled == 'true':
            responses = responses.filter(labeled_category__isnull=False)
        elif is_labeled == 'false':
            responses = responses.filter(labeled_category__isnull=True)

        category_id = request.query_params.get('category')
        if category_id:
            responses = responses.filter(
                Q(predicted_category_id=category_id) | Q(labeled_category_id=category_id)
            )

        # Date range filtering
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            responses = responses.filter(created_at__gte=start_date)
        if end_date:
            responses = responses.filter(created_at__lte=end_date)

        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        start = (page - 1) * page_size
        end = start + page_size

        total_count = responses.count()
        responses = responses[start:end]

        serializer = LLMResponseSerializer(responses, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': (total_count + page_size - 1) // page_size
            }
        })


class ResponseDetailAPIView(APIView):
    """Get details of a specific response"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        response_obj = get_object_or_404(
            LLMResponse,
            pk=pk,
            application__owner=request.user
        )
        
        serializer = LLMResponseSerializer(response_obj)
        return Response({
            'success': True,
            'data': serializer.data
        })


class LabelResponseAPIView(APIView):
    """Label a response for training"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        response_obj = get_object_or_404(
            LLMResponse,
            pk=pk,
            application__owner=request.user
        )

        serializer = LLMResponseLabelSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        
        # Verify category belongs to the same application
        category = get_object_or_404(
            ResponseCategory,
            pk=data['labeled_category'],
            application=response_obj.application
        )

        response_obj.labeled_category = category
        response_obj.labeled_by = request.user
        response_obj.labeled_at = timezone.now()
        response_obj.review_notes = data.get('review_notes', '')
        response_obj.is_training_data = data.get('is_training_data', True)
        response_obj.requires_review = False
        response_obj.save()

        response_serializer = LLMResponseSerializer(response_obj)
        
        return Response({
            'success': True,
            'message': 'Response labeled successfully',
            'data': response_serializer.data
        })


class BulkLabelResponseAPIView(APIView):
    """Bulk label multiple responses"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        response_ids = request.data.get('response_ids', [])
        category_id = request.data.get('labeled_category')
        review_notes = request.data.get('review_notes', '')
        is_training_data = request.data.get('is_training_data', True)

        if not response_ids or not category_id:
            return Response({
                'success': False,
                'error': 'response_ids and labeled_category are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get responses owned by user
        responses = LLMResponse.objects.filter(
            id__in=response_ids,
            application__owner=request.user
        )

        if not responses.exists():
            return Response({
                'success': False,
                'error': 'No valid responses found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Verify category
        category = get_object_or_404(ResponseCategory, pk=category_id)

        # Update all responses
        updated_count = responses.update(
            labeled_category=category,
            labeled_by=request.user,
            labeled_at=timezone.now(),
            review_notes=review_notes,
            is_training_data=is_training_data,
            requires_review=False
        )

        return Response({
            'success': True,
            'message': f'{updated_count} responses labeled successfully',
            'updated_count': updated_count
        })


# ==================== Model Training ====================

class ModelVersionListAPIView(APIView):
    """List all model versions for an application"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, app_id):
        application = get_object_or_404(IntegratedApplication, pk=app_id, owner=request.user)
        
        models = ModelVersion.objects.filter(
            application=application
        ).select_related('created_by').order_by('-created_at')

        serializer = ModelVersionSerializer(models, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })


class TrainModelAPIView(APIView):
    """Initiate model training"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TrainingJobCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        application = get_object_or_404(
            IntegratedApplication,
            pk=data['application_id'],
            owner=request.user
        )

        # Check if there's enough training data
        training_count = LLMResponse.objects.filter(
            application=application,
            labeled_category__isnull=False
        ).count()

        if training_count < 20:
            return Response({
                'success': False,
                'error': f'Insufficient training data. Need at least 20 labeled samples, have {training_count}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create training job
        training_job = TrainingJob.objects.create(
            application=application,
            status='queued',
            training_samples_count=training_count,
            initiated_by=request.user
        )

        # Start training asynchronously
        try:
            train_model_task(
                training_job.id,
                application.id,
                data['version_name'],
                data.get('hyperparameters')
            )
            
            return Response({
                'success': True,
                'message': 'Training job initiated successfully',
                'data': TrainingJobSerializer(training_job).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            training_job.status = 'failed'
            training_job.error_message = str(e)
            training_job.save()
            
            return Response({
                'success': False,
                'error': 'Failed to initiate training'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrainingJobListAPIView(APIView):
    """List training jobs for an application"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, app_id):
        application = get_object_or_404(IntegratedApplication, pk=app_id, owner=request.user)
        
        jobs = TrainingJob.objects.filter(
            application=application
        ).select_related('model_version', 'initiated_by').order_by('-created_at')

        serializer = TrainingJobSerializer(jobs, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data
        })


class TrainingJobDetailAPIView(APIView):
    """Get details of a training job"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        job = get_object_or_404(
            TrainingJob,
            pk=pk,
            application__owner=request.user
        )
        
        serializer = TrainingJobSerializer(job)
        return Response({
            'success': True,
            'data': serializer.data
        })


class ActivateModelAPIView(APIView):
    """Activate a specific model version"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        model_version = get_object_or_404(
            ModelVersion,
            pk=pk,
            application__owner=request.user
        )

        try:
            ml_service.activate_model(model_version)
            
            return Response({
                'success': True,
                'message': f'Model {model_version.version_name} activated successfully',
                'data': ModelVersionSerializer(model_version).data
            })

        except Exception as e:
            logger.error(f"Model activation error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Failed to activate model'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EvaluateModelAPIView(APIView):
    """Evaluate a model version"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        model_version = get_object_or_404(
            ModelVersion,
            pk=pk,
            application__owner=request.user
        )

        try:
            evaluation_results = ml_service.evaluate_model(model_version)
            
            return Response({
                'success': True,
                'data': evaluation_results
            })

        except Exception as e:
            logger.error(f"Model evaluation error: {str(e)}")
            return Response({
                'success': False,
                'error': 'Failed to evaluate model'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== Alert Management ====================

class AlertListAPIView(APIView):
    """List all alerts for user's applications"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        alerts = Alert.objects.filter(
            application__owner=request.user
        ).select_related('application', 'acknowledged_by').order_by('-created_at')

        # Filtering
        is_acknowledged = request.query_params.get('is_acknowledged')
        if is_acknowledged:
            acknowledged_val = is_acknowledged.lower() == 'true'
            alerts = alerts.filter(is_acknowledged=acknowledged_val)

        severity = request.query_params.get('severity')
        if severity:
            alerts = alerts.filter(severity=severity)

        app_id = request.query_params.get('application_id')
        if app_id:
            alerts = alerts.filter(application_id=app_id)

        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        start = (page - 1) * page_size
        end = start + page_size

        total_count = alerts.count()
        alerts = alerts[start:end]

        serializer = AlertSerializer(alerts, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': (total_count + page_size - 1) // page_size
            }
        })


class AcknowledgeAlertAPIView(APIView):
    """Acknowledge an alert"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        alert = get_object_or_404(
            Alert,
            pk=pk,
            application__owner=request.user
        )

        alert.is_acknowledged = True
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save()

        serializer = AlertSerializer(alert)
        
        return Response({
            'success': True,
            'message': 'Alert acknowledged successfully',
            'data': serializer.data
        })


class BulkAcknowledgeAlertsAPIView(APIView):
    """Bulk acknowledge multiple alerts"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        alert_ids = request.data.get('alert_ids', [])

        if not alert_ids:
            return Response({
                'success': False,
                'error': 'alert_ids is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        alerts = Alert.objects.filter(
            id__in=alert_ids,
            application__owner=request.user,
            is_acknowledged=False
        )

        updated_count = alerts.update(
            is_acknowledged=True,
            acknowledged_by=request.user,
            acknowledged_at=timezone.now()
        )

        return Response({
            'success': True,
            'message': f'{updated_count} alerts acknowledged successfully',
            'updated_count': updated_count
        })
    

# ==================== Dashboard & Analytics ====================

class DashboardOverviewAPIView(APIView):
    """Comprehensive dashboard overview with key metrics"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_apps = IntegratedApplication.objects.filter(owner=request.user)
        
        # Overall metrics
        total_applications = user_apps.count()
        
        all_responses = LLMResponse.objects.filter(application__in=user_apps)
        
        total_responses = all_responses.count()
        blocked_responses = all_responses.filter(status='blocked').count()
        flagged_responses = all_responses.filter(status='flagged').count()
        allowed_responses = all_responses.filter(status='allowed').count()
        
        avg_confidence = all_responses.aggregate(
            avg=Avg('confidence_score')
        )['avg'] or 0.0
        
        active_alerts = Alert.objects.filter(
            application__in=user_apps,
            is_acknowledged=False
        ).count()
        
        pending_reviews = all_responses.filter(requires_review=True).count()
        training_data_count = all_responses.filter(is_training_data=True).count()

        serializer = DashboardOverviewSerializer({
            'total_applications': total_applications,
            'total_responses': total_responses,
            'blocked_responses': blocked_responses,
            'flagged_responses': flagged_responses,
            'allowed_responses': allowed_responses,
            'avg_confidence_score': round(avg_confidence, 4),
            'active_alerts': active_alerts,
            'pending_reviews': pending_reviews,
            'training_data_count': training_data_count
        })

        return Response({
            'success': True,
            'data': serializer.data
        })


class ResponseTrendsAPIView(APIView):
    """Get response trends over time"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        app_id = request.query_params.get('application_id')
        days = int(request.query_params.get('days', 30))

        start_date = timezone.now() - timedelta(days=days)

        # Filter by application if provided
        if app_id:
            application = get_object_or_404(
                IntegratedApplication,
                pk=app_id,
                owner=request.user
            )
            responses = LLMResponse.objects.filter(
                application=application,
                created_at__gte=start_date
            )
        else:
            user_apps = IntegratedApplication.objects.filter(owner=request.user)
            responses = LLMResponse.objects.filter(
                application__in=user_apps,
                created_at__gte=start_date
            )

        # Aggregate by date
        from django.db.models.functions import TruncDate
        
        trends = responses.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total=Count('id'),
            blocked=Count('id', filter=Q(status='blocked')),
            flagged=Count('id', filter=Q(status='flagged')),
            allowed=Count('id', filter=Q(status='allowed'))
        ).order_by('date')

        serializer = ResponseTrendSerializer(trends, many=True)

        return Response({
            'success': True,
            'data': serializer.data
        })


class CategoryDistributionAPIView(APIView):
    """Get category distribution statistics"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        app_id = request.query_params.get('application_id')
        days = int(request.query_params.get('days', 30))

        start_date = timezone.now() - timedelta(days=days)

        # Filter by application
        if app_id:
            application = get_object_or_404(
                IntegratedApplication,
                pk=app_id,
                owner=request.user
            )
            responses = LLMResponse.objects.filter(
                application=application,
                created_at__gte=start_date,
                predicted_category__isnull=False
            )
        else:
            user_apps = IntegratedApplication.objects.filter(owner=request.user)
            responses = LLMResponse.objects.filter(
                application__in=user_apps,
                created_at__gte=start_date,
                predicted_category__isnull=False
            )

        total_responses = responses.count()

        # Get distribution
        distribution = responses.values(
            category_name=F('predicted_category__name')
        ).annotate(
            count=Count('id')
        ).order_by('-count')

        # Calculate percentages
        result = []
        for item in distribution:
            percentage = (item['count'] / total_responses * 100) if total_responses > 0 else 0
            result.append({
                'category_name': item['category_name'],
                'count': item['count'],
                'percentage': round(percentage, 2)
            })

        serializer = CategoryDistributionSerializer(result, many=True)

        return Response({
            'success': True,
            'data': serializer.data,
            'total_responses': total_responses
        })


class ApplicationMetricsAPIView(APIView):
    """Get detailed metrics for each application"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_apps = IntegratedApplication.objects.filter(
            owner=request.user
        ).select_related('owner')

        metrics = []

        for app in user_apps:
            responses = LLMResponse.objects.filter(application=app)
            total = responses.count()
            blocked = responses.filter(status='blocked').count()
            
            blocked_rate = (blocked / total * 100) if total > 0 else 0
            
            avg_confidence = responses.aggregate(
                avg=Avg('confidence_score')
            )['avg'] or 0.0

            # Get latest model version
            latest_model = ModelVersion.objects.filter(
                application=app
            ).order_by('-created_at').first()

            metrics.append({
                'application_id': app.id,
                'application_name': app.name,
                'total_responses': total,
                'blocked_rate': round(blocked_rate, 2),
                'avg_confidence': round(avg_confidence, 4),
                'model_version': app.model_version,
                'last_trained': latest_model.created_at if latest_model else None
            })

        serializer = ApplicationMetricsSerializer(metrics, many=True)

        return Response({
            'success': True,
            'data': serializer.data
        })


class RealtimeMetricsAPIView(APIView):
    """Get real-time metrics for monitoring"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        app_id = request.query_params.get('application_id')

        now = timezone.now()
        one_hour_ago = now - timedelta(hours=1)
        five_min_ago = now - timedelta(minutes=5)

        # Filter by application
        if app_id:
            application = get_object_or_404(
                IntegratedApplication,
                pk=app_id,
                owner=request.user
            )
            base_query = LLMResponse.objects.filter(application=application)
        else:
            user_apps = IntegratedApplication.objects.filter(owner=request.user)
            base_query = LLMResponse.objects.filter(application__in=user_apps)

        # Metrics for last hour
        last_hour_responses = base_query.filter(created_at__gte=one_hour_ago)
        requests_last_hour = last_hour_responses.count()
        blocked_last_hour = last_hour_responses.filter(status='blocked').count()

        # Metrics for last 5 minutes
        requests_last_5min = base_query.filter(created_at__gte=five_min_ago).count()

        # Average response time
        avg_response_time = last_hour_responses.aggregate(
            avg=Avg('response_time_ms')
        )['avg'] or 0.0

        # Calculate QPS (queries per second) for last 5 minutes
        current_qps = requests_last_5min / 300.0 if requests_last_5min > 0 else 0.0

        serializer = RealtimeMetricsSerializer({
            'timestamp': now,
            'requests_last_hour': requests_last_hour,
            'requests_last_5min': requests_last_5min,
            'blocked_last_hour': blocked_last_hour,
            'avg_response_time_ms': round(avg_response_time, 2),
            'current_qps': round(current_qps, 4)
        })

        return Response({
            'success': True,
            'data': serializer.data
        })


class ModelPerformanceAPIView(APIView):
    """Get performance metrics for all model versions"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, app_id):
        application = get_object_or_404(
            IntegratedApplication,
            pk=app_id,
            owner=request.user
        )

        models = ModelVersion.objects.filter(
            application=application
        ).order_by('-created_at')

        performance_data = []

        for model in models:
            performance_data.append({
                'model_version': model.version_name,
                'accuracy': model.accuracy or 0.0,
                'precision': model.precision or 0.0,
                'recall': model.recall or 0.0,
                'f1_score': model.f1_score or 0.0,
                'training_samples': model.training_samples,
                'is_active': model.is_active
            })

        serializer = ModelPerformanceSerializer(performance_data, many=True)

        return Response({
            'success': True,
            'data': serializer.data
        })


class HourlyDistributionAPIView(APIView):
    """Get hourly distribution of requests"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        app_id = request.query_params.get('application_id')
        days = int(request.query_params.get('days', 7))

        start_date = timezone.now() - timedelta(days=days)

        # Filter by application
        if app_id:
            application = get_object_or_404(
                IntegratedApplication,
                pk=app_id,
                owner=request.user
            )
            responses = LLMResponse.objects.filter(
                application=application,
                created_at__gte=start_date
            )
        else:
            user_apps = IntegratedApplication.objects.filter(owner=request.user)
            responses = LLMResponse.objects.filter(
                application__in=user_apps,
                created_at__gte=start_date
            )

        from django.db.models.functions import ExtractHour

        hourly_data = responses.annotate(
            hour=ExtractHour('created_at')
        ).values('hour').annotate(
            count=Count('id'),
            avg_confidence=Avg('confidence_score'),
            blocked_count=Count('id', filter=Q(status='blocked'))
        ).order_by('hour')

        # Format as 24-hour array
        result = {i: {'count': 0, 'avg_confidence': 0.0, 'blocked_count': 0} 
                  for i in range(24)}
        
        for item in hourly_data:
            result[item['hour']] = {
                'count': item['count'],
                'avg_confidence': round(item['avg_confidence'] or 0.0, 4),
                'blocked_count': item['blocked_count']
            }

        return Response({
            'success': True,
            'data': result
        })


class ConfidenceScoreDistributionAPIView(APIView):
    """Get distribution of confidence scores"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        app_id = request.query_params.get('application_id')

        # Filter by application
        if app_id:
            application = get_object_or_404(
                IntegratedApplication,
                pk=app_id,
                owner=request.user
            )
            responses = LLMResponse.objects.filter(
                application=application,
                confidence_score__isnull=False
            )
        else:
            user_apps = IntegratedApplication.objects.filter(owner=request.user)
            responses = LLMResponse.objects.filter(
                application__in=user_apps,
                confidence_score__isnull=False
            )

        # Create bins for confidence scores
        bins = {
            '0.0-0.2': {'min': 0.0, 'max': 0.2, 'count': 0},
            '0.2-0.4': {'min': 0.2, 'max': 0.4, 'count': 0},
            '0.4-0.6': {'min': 0.4, 'max': 0.6, 'count': 0},
            '0.6-0.8': {'min': 0.6, 'max': 0.8, 'count': 0},
            '0.8-1.0': {'min': 0.8, 'max': 1.0, 'count': 0},
        }

        for response in responses:
            score = response.confidence_score
            if 0.0 <= score < 0.2:
                bins['0.0-0.2']['count'] += 1
            elif 0.2 <= score < 0.4:
                bins['0.2-0.4']['count'] += 1
            elif 0.4 <= score < 0.6:
                bins['0.4-0.6']['count'] += 1
            elif 0.6 <= score < 0.8:
                bins['0.6-0.8']['count'] += 1
            elif 0.8 <= score <= 1.0:
                bins['0.8-1.0']['count'] += 1

        return Response({
            'success': True,
            'data': bins
        })


class TopBlockedCategoriesAPIView(APIView):
    """Get top blocked categories"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        app_id = request.query_params.get('application_id')
        limit = int(request.query_params.get('limit', 10))

        # Filter by application
        if app_id:
            application = get_object_or_404(
                IntegratedApplication,
                pk=app_id,
                owner=request.user
            )
            responses = LLMResponse.objects.filter(
                application=application,
                status='blocked',
                predicted_category__isnull=False
            )
        else:
            user_apps = IntegratedApplication.objects.filter(owner=request.user)
            responses = LLMResponse.objects.filter(
                application__in=user_apps,
                status='blocked',
                predicted_category__isnull=False
            )

        top_categories = responses.values(
            category_name=F('predicted_category__name'),
            severity=F('predicted_category__severity_level')
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:limit]

        return Response({
            'success': True,
            'data': list(top_categories)
        })