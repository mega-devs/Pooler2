import os
import tempfile
from django.urls import reverse
from pooler.utils import LogFormatter, chunks, extract_country_from_filename, get_email_bd_data, imapCheck, read_logs
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from files.models import ExtractedData, UploadedFile
from unittest.mock import patch


# for testing pooler/views.py
class PoolerViewsTestCase(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        
        # Create a temporary directory
        self.temp_dir = tempfile.mkdtemp()

        # Create some test data
        self.file_path = os.path.join(self.temp_dir, 'test.txt')
        with open(self.file_path, 'w') as f:
            f.write('Sample test file content.')

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
        uploaded_file = UploadedFile.objects.create(
            filename="test.txt",
            file_path=self.file_path,
            user=self.user)

        ExtractedData.objects.create(
            smtp_is_valid=True, 
            imap_is_valid=True,
            uploaded_file=uploaded_file,
            provider="test.com",
            email="test1@test.com",
            password="pass123")
        
        ExtractedData.objects.create(
            smtp_is_valid=False, 
            imap_is_valid=False,
            uploaded_file=uploaded_file,
            provider="test.com", 
            email="test2@test.com",
            password="pass456")

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

        self.assertEqual(data['count_of_smtp_valid'], 1)
        self.assertEqual(data['count_of_smtp_invalid'], 1)
        self.assertEqual(data['count_of_imap'], 2)
        self.assertEqual(data['smtp_checked'], 2)
        self.assertEqual(data['imap_checked'], 2)

    def test_panel_settings_get(self):
        """
        Test GET request to panel_settings returns active_page as 'settings'.
        """
        self.client.force_authenticate(user=self.user)
        url = reverse('pooler:panel_settings')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data.get('active_page'), 'settings')

    def test_panel_settings_post(self):
        """
        Test POST request to panel_settings returns active_page as 'settings'.
        """
        self.client.force_authenticate(user=self.user)        
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
            response = self.client.post(url, data={'url': 'http://smth.com/none.txt'})
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(response.json().get('error'), 'File not found')

    def test_check_smtp_view(self):
        """
        Test that check_smtp_view runs successfully.
        """
        url = reverse('pooler:checking_smtp')
        with patch('pooler.views.check_smtp_emails_from_db') as mock_task:
            async def mock_coro():
                return None
            mock_task.return_value = mock_coro()
            
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json().get('status'), 'success')

    def test_check_imap_view(self):
        """
        Test that check_imap_view runs successfully.
        """
        url = reverse('pooler:checking_imap')
        with patch('pooler.views.check_imap_emails_from_db') as mock_task:
            async def testing():
                return None
            mock_task.return_value = testing()
            
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


# for testing pooler/utils.py
class PoolerUtilsTestCase(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword')
        
        # Create a temporary directory
        self.temp_dir = tempfile.mkdtemp()

        # Create some test data
        self.file_path = os.path.join(self.temp_dir, 'test.txt')
        with open(self.file_path, 'w') as f:
            f.write('Sample test file content.')

        
        self.sample_email = "test@example.com"
        self.sample_password = "testpass123"
        self.sample_server = "smtp.example.com"

    def test_chunks_function(self):
        """Test the chunks utility function"""
        test_list = [1, 2, 3, 4, 5, 6, 7]
        chunk_size = 3
        result = list(chunks(test_list, chunk_size))
        self.assertEqual(result, [[1, 2, 3], [4, 5, 6], [7]])

    def test_extract_country_from_filename(self):
        """Test country code extraction from filename"""
        test_cases = [
            ("combo_US_2023.txt", "US"),
            ("emails_GB_valid.zip", "GB"),
            ("test_FR_123.csv", "FR"),
            ("invalid_filename.txt", None)
        ]
        for filename, expected in test_cases:
            result = extract_country_from_filename(filename)
            self.assertEqual(result, expected)

    def test_get_email_bd_data(self):
        """Test retrieval of email data from database"""
        uploaded_file = UploadedFile.objects.create(
            filename="test.txt",
            file_path=self.file_path,
            user=self.user)

        ExtractedData.objects.create(
            provider="smtp.test.com",
            email="test1@test.com", 
            password="pass123",
            uploaded_file=uploaded_file
        )
        ExtractedData.objects.create(
            provider="smtp.example.com",
            email="test2@example.com",
            password="pass456",
            uploaded_file=uploaded_file
        )
        
        result = get_email_bd_data()
        self.assertEqual(len(result), 2)
        self.assertTrue(all(
            key in result[0] for key in ['smtp_server', 'email', 'password']
        ))

    def test_imap_check(self):
        """Test IMAP connection checker"""
        with patch('imaplib.IMAP4_SSL') as mock_imap:
            mock_imap.return_value.login.return_value = True
            result = imapCheck(self.sample_email, self.sample_password, self.sample_server)
            self.assertTrue(result)

            mock_imap.side_effect = Exception("Connection failed")
            result = imapCheck(self.sample_email, self.sample_password, self.sample_server)
            self.assertFalse(result)

    def test_log_formatter(self):
        """Test log formatting utilities"""
        thread_num = "Thread-1"
        timestamp = "2023-01-01 12:00:00"
        server = "smtp.test.com"
        user = "test@test.com"
        port = 587
        
        smtp_log = LogFormatter.format_smtp_log(
            thread_num=thread_num,
            timestamp=timestamp,
            server=server,
            user=user,
            port=port,
            response="250 OK",
            status="VALID"
        )
        self.assertIn("VALID", smtp_log)
        self.assertIn(thread_num, smtp_log)
        
        imap_log = LogFormatter.format_imap_log(
            thread_num=thread_num,
            timestamp=timestamp,
            server=server,
            user=user,
            port=port,
            status="VALID"
        )
        self.assertIn("VALID", imap_log)

    async def test_read_logs(self):
        """Test log reading functionality"""
        with patch('aiofiles.open') as mock_open:
            mock_open.return_value.__aenter__.return_value.readlines.return_value = [
                "log line 1\n",
                "log line 2\n"
            ]
            result = await read_logs(0)
            self.assertIn('smtp_logs', result)
            self.assertIn('imap_logs', result)
            self.assertEqual(result['n'], 2)
