
import tempfile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, Mock
import os
import zipfile

from users.models import User

from .models import UploadedFile, ExtractedData
from .tasks import async_handle_archive, async_process_uploaded_files
from .service import (
    extract_country_from_filename, remove_duplicate_lines, 
    handle_archive, determine_origin, process_uploaded_files
)
from .serializers import ExtractedDataSerializer, UploadedFileSerializer
from .resources import UploadedFileResource, ExtractedDataResource


class FileTasksTest(TestCase):
    def setUp(self):
        # Create a temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        # Define paths
        self.file_path = os.path.join(self.temp_dir, 'test.zip')

        # Create a zip archive in the temp directory
        with zipfile.ZipFile(self.file_path, 'w') as zipf:
            zipf.writestr('test.txt', 'This is a test file.')

        self.uploaded_file = UploadedFile.objects.create(
            filename='test.zip',
            file_path=self.file_path,
            user=self.user
        )

    def tearDown(self):
        # Cleanup temporary directory
        if os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.temp_dir)

    @patch('files.tasks.handle_archive')
    def test_async_handle_archive(self, mock_handle):
        """Test async archive handling task."""
        file_path = self.file_path
        save_path = self.temp_dir
        
        async_handle_archive(file_path, save_path)
        mock_handle.assert_called_once_with(file_path)

    @patch('files.tasks.process_uploaded_files')
    def test_async_process_uploaded_files(self, mock_process):
        """Test async file processing task."""
        base_dir = self.temp_dir

        async_process_uploaded_files(base_dir, self.uploaded_file.id)
        mock_process.assert_called_once_with(base_dir, self.uploaded_file)


class FileServiceTest(TestCase):
    def setUp(self):
        self.test_file_path = 'test_file.txt'
        
    def test_extract_country_from_filename(self):
        """Test country code extraction"""
        test_cases = [
            ('file_US_test.txt', 'US'),
            ('combo_GB_2023.zip', 'GB'),
            ('invalid.txt', None)
        ]
        for filename, expected in test_cases:
            result = extract_country_from_filename(filename)
            self.assertEqual(result, expected)

    @patch('builtins.open')
    def test_remove_duplicate_lines(self, mock_open):
        """Test duplicate line removal"""
        mock_open.return_value.__enter__.return_value.read.return_value = b'line1\nline1\nline2'
        result = remove_duplicate_lines(self.test_file_path)
        self.assertEqual(result, 1)

    def test_determine_origin(self):
        """Test file origin determination"""
        test_cases = [
            ('smtp_file.txt', 'SMTP'),
            ('imap_data.zip', 'IMAP'),
            ('telegram_export.csv', 'TELEGRAM'),
            ('other.txt', 'MANUAL')
        ]
        for filename, expected in test_cases:
            result = determine_origin(filename)
            self.assertEqual(result, expected)


class FileUrlsTest(TestCase):
    def test_urls_resolve_correctly(self):
        """Test URL pattern resolution"""
        urls_to_test = [
            ('uploaded_files_list', '/files/'),
            ('upload_combofile', '/files/upload/'),
            ('panel_table', '/files/panel/tables/')
        ]
        for name, path in urls_to_test:
            url = reverse(f'files:{name}')
            self.assertEqual(url, path)


