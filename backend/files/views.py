"""
API views for file management.

This module provides REST API endpoints for file operations,
delegating business logic to service layer functions.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from .models import File
from .serializers import FileSerializer
from .services.upload_service import handle_upload
from .services.delete_service import delete_file
from .services.search_service import search_files_for_user, distinct_file_types_for_user
from .services.stats_service import get_storage_stats
from .constants import (
    ERROR_USER_ID_REQUIRED,
    ERROR_NO_FILE_PROVIDED,
)

logger = logging.getLogger(__name__)


class FileViewSet(viewsets.ModelViewSet):
    serializer_class = FileSerializer
    
    def get_throttles(self):
        # Exclude delete and stats from throttling
        if self.action in ['destroy', 'storage_stats']:
            return []
        return super().get_throttles()

    def get_queryset(self):
        """
        Get queryset filtered by user_id and query parameters.
        
        Returns:
            QuerySet of File objects for the requesting user
            
        Raises:
            ValidationError: If UserId header is missing
        """
        user_id = getattr(self.request, 'user_id', None)
        if not user_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"detail": ERROR_USER_ID_REQUIRED})
        return search_files_for_user(user_id, self.request.query_params)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific file by ID.
        
        Returns:
            200 OK with file data, or 404 if not found
        """
        user_id = getattr(request, 'user_id', None)
        if not user_id:
            return Response(
                {'detail': ERROR_USER_ID_REQUIRED}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        instance = get_object_or_404(File, id=kwargs.get('pk'), user_id=user_id)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Upload a new file.
        
        Returns:
            201 Created with file data, or 400/429 on error
        """
        user_id = getattr(request, 'user_id', None)
        if not user_id:
            return Response(
                {'detail': ERROR_USER_ID_REQUIRED}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {'detail': ERROR_NO_FILE_PROVIDED}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        new_file = handle_upload(user_id, file_obj)
        serializer = self.get_serializer(new_file)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a file.
        
        Returns:
            204 No Content on success, or 409 if file has references
        """
        user_id = getattr(request, 'user_id', None)
        if not user_id:
            return Response(
                {'detail': ERROR_USER_ID_REQUIRED}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        delete_file(user_id, kwargs.get('pk'))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='storage_stats', throttle_classes=[])
    def storage_stats(self, request):
        """
        Get storage statistics for the requesting user.
        
        Returns:
            200 OK with storage statistics
        """
        user_id = getattr(request, 'user_id', None)
        if not user_id:
            return Response(
                {'detail': ERROR_USER_ID_REQUIRED}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        data = get_storage_stats(user_id)
        return Response(data)

    @action(detail=False, methods=['get'], url_path='file_types')
    def file_types(self, request):
        """
        Get distinct file types (MIME types) for the requesting user.
        
        Returns:
            200 OK with list of file types
        """
        user_id = getattr(request, 'user_id', None)
        if not user_id:
            return Response(
                {'detail': ERROR_USER_ID_REQUIRED}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        types = distinct_file_types_for_user(user_id)
        return Response(types)
