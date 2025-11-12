"""
Storage statistics service.

This module provides storage statistics calculation for users,
including total storage, original storage, and savings from deduplication.
"""

import logging
from typing import Dict, Any
from files.models import UserStats
from files.utils import validate_user_id

logger = logging.getLogger(__name__)


def get_storage_stats(user_id: str) -> Dict[str, Any]:
    """
    Get storage statistics for a user.
    
    Calculates:
    - total_storage_used: Storage used by unique files (originals only)
    - original_storage_used: Total storage if all files were stored separately
    - storage_savings: Difference between original and total (savings from deduplication)
    - savings_percentage: Percentage of storage saved
    
    Args:
        user_id: The user ID to get statistics for
        
    Returns:
        dict: Storage statistics with keys:
            - user_id: The user ID
            - total_storage_used: Bytes used by unique files
            - original_storage_used: Total bytes if no deduplication
            - storage_savings: Bytes saved from deduplication
            - savings_percentage: Percentage saved (0-100)
            
    Raises:
        ValueError: If user_id is missing or invalid
    """
    validate_user_id(user_id)
    
    stats, _ = UserStats.objects.get_or_create(user_id=user_id)
    total = stats.total_storage_used or 0
    original = stats.original_storage_used or 0
    savings = max(0, original - total)
    
    # Calculate savings percentage, avoiding division by zero
    savings_percentage = float((savings / original) * 100) if original > 0 else 0.0
    
    result = {
        "user_id": user_id,
        "total_storage_used": total,
        "original_storage_used": original,
        "storage_savings": savings,
        "savings_percentage": round(savings_percentage, 2),
    }
    
    logger.debug(f"Storage stats for user_id={user_id}: {result}")
    return result


