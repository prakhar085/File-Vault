"""
File search and filtering service.

This module provides file search and filtering capabilities, including
reference count annotation and FTS (Full-Text Search) support.
"""

import logging
from typing import List, Optional
from django.db.models import QuerySet, OuterRef, Subquery, IntegerField, Value, Count
from django.db.models.functions import Coalesce
from django.conf import settings
from django_filters import rest_framework as django_filters
from files.models import File
from files.utils import validate_user_id

logger = logging.getLogger(__name__)


def _reference_count_subquery():
    """
    Create a subquery to count references for each original file.
    
    Returns:
        Coalesce expression that returns 0 if no references exist,
        otherwise returns the count of references.
    """
    return Coalesce(
        Subquery(
            File.objects.filter(original_file=OuterRef('pk'))
            .values('original_file')
            .annotate(c=Count('*'))
            .values('c')[:1]
        ),
        Value(0),
        output_field=IntegerField(),
    )


class FileFilter(django_filters.FilterSet):
    """
    FilterSet for file search and filtering.
    
    Supports:
    - search: Case-insensitive filename search
    - file_type: Exact MIME type match (case-insensitive)
    - min_size, max_size: Size range filtering (bytes)
    - start_date, end_date: Upload date range filtering (ISO datetime)
    """
    search = django_filters.CharFilter(method='filter_search')
    file_type = django_filters.CharFilter(field_name='file_type', lookup_expr='iexact')
    min_size = django_filters.NumberFilter(field_name='size', lookup_expr='gte')
    max_size = django_filters.NumberFilter(field_name='size', lookup_expr='lte')
    start_date = django_filters.IsoDateTimeFilter(field_name='uploaded_at', lookup_expr='gte')
    end_date = django_filters.IsoDateTimeFilter(field_name='uploaded_at', lookup_expr='lte')

    class Meta:
        model = File
        fields = ['search', 'file_type', 'min_size', 'max_size', 'start_date', 'end_date']

    def filter_search(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """
        Filter files by filename using search.
        
        Currently uses case-insensitive contains matching.
        Can be extended to use FTS5 when enabled.
        
        Args:
            queryset: The queryset to filter
            name: Field name (unused)
            value: Search term
            
        Returns:
            Filtered queryset
        """
        # Optional FTS guard; fallback to icontains
        enable_fts = getattr(settings, 'FILE_VAULT_ENABLE_FTS', False)
        if enable_fts:
            # FTS stub: fallback until FTS tables are provisioned
            # TODO: Implement FTS5 when FILE_VAULT_ENABLE_FTS=True
            logger.debug("FTS enabled but not yet implemented, using icontains")
            return queryset.filter(original_filename__icontains=value)
        return queryset.filter(original_filename__icontains=value)


def search_files_for_user(user_id: str, params: dict) -> QuerySet[File]:
    """
    Search and filter files for a specific user.
    
    Args:
        user_id: The user ID to filter files for
        params: Query parameters for filtering (from request.query_params)
        
    Returns:
        QuerySet of File objects filtered by user_id and params,
        annotated with reference_count for each file.
        
    Note:
        Returns empty queryset if user_id is invalid.
    """
    if not user_id:
        logger.warning("search_files_for_user called with empty user_id")
        return File.objects.none()
    
    # Filter by user_id and annotate with reference_count
    # Use select_related for foreign key (original_file) to avoid N+1 queries
    qs = File.objects.filter(user_id=user_id).select_related('original_file')
    qs = qs.annotate(reference_count=_reference_count_subquery())
    
    # Apply filters from query parameters
    file_filter = FileFilter(params, queryset=qs)
    
    logger.debug(f"Search for user_id={user_id}, params={params}, count={file_filter.qs.count()}")
    return file_filter.qs


def distinct_file_types_for_user(user_id: str) -> List[str]:
    """
    Get distinct file types (MIME types) for a user.
    
    Args:
        user_id: The user ID to get file types for
        
    Returns:
        List of distinct MIME types (empty list if user_id is invalid)
    """
    if not user_id:
        logger.warning("distinct_file_types_for_user called with empty user_id")
        return []
    
    file_types = list(
        File.objects.filter(user_id=user_id)
        .values_list('file_type', flat=True)
        .distinct()
        .order_by('file_type')
    )
    
    logger.debug(f"File types for user_id={user_id}: {len(file_types)} distinct types")
    return file_types


