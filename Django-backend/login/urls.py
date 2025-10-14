from django.urls import path
from .views import JWTLoginView, JWTLogoutView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('sign-in/', JWTLoginView.as_view(), name='jwt_login'),
    path('sign-out/', JWTLogoutView.as_view(), name='jwt_logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]