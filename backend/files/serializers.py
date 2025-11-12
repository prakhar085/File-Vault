from rest_framework import serializers
from .models import File


class FileSerializer(serializers.ModelSerializer):
    reference_count = serializers.IntegerField(read_only=True)
    original_file = serializers.PrimaryKeyRelatedField(read_only=True)
    # File field will automatically serialize to a URL for download

    class Meta:
        model = File
        fields = [
            'id',
            'file',  # This provides the download URL
            'original_filename',
            'file_type',
            'size',
            'uploaded_at',
            'user_id',
            'file_hash',  # SHA-256 hash for deduplication
            'is_reference',
            'original_file',
            'reference_count',
        ]
        read_only_fields = ['id', 'uploaded_at', 'is_reference', 'original_file', 'reference_count', 'user_id', 'file_hash']