"""
Rate throttling for API requests based on user ID.

This module implements per-user rate limiting using Django REST Framework's
throttling mechanism.
"""

import logging
from typing import Optional
from rest_framework.throttling import SimpleRateThrottle
from django.conf import settings
from files.constants import (
    DEFAULT_RATE_LIMIT_CALLS,
    DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
    RATE_LIMIT_CACHE_PREFIX,
)

logger = logging.getLogger(__name__)


class UserIdRateThrottle(SimpleRateThrottle):
    """
    Rate throttle based on user ID.
    
    Limits requests per user according to configured rate limits.
    Uses Django's cache to track request counts per user.
    """
    scope = "user_id"

    def get_cache_key(self, request, view) -> Optional[str]:
        """
        Get cache key for rate limiting based on user_id.
        
        Args:
            request: The HTTP request object
            view: The view being accessed
            
        Returns:
            Cache key string, or None if user_id is not available
        """
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return None
        return self.cache_key_for_user(user_id)

    def cache_key_for_user(self, user_id: str) -> str:
        """
        Generate cache key for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            Cache key string
        """
        return f"{RATE_LIMIT_CACHE_PREFIX}_{user_id}"

    def get_rate(self) -> str:
        """
        Get rate limit string from settings.
        
        Returns:
            Rate limit string in format "calls/unit" (e.g., "2/second")
        """
        calls = getattr(settings, "FILE_VAULT_RATE_LIMIT_CALLS", DEFAULT_RATE_LIMIT_CALLS)
        window = int(getattr(settings, "FILE_VAULT_RATE_LIMIT_WINDOW", DEFAULT_RATE_LIMIT_WINDOW_SECONDS))
        
        # DRF supports units: second(s)/minute(s)/hour(s)/day(s)
        if window == 1:
            unit = "second"
        elif window == 60:
            unit = "minute"
        elif window == 3600:
            unit = "hour"
        elif window == 86400:
            unit = "day"
        else:
            unit = "second"
        
        return f"{calls}/{unit}"

