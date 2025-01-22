from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from files.models import ExtractedData
from unittest.mock import patch
import json


class PoolerViewsTestCase(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

    def test_redirect_to_panel(self):
        """
        Test that redirect_to_panel returns the correct redirect url.
        """
        url = reverse('pooler:redirect_to_panel')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('redirect', response.json())
    def test_panel(self):
        """
        Test that panel view returns the correct statistics.
        """
        # Create some sample data
        ExtractedData.objects.create(smtp_is_valid=True, imap_is_valid=True)
        ExtractedData.objects.create(smtp_is_valid=False, imap_is_valid=False)

        url = reverse('pooler:panel')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        expected_keys = [
            'active_page',
            'count_of_smtp_valid',
            'count_of_smtp_invalid',
            'count_of_smtp',
            'count_of_imap',
            'count_imap_valid',
            'count_imap_invalid',
            'smtp_checked',
            'imap_checked'
        ]
        for key in expected_keys:
            self.assertIn(key, data)

        # Verify counts
        self.assertEqual(data['count_of_smtp_valid'], 1)
        self.assertEqual(data['count_of_smtp_invalid'], 1)
        self.assertEqual(data['count_of_imap'], 2)
        self.assertEqual(data['smtp_checked'], 2)
        self.assertEqual(data['imap_checked'], 2)

    def test_panel_settings_get(self):
        """
        Test GET request to panel_settings returns active_page as 'settings'.
        """
        url = reverse('pooler:panel_settings')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data.get('active_page'), 'settings')

    def test_panel_settings_post(self):
        """
        Test POST request to panel_settings returns active_page as 'settings'.
        """
        url = reverse('pooler:panel_settings')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data.get('active_page'), 'settings')

    def test_upload_file_by_url_no_url(self):
        """
        Test that uploading without a URL returns appropriate error.
        """
        url = reverse('pooler:upload_file_by_url')
        response = self.client.post(url, data={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json().get('error'), 'No URL provided')

    @patch('pooler.views.requests.get')
    def test_upload_file_by_url_success(self, mock_get):
        """
        Test successful upload of a file via URL.
        """
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b'Test content'
        url = reverse('pooler:upload_file_by_url')
        response = self.client.post(url, data={'url': 'http://example.com/testfile.txt'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get('filename'), 'testfile.txt')

    def test_upload_file_by_url_file_not_found(self):
        """
        Test that a 404 response from the URL returns an error.
        """
        url = reverse('pooler:upload_file_by_url')
        with patch('pooler.views.requests.get') as mock_get:
            mock_get.return_value.status_code = 404
            response = self.client.post(url, data={'url': 'http://example.com/nonexistent.txt'})
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(response.json().get('error'), 'File not found')

    def test_check_smtp_view(self):
        """
        Test that check_smtp_view runs successfully.
        """
        url = reverse('pooler:check_smtp_view')
        with patch('pooler.views.check_smtp_emails_from_db') as mock_task:
            mock_task.return_value = None
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json().get('status'), 'success')

    def test_check_imap_view(self):
        """
        Test that check_imap_view runs successfully.
        """
        url = reverse('pooler:check_imap_view')
        with patch('pooler.views.check_imap_emails_from_db') as mock_task:
            mock_task.return_value = None
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json().get('status'), 'success')

    @patch('pooler.views.read_logs')
    def test_get_logs(self, mock_read_logs):
        """
        Test retrieval of logs.
        """
        mock_read_logs.return_value = {'logs': []}
        url = reverse('pooler:get_logs')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('logs', response.json())

    def test_clear_temp_logs(self):
        """
        Test that temporary logs are cleared successfully.
        """
        url = reverse('pooler:clear_temp_logs')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get('message'), 'Logs cleared successfully')

    @patch('os.remove')
    def test_clear_full_logs(self, mock_remove):
        """
        Test that full logs are cleared successfully.
        """
        url = reverse('pooler:clear_full_logs')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get('message'), 'Logs cleared successfully')

    def test_download_logs_file(self):
        """
        Test downloading of log files.
        """
        url = reverse('pooler:download_logs_file')
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = 'log content'
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('smtp', response.json())
            self.assertIn('imap', response.json())
