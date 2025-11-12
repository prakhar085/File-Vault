"""
File deletion service with reference checking and statistics updates.

This module handles file deletion, including reference counting for originals,
physical file removal, and user statistics updates.
"""

import logging
from typing import Optional
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import APIException, NotFound
from files.models import File, UserStats
from files.constants import ERROR_CANNOT_DELETE_WITH_REFERENCES
from files.utils import validate_user_id

logger = logging.getLogger(__name__)


class ConflictError(APIException):
    """Exception raised when attempting to delete an original file with active references."""
    status_code = 409
    default_detail = {"detail": ERROR_CANNOT_DELETE_WITH_REFERENCES}

    def __init__(self):
        super().__init__(self.default_detail)


@transaction.atomic
def delete_file(user_id: str, file_id: str) -> None:
    """
    Delete a file record and update user statistics.
    
    For reference files:
    - Deletes the reference record only
    - Decrements original_storage_used
    
    For original files:
    - Checks if any references exist (across all users)
    - If references exist, raises ConflictError
    - Otherwise, deletes physical file and record
    - Decrements both original_storage_used and total_storage_used
    
    Args:
        user_id: The user ID requesting deletion
        file_id: The UUID of the file to delete
        
    Raises:
        ValueError: If user_id is missing or invalid
        NotFound: If file doesn't exist or doesn't belong to user
        ConflictError: If attempting to delete an original with active references
        
    Note:
        This function is atomic - either all changes succeed or none do.
    """
    validate_user_id(user_id)
    
    logger.info(f"Processing deletion for user_id={user_id}, file_id={file_id}")
    
    try:
        file_obj = File.objects.get(id=file_id, user_id=user_id)
    except ObjectDoesNotExist:
        logger.warning(f"File not found: file_id={file_id}, user_id={user_id}")
        raise NotFound()

    stats, _ = UserStats.objects.get_or_create(user_id=user_id)

    if file_obj.is_reference:
        # Delete reference record only
        logger.info(f"Deleting reference file_id={file_id}")
        size = file_obj.size or 0
        stats.original_storage_used = max(0, (stats.original_storage_used or 0) - size)
        stats.save(update_fields=["original_storage_used", "updated_at"])
        file_obj.delete()
        logger.info(f"Reference deleted successfully: file_id={file_id}")
        return

    # It's an original - check if ANY user has references to it
    # We prevent deletion if ANY user (including the current user) has references
    # Use exists() for better performance when we only need to check existence
    has_references = File.objects.filter(original_file=file_obj).exists()
    if has_references:
        # Get count only for logging purposes
        ref_count = File.objects.filter(original_file=file_obj).count()
        logger.warning(
            f"Cannot delete original file_id={file_id}: "
            f"{ref_count} reference(s) exist"
        )
        raise ConflictError()

    # Delete storage and object
    logger.info(f"Deleting original file_id={file_id}")
    storage_file = file_obj.file
    size = file_obj.size or 0
    
    # Delete database record first
    file_obj.delete()
    
    # Attempt to delete physical file
    if storage_file:
        try:
            storage_file.delete(save=False)
            logger.debug(f"Physical file deleted for file_id={file_id}")
        except Exception as e:
            # Ignore physical delete failures to keep API responsive
            # File record is already gone, so this is non-critical
            logger.warning(f"Failed to delete physical file for file_id={file_id}: {e}")

    # Update user stats
    stats.original_storage_used = max(0, (stats.original_storage_used or 0) - size)
    stats.total_storage_used = max(0, (stats.total_storage_used or 0) - size)
    stats.save(update_fields=["original_storage_used", "total_storage_used", "updated_at"])
    
    logger.info(f"Original file deleted successfully: file_id={file_id}, user_id={user_id}")


