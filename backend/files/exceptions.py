from rest_framework.views import exception_handler
from rest_framework.exceptions import Throttled
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    if isinstance(exc, Throttled):
        return Response({"detail": "Call Limit Reached"}, status=429)
    return exception_handler(exc, context)


