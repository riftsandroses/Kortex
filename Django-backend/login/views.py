from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
import re

class JWTLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"error": "Username and password required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, username):
            return Response({"error": "Please enter a valid email address"}, status=status.HTTP_400_BAD_REQUEST)

        # Lookup user by email
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        # Authenticate user
        user = authenticate(username=user.username, password=password)
        if user is None:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # Create response
        response = Response({
            "message": "Login successful",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }
        }, status=status.HTTP_200_OK)

        # Set HttpOnly cookies
        response.set_cookie(
            key='access_token',
            value=access_token,
            httponly=True,
            secure=False,        # ⚠️ Change to True in production (HTTPS)
            samesite='Lax',
            max_age=60 * 60 * 24  # 1 day
        )
        response.set_cookie(
            key='refresh_token',
            value=refresh_token,
            httponly=True,
            secure=False,
            samesite='Lax',
            max_age=60 * 60 * 24 * 7  # 7 days
        )

        return response


class JWTLogoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        response = Response(
            {"message": "Successfully logged out"},
            status=status.HTTP_205_RESET_CONTENT
        )

        # Delete cookies
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')

        # Optionally, blacklist the refresh token
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass

        return response