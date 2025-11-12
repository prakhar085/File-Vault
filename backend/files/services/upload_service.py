"""
File upload service with deduplication and quota management.

This module handles file uploads, including SHA-256 hashing for deduplication,
storage quota enforcement, and user statistics tracking.
"""

import hashlib
import logging
from typing import Optional
from django.db import transaction
from django.core.files.uploadedfile import UploadedFile
from rest_framework.exceptions import APIException
from files.models import File, UserStats
from files.constants import ERROR_STORAGE_QUOTA_EXCEEDED
from files.utils import (
    get_storage_quota_bytes,
    validate_user_id,
    get_file_size,
    get_file_type,
    get_original_filename,
)

logger = logging.getLogger(__name__)


class QuotaExceeded(APIException):
    """Exception raised when storage quota is exceeded."""
    status_code = 429
    default_detail = {"detail": ERROR_STORAGE_QUOTA_EXCEEDED}

    def __init__(self):
        super().__init__(self.default_detail)


def _compute_sha256_streaming(uploaded_file: UploadedFile) -> str:
    """
    Compute SHA-256 hash of uploaded file using streaming to avoid loading entire file into memory.
    
    Args:
        uploaded_file: The uploaded file to hash
        
    Returns:
        str: SHA-256 hex digest (64 characters)
        
    Note:
        The file pointer is reset to the beginning after hashing to allow
        subsequent reads of the file content.
    """
    sha256 = hashlib.sha256()
    # Reset file pointer to beginning
    if hasattr(uploaded_file, 'seek'):
        uploaded_file.seek(0)
    
    # Stream file in chunks to avoid memory issues with large files
    for chunk in uploaded_file.chunks():
        sha256.update(chunk)
    
    # Reset file pointer again after hashing for subsequent reads
    if hasattr(uploaded_file, 'seek'):
        uploaded_file.seek(0)
    
    return sha256.hexdigest()


def _get_or_create_user_stats(user_id: str) -> UserStats:
    """
    Get or create UserStats record for a user.
    
    Args:
        user_id: The user ID
        
    Returns:
        UserStats: The user statistics record
    """
    stats, _ = UserStats.objects.get_or_create(user_id=user_id)
    return stats


@transaction.atomic
def handle_upload(user_id: str, uploaded_file: UploadedFile) -> File:
    """
    Handle file upload with deduplication and quota enforcement.
    
    This function:
    1. Computes SHA-256 hash of the uploaded file
    2. Checks for existing file with the same hash
    3. Creates a reference record if duplicate exists, otherwise creates new original
    4. Enforces storage quota for new originals
    5. Updates user statistics
    
    Args:
        user_id: The user ID uploading the file
        uploaded_file: The file to upload
        
    Returns:
        File: The created File record (either original or reference)
        
    Raises:
        ValueError: If user_id is missing or invalid
        QuotaExceeded: If uploading a new original would exceed storage quota
        
    Note:
        This function is atomic - either all changes succeed or none do.
    """
    validate_user_id(user_id)
    
    logger.info(f"Processing upload for user_id={user_id}, filename={getattr(uploaded_file, 'name', 'unknown')}")
    
    # Compute hash and extract metadata
    file_hash = _compute_sha256_streaming(uploaded_file)
    size = get_file_size(uploaded_file)
    file_type = get_file_type(uploaded_file)
    original_filename = get_original_filename(uploaded_file)

    logger.debug(f"File hash={file_hash[:8]}..., size={size}, type={file_type}")

    # Lookup existing original across all users (for deduplication)
    # The new file record will always be scoped to user_id
    existing_original = File.objects.filter(
        file_hash=file_hash, 
        is_reference=False
    ).first()

    stats = _get_or_create_user_stats(user_id)

    # Always increase original_storage_used by uploaded size
    stats.original_storage_used = (stats.original_storage_used or 0) + size

    if existing_original:
        # Create a reference record for this user
        logger.info(f"Duplicate detected, creating reference to original file_id={existing_original.id}")
        new_file = File.objects.create(
            file=None,
            original_filename=original_filename,
            file_type=file_type,
            size=size,
            user_id=user_id,
            file_hash=file_hash,
            is_reference=True,
            original_file=existing_original,
        )
        # total_storage_used unchanged for references
        stats.save(update_fields=["original_storage_used", "updated_at"])
        return new_file

    # Enforce quota for new originals
    quota_bytes = get_storage_quota_bytes()
    current_usage = stats.total_storage_used or 0
    
    if current_usage + size > quota_bytes:
        logger.warning(
            f"Quota exceeded for user_id={user_id}: "
            f"current={current_usage}, requested={size}, quota={quota_bytes}"
        )
        # Revert original_storage_used increment within this atomic transaction
        transaction.set_rollback(True)
        raise QuotaExceeded()

    # Save new original file
    logger.info(f"Creating new original file for user_id={user_id}")
    new_file = File.objects.create(
        file=uploaded_file,
        original_filename=original_filename,
        file_type=file_type,
        size=size,
        user_id=user_id,
        file_hash=file_hash,
        is_reference=False,
        original_file=None,
    )

    stats.total_storage_used = current_usage + size
    stats.save(update_fields=["original_storage_used", "total_storage_used", "updated_at"])
    
    logger.info(f"Upload successful: file_id={new_file.id}, user_id={user_id}")
    return new_file


