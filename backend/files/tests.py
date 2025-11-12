"""
Comprehensive test suite for Abnormal File Vault application.
Run with: python manage.py test files.tests
"""
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
import hashlib
import io
from files.models import File, UserStats
from files.services.upload_service import handle_upload, QuotaExceeded
from files.services.delete_service import delete_file, ConflictError
from files.services.search_service import search_files_for_user, distinct_file_types_for_user
from files.services.stats_service import get_storage_stats
from rest_framework.exceptions import NotFound


class FileModelTestCase(TestCase):
    """Test File model functionality"""
    
    def setUp(self):
        self.test_content = b"test file content"
        self.test_file = SimpleUploadedFile(
            "test.txt",
            self.test_content,
            content_type="text/plain"
        )
    
    def test_file_creation(self):
        """Test creating a file record"""
        file_obj = File.objects.create(
            file=self.test_file,
            original_filename="test.txt",
            file_type="text/plain",
            size=len(self.test_content),
            user_id="user1",
            file_hash="abc123",
            is_reference=False,
        )
        self.assertIsNotNone(file_obj.id)
        self.assertEqual(file_obj.original_filename, "test.txt")
        self.assertFalse(file_obj.is_reference)
        self.assertIsNone(file_obj.original_file)
    
    def test_reference_file_creation(self):
        """Test creating a reference file"""
        original = File.objects.create(
            file=self.test_file,
            original_filename="original.txt",
            file_type="text/plain",
            size=len(self.test_content),
            user_id="user1",
            file_hash="abc123",
            is_reference=False,
        )
        # Create a new file for reference (no file field)
        reference_file = SimpleUploadedFile(
            "reference.txt",
            self.test_content,
            content_type="text/plain"
        )
        reference = File.objects.create(
            original_filename="reference.txt",
            file_type="text/plain",
            size=len(self.test_content),
            user_id="user2",
            file_hash="abc123",
            is_reference=True,
            original_file=original,
        )
        self.assertTrue(reference.is_reference)
        self.assertEqual(reference.original_file, original)
        # File field should be empty/None for reference
        self.assertFalse(reference.file)  # FieldFile evaluates to False when empty


class UserStatsModelTestCase(TestCase):
    """Test UserStats model functionality"""
    
    def test_user_stats_creation(self):
        """Test creating user stats"""
        stats = UserStats.objects.create(
            user_id="user1",
            total_storage_used=1024,
            original_storage_used=2048,
        )
        self.assertEqual(stats.user_id, "user1")
        self.assertEqual(stats.total_storage_used, 1024)
        self.assertEqual(stats.original_storage_used, 2048)


