from django.db import models
import uuid
import os


def file_upload_path(instance, filename):
    ext = filename.split('.')[-1] if '.' in filename else ''
    name = f"{uuid.uuid4()}"
    filename = f"{name}.{ext}" if ext else name
    return os.path.join('uploads', filename)


class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to=file_upload_path, null=True, blank=True)
    original_filename = models.CharField(max_length=255, db_index=True)
    file_type = models.CharField(max_length=100, db_index=True)
    size = models.IntegerField(db_index=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user_id = models.CharField(max_length=255, db_index=True)
    file_hash = models.CharField(max_length=64, db_index=True)
    is_reference = models.BooleanField(default=False, db_index=True)
    original_file = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="references",
        related_query_name="reference",
    )

    class Meta:
        indexes = [
            # Single column indexes (already have db_index=True, but explicit for clarity)
            models.Index(fields=["user_id"], name="idx_user_id"),
            models.Index(fields=["original_filename"], name="idx_original_filename"),
            models.Index(fields=["file_hash"], name="idx_file_hash"),
            
            # Composite indexes for common filter combinations
            models.Index(fields=["user_id", "uploaded_at"], name="idx_user_uploaded"),
            models.Index(fields=["user_id", "file_type"], name="idx_user_file_type"),
            models.Index(fields=["user_id", "size"], name="idx_user_size"),
            
            # Index for search queries (user_id + original_filename)
            models.Index(fields=["user_id", "original_filename"], name="idx_user_filename_search"),
            
            # Index for filtering originals vs references per user
            models.Index(fields=["user_id", "is_reference"], name="idx_user_is_reference"),
            
            # Multi-column indexes for complex filters
            models.Index(fields=["user_id", "file_type", "uploaded_at"], name="idx_user_type_date"),
            models.Index(fields=["user_id", "size", "uploaded_at"], name="idx_user_size_date"),
            
            # Index for deduplication lookups (hash + is_reference)
            models.Index(fields=["file_hash", "is_reference"], name="idx_hash_is_reference"),
        ]

    def __str__(self):
        return self.original_filename


class UserStats(models.Model):
    user_id = models.CharField(primary_key=True, max_length=255)
    total_storage_used = models.IntegerField(default=0)
    original_storage_used = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
