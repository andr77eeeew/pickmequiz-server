from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import Quiz

class IsCreator(BasePermission):

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Quiz):
            if request.method not in SAFE_METHODS:
                return obj.creator == request.user
            return True
        return False