class FileViewsTest(APITestCase):
    def setUp(self):
        # Create a temporary directory
        self.temp_dir = tempfile.mkdtemp()

        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        # Create some test data
        self.file_path = os.path.join(self.temp_dir, 'test.txt')
        with open(self.file_path, 'w') as f:
            f.write('Sample test file content.')

        self.uploaded_file = UploadedFile.objects.create(
            filename='test.txt',
            file_path=self.file_path,
            user=self.user
        )
        
        self.extracted_data = ExtractedData.objects.create(
            email='test@test.com',
            password='testpass',
            provider='test',
            uploaded_file=self.uploaded_file,
            upload_origin='MANUAL'
        )

    def tearDown(self):
        # Cleanup temporary directory
        if os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.temp_dir)

    def test_panel_table(self):
        """Test panel table data retrieval."""
        url = reverse('files:panel_table')
        response = self.client.get(url)
        
        # Convert JsonResponse to dict
        response_data = response.json()
        
        # Verify response status and structure
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response_data)
        
        # Verify data content
        self.assertTrue(isinstance(response_data['data'], list))
        self.assertEqual(len(response_data['data']), 1)
        
        # Verify expected fields in response
        expected_fields = {
            'data', 'countries', 'show_all', 
            'random_count', 'total_pages'
        }
        self.assertTrue(
            expected_fields.issubset(set(response_data.keys())),
            "Response is missing one or more expected fields."
        )

    def test_upload_combofile(self):
        """Test combo file upload functionality."""
        url = reverse('files:upload_combofile')
        
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(suffix='.txt') as temp_file:
            temp_file.write(b'test@gmail.com:password123')
            temp_file.seek(0)
            
            # Prepare file upload data
            upload_data = {
                'file': temp_file
            }
            
            response = self.client.post(url, upload_data, format='multipart')
            response_data = response.json()
            
            # Verify response status and structure
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertIn('message', response_data)
            self.assertIn('file_id', response_data)
            
            # Verify file was created in database
            file_id = response_data['file_id']
            uploaded_file = UploadedFile.objects.get(id=file_id)
            self.assertEqual(uploaded_file.user, self.user)
            self.assertTrue(os.path.exists(uploaded_file.file_path))
    
    def test_upload_combofile_no_file(self):
        """Test combo file upload with no file."""
        url = reverse('files:upload_combofile')
        response = self.client.post(url, {}, format='multipart')
            
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
        self.assertEqual(
            response.json().get('error', ''), 
            'No file part', 
            "Expected 'No file part' error message."
        )

        
class FileSerializerTest(TestCase):
    def setUp(self):
        # Create a temporary directory
        self.temp_dir = tempfile.mkdtemp()

        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        # Create some test data
        self.file_path = os.path.join(self.temp_dir, 'test.txt')
        with open(self.file_path, 'w') as f:
            f.write('Sample test file content.')
        
        # Setup data for UploadedFile
        self.file_data = {
            'filename': 'test.txt',
            'file_path': self.file_path,
            'user': self.user.id,
            'origin': 'MANUAL'
        }
        
    def test_uploaded_file_serializer(self):
        """Test UploadedFile serializer"""
        serializer = UploadedFileSerializer(data=self.file_data)
        self.assertTrue(serializer.is_valid())
        
    def test_extracted_data_serializer(self):
        """Test ExtractedData serializer"""
        # Create uploaded file first
        uploaded_file = UploadedFile.objects.create(
            filename='test.txt',
            file_path=self.file_path,
            user=self.user
        )
        
        data = {
            'email': 'test@test.com',
            'password': 'testpass',
            'provider': 'test',
            'uploaded_file': uploaded_file.id,
            'upload_origin': 'MANUAL'
        }
        serializer = ExtractedDataSerializer(data=data)
        self.assertTrue(serializer.is_valid())


class FileResourceTest(TestCase):
    def setUp(self):
                # Create a temporary directory
        self.temp_dir = tempfile.mkdtemp()

        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        # Create some test data
        self.file_path = os.path.join(self.temp_dir, 'test.txt')
        with open(self.file_path, 'w') as f:
            f.write('Sample test file content.')
        
        self.uploaded_file = UploadedFile.objects.create(
            filename='test.txt',
            file_path=self.file_path,
            user=self.user
        )
        
        self.extracted_data = ExtractedData.objects.create(
            email='test@test.com',
            password='testpass',
            provider='test',
            uploaded_file=self.uploaded_file,
            upload_origin='MANUAL'
        )

    def test_uploaded_file_resource(self):
        """Test UploadedFile export resource"""
        resource = UploadedFileResource()
        dataset = resource.export()
        self.assertEqual(len(dataset), 1)

    def test_extracted_data_resource(self):
        """Test ExtractedData export resource"""
        resource = ExtractedDataResource()
        dataset = resource.export()
        exported_data = dataset.dict[0]
        self.assertEqual(
            exported_data['uploaded_file_name'],
            self.uploaded_file.filename
        )
