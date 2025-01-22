from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from .models import ExtractedData, UploadedFile
from unittest.mock import patch, MagicMock
import os


class FilesViewsTestCase(APITestCase):
    def setUp(self):
        # Create test user and token
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        # Create uploaded file first
        self.uploaded_file = UploadedFile.objects.create(
            filename='test.txt',
            file_path='/test/path/test.txt',
            country='US',
            origin='MANUAL',
            user=self.user
        )

        # Then create extracted data with reference to uploaded file
        self.extracted_data = ExtractedData.objects.create(
            email='test@example.com',
            password='testpass',
            provider='gmail',
            country='US',
            filename='test.txt',
            line_number=1,
            upload_origin='MANUAL',
            uploaded_file=self.uploaded_file  # Add this reference
        )
        
    def test_panel_table(self):
        """Test panel_table view returns correct data structure and pagination"""
        url = reverse('files:panel_table')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.json())
        self.assertIn('countries', response.json())
        self.assertIn('show_all', response.json())

    def test_upload_combofile(self):
        """Test file upload functionality"""
        url = reverse('files:upload_combofile')
        file_content = b'test content'
        uploaded_file = SimpleUploadedFile('test.txt', file_content)
        
        response = self.client.post(url, {'file': uploaded_file}, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.json())
        self.assertIn('file_id', response.json())

    def test_download_file(self):
        """Test file download functionality"""
        filename = 'test.txt'
        url = reverse('files:download_file', kwargs={'filename': filename})
        
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b'test content'
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('filename', response.json())
            self.assertIn('download_url', response.json())

    def test_uploaded_files_list(self):
        """Test listing uploaded files"""
        url = reverse('files:uploaded_files_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('files', response.json())
        self.assertTrue(len(response.json()['files']) > 0)

    def test_uploaded_file_update(self):
        """Test updating uploaded file information"""
        url = reverse('files:uploaded_file_update', kwargs={'pk': self.uploaded_file.pk})
        update_data = {
            'filename': 'updated.txt',
            'status': 'processed'
        }
        
        response = self.client.put(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('file', response.json())
        self.assertEqual(response.json()['file']['filename'], 'updated.txt')

    def test_uploaded_file_delete(self):
        """Test deleting uploaded file"""
        url = reverse('files:uploaded_file_delete', kwargs={'pk': self.uploaded_file.pk})
        
        with patch('os.remove') as mock_remove:
            response = self.client.delete(url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('message', response.json())
            mock_remove.assert_called()

    def test_download_txt(self):
        """Test downloading data in TXT format"""
        url = reverse('files:download_txt')
        self.client.session['current_data_ids'] = [self.extracted_data.id]
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.json())
        self.assertEqual(len(response.json()['data']), 1)

    def test_extracted_data_update(self):
        """Test updating extracted data"""
        url = reverse('files:extracted_data_update', kwargs={'pk': self.extracted_data.pk})
        update_data = {
            'email': 'updated@example.com',
            'password': 'newpass'
        }
        
        response = self.client.post(url, update_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['status'], 'success')

    def test_extracted_data_delete(self):
        """Test deleting extracted data"""
        url = reverse('files:extracted_data_delete', kwargs={'pk': self.extracted_data.pk})
        
        with patch('os.remove') as mock_remove:
            response = self.client.post(url)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()['status'], 'success')

    def test_viewsets(self):
        """Test ModelViewSet endpoints"""
        # Test ExtractedData viewset
        url = reverse('files:extracteddata-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test UploadedFile viewset
        url = reverse('files:uploadedfile-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        