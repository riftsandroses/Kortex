from rest_framework import permissions


class IsApplicationOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of an application to access it.
    """

    def has_object_permission(self, request, view, obj):
        # Check if the object has an owner attribute
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        # Check if the object has an application attribute with an owner
        if hasattr(obj, 'application'):
            return obj.application.owner == request.user
        
        return False


class HasValidAPIKey(permissions.BasePermission):
    """
    Permission class for API key authentication for external applications.
    """
    
    def has_permission(self, request, view):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return False
        
        from .models import IntegratedApplication
        
        try:
            app = IntegratedApplication.objects.get(
                api_key=api_key,
                is_active=True
            )
            # Attach app to request for use in view
            request.integrated_app = app
            return True
        except IntegratedApplication.DoesNotExist:
            return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow read access to all, but write access only to owners.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            # Still check ownership for read
            if hasattr(obj, 'owner'):
                return obj.owner == request.user
            if hasattr(obj, 'application'):
                return obj.application.owner == request.user
            return False

        # Write permissions are only allowed to the owner
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'application'):
            return obj.application.owner == request.user
        
        return False