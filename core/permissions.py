from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Coach, Group, Player, PlayerEvaluation


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class IsAdminOrCoachReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_staff:
            return True
        # Coaches can read; write restrictions handled in object-level checks
        if request.user and hasattr(request.user, "coach_profile"):
            return request.method in SAFE_METHODS
        return False


class IsAdminOrCoachOfObject(BasePermission):
    """Admin has full access. Coach must own the object (group/player/evaluation)."""

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        coach = getattr(request.user, "coach_profile", None)
        if not coach:
            return False

        if isinstance(obj, Group):
            return obj.coach_id == coach.id
        if isinstance(obj, Player):
            return obj.group.coach_id == coach.id
        if isinstance(obj, PlayerEvaluation):
            return obj.player.group.coach_id == coach.id
        return False


class IsAdminOrCoachWriteOwnGroup(BasePermission):
    """Allow admin full access; coach can write only within their group."""

    def has_permission(self, request, view):
        if request.user and request.user.is_staff:
            return True
        # For non-safe methods, require coach
        if request.method not in SAFE_METHODS:
            return hasattr(request.user, "coach_profile")
        return True

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        coach = getattr(request.user, "coach_profile", None)
        if not coach:
            return False
        if isinstance(obj, Group):
            return obj.coach_id == coach.id
        if isinstance(obj, Player):
            return obj.group.coach_id == coach.id
        if isinstance(obj, PlayerEvaluation):
            return obj.player.group.coach_id == coach.id
        return False