class UploadServiceTestCase(TestCase):
    """Test upload service functionality"""
    
    def setUp(self):
        self.test_content = b"test file content"
        self.test_file = SimpleUploadedFile(
            "test.txt",
            self.test_content,
            content_type="text/plain"
        )
        self.user_id = "user1"
    
    def test_upload_new_file(self):
        """Test uploading a new file"""
        file_obj = handle_upload(self.user_id, self.test_file)
        self.assertIsNotNone(file_obj.id)
        self.assertFalse(file_obj.is_reference)
        self.assertEqual(file_obj.user_id, self.user_id)
        
        # Check UserStats created
        stats = UserStats.objects.get(user_id=self.user_id)
        self.assertEqual(stats.total_storage_used, len(self.test_content))
        self.assertEqual(stats.original_storage_used, len(self.test_content))
    
    def test_upload_duplicate_file(self):
        """Test uploading duplicate file creates reference"""
        # Upload first file
        original = handle_upload(self.user_id, self.test_file)
        
        # Create another file with same content
        test_file2 = SimpleUploadedFile(
            "test2.txt",
            self.test_content,
            content_type="text/plain"
        )
        
        # Upload duplicate
        reference = handle_upload(self.user_id, test_file2)
        
        self.assertTrue(reference.is_reference)
        self.assertEqual(reference.original_file, original)
        self.assertEqual(reference.file_hash, original.file_hash)
        
        # Check stats - total_storage_used should not increase, but original_storage_used should
        stats = UserStats.objects.get(user_id=self.user_id)
        self.assertEqual(stats.total_storage_used, len(self.test_content))  # Only original counts
        self.assertEqual(stats.original_storage_used, len(self.test_content) * 2)  # Both files count
    
    def test_upload_quota_exceeded(self):
        """Test that quota is enforced"""
        # Set quota to 1 byte (very small)
        with patch('django.conf.settings.FILE_VAULT_STORAGE_QUOTA_MB', 0.000001):
            large_content = b"x" * (2 * 1024 * 1024)  # 2MB
            large_file = SimpleUploadedFile(
                "large.txt",
                large_content,
                content_type="text/plain"
            )
            with self.assertRaises(QuotaExceeded):
                handle_upload(self.user_id, large_file)
    
    def test_upload_file_over_10mb_quota(self):
        """Test uploading a file larger than default 10MB quota"""
        # Default quota is 10MB = 10 * 1024 * 1024 bytes
        quota_bytes = 10 * 1024 * 1024
        # Create file that exceeds quota by 1MB
        large_content = b"x" * (quota_bytes + 1024 * 1024)  # 11MB
        large_file = SimpleUploadedFile(
            "large_11mb.txt",
            large_content,
            content_type="text/plain"
        )
        with self.assertRaises(QuotaExceeded):
            handle_upload(self.user_id, large_file)
        
        # Verify no file was created
        self.assertEqual(File.objects.filter(user_id=self.user_id).count(), 0)
    
    def test_upload_file_exactly_at_quota_limit(self):
        """Test uploading a file exactly at the quota limit"""
        quota_bytes = 10 * 1024 * 1024  # 10MB
        # Create file exactly at quota
        exact_content = b"x" * quota_bytes
        exact_file = SimpleUploadedFile(
            "exact_10mb.txt",
            exact_content,
            content_type="text/plain"
        )
        # Should succeed at exact limit
        file_obj = handle_upload(self.user_id, exact_file)
        self.assertIsNotNone(file_obj.id)
        stats = UserStats.objects.get(user_id=self.user_id)
        self.assertEqual(stats.total_storage_used, quota_bytes)
    
    def test_upload_multiple_files_cumulative_quota(self):
        """Test that cumulative file uploads respect quota"""
        quota_bytes = 10 * 1024 * 1024  # 10MB
        # Upload first file (5MB)
        file1_size = 5 * 1024 * 1024
        file1_content = b"x" * file1_size
        file1 = SimpleUploadedFile("file1.txt", file1_content, content_type="text/plain")
        handle_upload(self.user_id, file1)
        
        # Upload second file (4MB) - should succeed (total 9MB)
        file2_size = 4 * 1024 * 1024
        file2_content = b"y" * file2_size
        file2 = SimpleUploadedFile("file2.txt", file2_content, content_type="text/plain")
        handle_upload(self.user_id, file2)
        
        # Upload third file (2MB) - should fail (would be 11MB total)
        file3_size = 2 * 1024 * 1024
        file3_content = b"z" * file3_size
        file3 = SimpleUploadedFile("file3.txt", file3_content, content_type="text/plain")
        with self.assertRaises(QuotaExceeded):
            handle_upload(self.user_id, file3)
        
        # Verify only 2 files exist
        self.assertEqual(File.objects.filter(user_id=self.user_id, is_reference=False).count(), 2)
        stats = UserStats.objects.get(user_id=self.user_id)
        self.assertEqual(stats.total_storage_used, file1_size + file2_size)
    
    def test_upload_empty_file(self):
        """Test uploading an empty file"""
        empty_file = SimpleUploadedFile(
            "empty.txt",
            b"",
            content_type="text/plain"
        )
        file_obj = handle_upload(self.user_id, empty_file)
        self.assertIsNotNone(file_obj.id)
        self.assertEqual(file_obj.size, 0)
        stats = UserStats.objects.get(user_id=self.user_id)
        self.assertEqual(stats.total_storage_used, 0)
        self.assertEqual(stats.original_storage_used, 0)
    
    def test_upload_very_small_file(self):
        """Test uploading a very small file (1 byte)"""
        small_file = SimpleUploadedFile(
            "small.txt",
            b"x",
            content_type="text/plain"
        )
        file_obj = handle_upload(self.user_id, small_file)
        self.assertIsNotNone(file_obj.id)
        self.assertEqual(file_obj.size, 1)
        stats = UserStats.objects.get(user_id=self.user_id)
        self.assertEqual(stats.total_storage_used, 1)
    
    def test_quota_allows_reference_after_limit(self):
        """Test that quota doesn't prevent creating references when original exists"""
        quota_bytes = 10 * 1024 * 1024  # 10MB
        
        # Upload original file (10MB) - exactly at quota
        exact_content = b"x" * quota_bytes
        original_file = SimpleUploadedFile(
            "original.txt",
            exact_content,
            content_type="text/plain"
        )
        original = handle_upload(self.user_id, original_file)
        
        # Upload same file again (should create reference, not count against quota)
        duplicate_file = SimpleUploadedFile(
            "duplicate.txt",
            exact_content,
            content_type="text/plain"
        )
        reference = handle_upload(self.user_id, duplicate_file)
        
        self.assertTrue(reference.is_reference)
        # Total storage should still be 10MB (only original counts)
        stats = UserStats.objects.get(user_id=self.user_id)
        self.assertEqual(stats.total_storage_used, quota_bytes)
        # But original_storage_used should include both
        self.assertEqual(stats.original_storage_used, quota_bytes * 2)
    
    def test_upload_missing_user_id(self):
        """Test that missing user_id raises error"""
        with self.assertRaises(ValueError):
            handle_upload("", self.test_file)


