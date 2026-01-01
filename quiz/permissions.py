from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Quiz


class IsCreator(BasePermission):

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Quiz):
            if request.method not in SAFE_METHODS:
                return obj.creator == request.user
            return True
        return False
