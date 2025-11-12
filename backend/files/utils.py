"""
Utility functions for the File Vault application.

This module contains shared utility functions used across services.
"""

import logging
from typing import Optional
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)


def get_storage_quota_bytes() -> int:
    """
    Get the storage quota in bytes from settings.
    
    Returns:
        int: Storage quota in bytes (default: 10 MB)
    """
    quota_mb = getattr(settings, 'FILE_VAULT_STORAGE_QUOTA_MB', 10)
    return int(quota_mb) * 1024 * 1024


def validate_user_id(user_id: Optional[str]) -> None:
    """
    Validate that user_id is provided and not empty.
    
    Args:
        user_id: The user ID to validate
        
    Raises:
        ValueError: If user_id is None or empty
    """
    if not user_id or not user_id.strip():
        raise ValueError("user_id is required and cannot be empty")


def get_file_size(uploaded_file: UploadedFile) -> int:
    """
    Safely extract file size from uploaded file.
    
    Args:
        uploaded_file: The uploaded file object
        
    Returns:
        int: File size in bytes (0 if not available)
    """
    return getattr(uploaded_file, 'size', 0) or 0


def get_file_type(uploaded_file: UploadedFile) -> str:
    """
    Safely extract MIME type from uploaded file.
    
    Args:
        uploaded_file: The uploaded file object
        
    Returns:
        str: MIME type (empty string if not available)
    """
    return getattr(uploaded_file, 'content_type', '') or ''


def get_original_filename(uploaded_file: UploadedFile) -> str:
    """
    Safely extract original filename from uploaded file.
    
    Args:
        uploaded_file: The uploaded file object
        
    Returns:
        str: Original filename (empty string if not available)
    """
    return getattr(uploaded_file, 'name', '') or ''

