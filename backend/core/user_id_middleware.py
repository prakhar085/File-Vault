"""
User ID middleware for enforcing UserId header on API requests.

This middleware validates that all API requests include a UserId header
and attaches it to the request object for use in views and services.
"""

import logging
from django.http import JsonResponse
from files.constants import USER_ID_HEADER, ERROR_USER_ID_REQUIRED

logger = logging.getLogger(__name__)


class UserIdMiddleware:
    """
    Middleware to enforce UserId header on API requests.
    
    Only enforces header validation for paths starting with '/api/'.
    Allows frontend and static file access without the header.
    """
    
    def __init__(self, get_response):
        """
        Initialize middleware.
        
        Args:
            get_response: Django's get_response callable
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        Process request and validate UserId header for API routes.
        
        Args:
            request: The HTTP request object
            
        Returns:
            HTTP response (either error response or next middleware's response)
        """
        # Only enforce for API routes; allow frontend/static access without header
        if request.path.startswith('/api/'):
            user_id = request.headers.get(USER_ID_HEADER)
            if not user_id:
                logger.warning(f"Missing UserId header for API request: {request.path}")
                return JsonResponse(
                    {"detail": ERROR_USER_ID_REQUIRED}, 
                    status=400
                )
            request.user_id = user_id
            logger.debug(f"UserId header validated: user_id={user_id}, path={request.path}")
        return self.get_response(request)