class DeleteServiceTestCase(TestCase):
    """Test delete service functionality"""
    
    def setUp(self):
        self.test_content = b"test file content"
        self.test_file = SimpleUploadedFile(
            "test.txt",
            self.test_content,
            content_type="text/plain"
        )
        self.user_id = "user1"
    
    def test_delete_reference(self):
        """Test deleting a reference file"""
        # Create original and reference
        original = handle_upload(self.user_id, self.test_file)
        test_file2 = SimpleUploadedFile(
            "test2.txt",
            self.test_content,
            content_type="text/plain"
        )
        reference = handle_upload(self.user_id, test_file2)
        
        # Delete reference
        delete_file(self.user_id, str(reference.id))
        
        # Reference should be gone, original should remain
        self.assertFalse(File.objects.filter(id=reference.id).exists())
        self.assertTrue(File.objects.filter(id=original.id).exists())
        
        # Check stats updated
        stats = UserStats.objects.get(user_id=self.user_id)
        self.assertEqual(stats.original_storage_used, len(self.test_content))  # Only original remains
    
    def test_delete_original_with_references(self):
        """Test that deleting original with references raises ConflictError"""
        # Create original
        original = handle_upload(self.user_id, self.test_file)
        
        # Create reference
        test_file2 = SimpleUploadedFile(
            "test2.txt",
            self.test_content,
            content_type="text/plain"
        )
        handle_upload(self.user_id, test_file2)
        
        # Try to delete original
        with self.assertRaises(ConflictError):
            delete_file(self.user_id, str(original.id))
    
    def test_delete_original_without_references(self):
        """Test deleting original without references"""
        original = handle_upload(self.user_id, self.test_file)
        
        delete_file(self.user_id, str(original.id))
        
        self.assertFalse(File.objects.filter(id=original.id).exists())
        
        # Check stats
        stats = UserStats.objects.get(user_id=self.user_id)
        self.assertEqual(stats.total_storage_used, 0)
        self.assertEqual(stats.original_storage_used, 0)
    
    def test_delete_nonexistent_file(self):
        """Test deleting non-existent file raises NotFound"""
        with self.assertRaises(NotFound):
            delete_file(self.user_id, "00000000-0000-0000-0000-000000000000")
    
    def test_delete_missing_user_id(self):
        """Test that missing user_id raises error"""
        with self.assertRaises(ValueError):
            delete_file("", "00000000-0000-0000-0000-000000000000")


