from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


class IsAgent(BasePermission):
    message = "Action réservée aux agents."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_agent)


def assert_can_access_npi(user, npi):
    """Un usager n'accède qu'à son propre NPI (anti-IDOR) ; un agent accède à tous."""
    if user.is_usager and npi != user.npi:
        raise PermissionDenied("Vous ne pouvez accéder qu'à vos propres demandes.")
