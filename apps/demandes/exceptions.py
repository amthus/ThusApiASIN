import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

CODES = {
    400: "validation_error",
    401: "not_authenticated",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    415: "unsupported_media_type",
    429: "throttled",
}


class ConflictError(APIException):
    """409 : l'action est refusée à cause de l'état actuel des données."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conflit avec l'état actuel de la ressource."
    default_code = "conflict"


def api_exception_handler(exc, context):
    """Format d'erreur unique : {"error": {"code", "message", "details"}} ; jamais de stack trace."""
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Erreur inattendue")
        return Response(
            {"error": {"code": "server_error", "message": "Erreur interne du serveur.", "details": None}},
            status=500,
        )
    data = response.data
    if isinstance(data, dict) and set(data) == {"detail"}:
        message, details = str(data["detail"]), None
    else:
        message, details = "Données invalides.", data
    response.data = {
        "error": {"code": CODES.get(response.status_code, "error"), "message": message, "details": details}
    }
    return response