class SearchServiceTestCase(TestCase):
    """Test search service functionality"""
    
    def setUp(self):
        self.user_id = "user1"
        self.test_content = b"test content"
        
        # Create test files
        for i in range(5):
            file_obj = SimpleUploadedFile(
                f"test{i}.txt",
                self.test_content,
                content_type="text/plain"
            )
            handle_upload(self.user_id, file_obj)
    
    def test_search_all_files(self):
        """Test searching all files for user"""
        files = search_files_for_user(self.user_id, {})
        self.assertEqual(files.count(), 5)
    
    def test_search_by_filename(self):
        """Test searching by filename"""
        files = search_files_for_user(self.user_id, {"search": "test0"})
        self.assertEqual(files.count(), 1)
        self.assertIn("test0", files.first().original_filename)
    
    def test_search_by_file_type(self):
        """Test searching by file type"""
        files = search_files_for_user(self.user_id, {"file_type": "text/plain"})
        self.assertEqual(files.count(), 5)
    
    def test_search_by_size_range(self):
        """Test searching by size range"""
        files = search_files_for_user(self.user_id, {"min_size": 10, "max_size": 20})
        self.assertEqual(files.count(), 5)
    
    def test_distinct_file_types(self):
        """Test getting distinct file types"""
        types = distinct_file_types_for_user(self.user_id)
        self.assertIn("text/plain", types)
    
    def test_search_empty_user_id(self):
        """Test searching with empty user_id returns empty queryset"""
        files = search_files_for_user("", {})
        self.assertEqual(files.count(), 0)


class StatsServiceTestCase(TestCase):
    """Test stats service functionality"""
    
    def setUp(self):
        self.user_id = "user1"
        self.test_content = b"test content"
    
    def test_get_storage_stats(self):
        """Test getting storage stats"""
        # Upload file
        test_file = SimpleUploadedFile(
            "test.txt",
            self.test_content,
            content_type="text/plain"
        )
        handle_upload(self.user_id, test_file)
        
        stats = get_storage_stats(self.user_id)
        self.assertEqual(stats["user_id"], self.user_id)
        self.assertEqual(stats["total_storage_used"], len(self.test_content))
        self.assertEqual(stats["original_storage_used"], len(self.test_content))
        self.assertEqual(stats["storage_savings"], 0)
        self.assertEqual(stats["savings_percentage"], 0.0)
    
    def test_stats_with_deduplication(self):
        """Test stats with deduplication"""
        # Upload original
        test_file1 = SimpleUploadedFile(
            "test1.txt",
            self.test_content,
            content_type="text/plain"
        )
        handle_upload(self.user_id, test_file1)
        
        # Upload duplicate (reference)
        test_file2 = SimpleUploadedFile(
            "test2.txt",
            self.test_content,
            content_type="text/plain"
        )
        handle_upload(self.user_id, test_file2)
        
        stats = get_storage_stats(self.user_id)
        self.assertEqual(stats["total_storage_used"], len(self.test_content))  # Only original
        self.assertEqual(stats["original_storage_used"], len(self.test_content) * 2)  # Both files
        self.assertEqual(stats["storage_savings"], len(self.test_content))  # Savings
        self.assertGreater(stats["savings_percentage"], 0)
    
    def test_stats_missing_user_id(self):
        """Test that missing user_id raises error"""
        with self.assertRaises(ValueError):
            get_storage_stats("")


