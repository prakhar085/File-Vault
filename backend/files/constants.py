"""
Constants for the File Vault application.

This module centralizes all configuration constants, error messages,
and magic numbers used throughout the application.
"""

# Default Configuration Values
DEFAULT_STORAGE_QUOTA_MB = 10
DEFAULT_RATE_LIMIT_CALLS = 2
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 1

# HTTP Header Names
USER_ID_HEADER = "UserId"

# API Error Messages
ERROR_USER_ID_REQUIRED = "UserId header required"
ERROR_NO_FILE_PROVIDED = "No file provided"
ERROR_CALL_LIMIT_REACHED = "Call Limit Reached"
ERROR_STORAGE_QUOTA_EXCEEDED = "Storage Quota Exceeded"
ERROR_CANNOT_DELETE_WITH_REFERENCES = "Cannot delete original file with active references"

# File Upload Settings
SHA256_HASH_LENGTH = 64  # SHA-256 hex digest length
MAX_FILENAME_LENGTH = 255
MAX_FILE_TYPE_LENGTH = 100

# Rate Limit Cache Key Prefix
RATE_LIMIT_CACHE_PREFIX = "throttle_user_id"

# Database Index Names (for reference)
INDEX_USER_ID = "idx_user_id"
INDEX_USER_UPLOADED = "idx_user_uploaded"
INDEX_USER_FILE_TYPE = "idx_user_file_type"
INDEX_USER_SIZE = "idx_user_size"
INDEX_USER_FILENAME_SEARCH = "idx_user_filename_search"
INDEX_USER_IS_REFERENCE = "idx_user_is_reference"
INDEX_HASH_IS_REFERENCE = "idx_hash_is_reference"