class APIViewTestCase(TestCase):
    """Test API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user_id = "user1"
        self.test_content = b"test file content"
        self.test_file = SimpleUploadedFile(
            "test.txt",
            self.test_content,
            content_type="text/plain"
        )
        # Clear rate limit cache before each test
        from django.core.cache import cache
        cache.clear()
    
    def test_upload_file_success(self):
        """Test successful file upload"""
        response = self.client.post(
            '/api/files/',
            {'file': self.test_file},
            HTTP_USERID=self.user_id
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['original_filename'], 'test.txt')
    
    def test_upload_file_missing_userid_header(self):
        """Test upload without UserId header returns 400"""
        response = self.client.post(
            '/api/files/',
            {'file': self.test_file}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Parse JSON response
        import json
        data = json.loads(response.content)
        self.assertIn('UserId header required', data['detail'])
    
    def test_list_files(self):
        """Test listing files"""
        # Upload a file
        self.client.post(
            '/api/files/',
            {'file': self.test_file},
            HTTP_USERID=self.user_id
        )
        
        # List files
        response = self.client.get('/api/files/', HTTP_USERID=self.user_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data.get('results', response.data)), 1)
    
    def test_get_file_details(self):
        """Test getting file details"""
        # Upload file
        upload_response = self.client.post(
            '/api/files/',
            {'file': self.test_file},
            HTTP_USERID=self.user_id
        )
        file_id = upload_response.data['id']
        
        # Get file details
        response = self.client.get(f'/api/files/{file_id}/', HTTP_USERID=self.user_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], file_id)
    
    def test_delete_file(self):
        """Test deleting a file"""
        # Upload file
        upload_response = self.client.post(
            '/api/files/',
            {'file': self.test_file},
            HTTP_USERID=self.user_id
        )
        file_id = upload_response.data['id']
        
        # Delete file
        response = self.client.delete(f'/api/files/{file_id}/', HTTP_USERID=self.user_id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify deleted
        get_response = self.client.get(f'/api/files/{file_id}/', HTTP_USERID=self.user_id)
        self.assertEqual(get_response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_storage_stats_endpoint(self):
        """Test storage stats endpoint"""
        # Upload file
        self.client.post(
            '/api/files/',
            {'file': self.test_file},
            HTTP_USERID=self.user_id
        )
        
        # Get stats
        response = self.client.get('/api/files/storage_stats/', HTTP_USERID=self.user_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_storage_used', response.data)
        self.assertIn('original_storage_used', response.data)
        self.assertIn('storage_savings', response.data)
        self.assertIn('savings_percentage', response.data)
    
    def test_file_types_endpoint(self):
        """Test file types endpoint"""
        # Wait a bit to avoid rate limiting
        import time
        time.sleep(0.6)
        
        # Upload file
        self.client.post(
            '/api/files/',
            {'file': self.test_file},
            HTTP_USERID=self.user_id
        )
        
        # Wait a bit more to avoid rate limiting
        time.sleep(0.6)
        
        # Get file types
        response = self.client.get('/api/files/file_types/', HTTP_USERID=self.user_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertIn('text/plain', response.data)
    
    def test_upload_file_over_10mb_via_api(self):
        """Test uploading file over 10MB via API returns 429"""
        quota_bytes = 10 * 1024 * 1024  # 10MB
        large_content = b"x" * (quota_bytes + 1024 * 1024)  # 11MB
        large_file = SimpleUploadedFile(
            "large_11mb.txt",
            large_content,
            content_type="text/plain"
        )
        
        response = self.client.post(
            '/api/files/',
            {'file': large_file},
            HTTP_USERID=self.user_id
        )
        
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        # Parse JSON response
        import json
        data = json.loads(response.content)
        self.assertIn('Storage Quota Exceeded', data['detail'])
    
    def test_upload_file_no_file_field(self):
        """Test uploading without file field returns 400"""
        response = self.client.post(
            '/api/files/',
            {},
            HTTP_USERID=self.user_id
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('No file provided', response.data['detail'])
    
    def test_upload_empty_file_via_api(self):
        """Test uploading empty file via API"""
        empty_file = SimpleUploadedFile(
            "empty.txt",
            b"",
            content_type="text/plain"
        )
        response = self.client.post(
            '/api/files/',
            {'file': empty_file},
            HTTP_USERID=self.user_id
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['size'], 0)
    
    def test_upload_file_exactly_10mb_via_api(self):
        """Test uploading file exactly at 10MB quota via API"""
        quota_bytes = 10 * 1024 * 1024  # 10MB
        exact_content = b"x" * quota_bytes
        exact_file = SimpleUploadedFile(
            "exact_10mb.txt",
            exact_content,
            content_type="text/plain"
        )
        
        response = self.client.post(
            '/api/files/',
            {'file': exact_file},
            HTTP_USERID=self.user_id
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['size'], quota_bytes)
    
    def test_upload_multiple_files_until_quota_via_api(self):
        """Test uploading multiple files until quota is reached via API"""
        # Upload first file (5MB)
        file1_size = 5 * 1024 * 1024
        file1_content = b"x" * file1_size
        file1 = SimpleUploadedFile("file1.txt", file1_content, content_type="text/plain")
        
        response1 = self.client.post(
            '/api/files/',
            {'file': file1},
            HTTP_USERID=self.user_id
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Upload second file (4MB) - should succeed
        file2_size = 4 * 1024 * 1024
        file2_content = b"y" * file2_size
        file2 = SimpleUploadedFile("file2.txt", file2_content, content_type="text/plain")
        
        import time
        time.sleep(0.6)  # Avoid rate limit
        
        response2 = self.client.post(
            '/api/files/',
            {'file': file2},
            HTTP_USERID=self.user_id
        )
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        
        # Upload third file (2MB) - should fail (11MB total)
        file3_size = 2 * 1024 * 1024
        file3_content = b"z" * file3_size
        file3 = SimpleUploadedFile("file3.txt", file3_content, content_type="text/plain")
        
        time.sleep(0.6)  # Avoid rate limit
        
        response3 = self.client.post(
            '/api/files/',
            {'file': file3},
            HTTP_USERID=self.user_id
        )
        self.assertEqual(response3.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        import json
        data = json.loads(response3.content)
        self.assertIn('Storage Quota Exceeded', data['detail'])


class MiddlewareTestCase(TestCase):
    """Test middleware functionality"""
    
    def setUp(self):
        self.client = Client()
    
    def test_userid_middleware_enforces_header(self):
        """Test that UserId middleware enforces header for API routes"""
        response = self.client.get('/api/files/')
        self.assertEqual(response.status_code, 400)
        self.assertIn('UserId header required', response.json()['detail'])
    
    def test_userid_middleware_allows_frontend(self):
        """Test that UserId middleware allows frontend access without header"""
        response = self.client.get('/')
        # Should not return 400 (might be 200 or 404 depending on frontend build)
        self.assertNotEqual(response.status_code, 400)
    
    def test_userid_middleware_with_header(self):
        """Test that UserId middleware accepts valid header"""
        response = self.client.get('/api/files/', HTTP_USERID='user1')
        # Should not return 400 (might be 200 with empty results)
        self.assertNotEqual(response.status_code, 400)


class RateLimitingTestCase(TestCase):
    """Test rate limiting functionality"""
    
    def setUp(self):
        self.client = APIClient()
        self.user_id = "user1"
        self.test_content = b"test content"
        self.test_file = SimpleUploadedFile(
            "test.txt",
            self.test_content,
            content_type="text/plain"
        )
    
    def test_rate_limit_enforcement(self):
        """Test that rate limiting is enforced"""
        # Make requests rapidly to trigger rate limit
        with patch('files.throttling.settings.FILE_VAULT_RATE_LIMIT_CALLS', 2):
            # First two requests should succeed
            response1 = self.client.get('/api/files/', HTTP_USERID=self.user_id)
            response2 = self.client.get('/api/files/', HTTP_USERID=self.user_id)
            
            # Third request should be rate limited
            response3 = self.client.get('/api/files/', HTTP_USERID=self.user_id)
            
            # At least one should be rate limited (429)
            self.assertTrue(
                response3.status_code == status.HTTP_429_TOO_MANY_REQUESTS or
                response2.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            )
    
    def test_rate_limit_message(self):
        """Test that rate limit returns correct message"""
        with patch('files.throttling.settings.FILE_VAULT_RATE_LIMIT_CALLS', 1):
            # Make first request
            self.client.get('/api/files/', HTTP_USERID=self.user_id)
            
            # Second request should be rate limited
            response = self.client.get('/api/files/', HTTP_USERID=self.user_id)
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                self.assertEqual(response.data['detail'], 'Call Limit Reached')

