from datetime import datetime
from django.test import TestCase, AsyncClient
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import AsyncMock, mock_open, patch, Mock
import json
import os

from .utils import is_valid_telegram_username, parse_messages, read_existing_messages, write_messages


class TelegramUrlsTest(TestCase):
    def test_urls_resolve_correctly(self):
        """Test URL pattern resolution"""
        urls_to_test = [
            ('upload_file_by_telegram', '/telegram/upload_file_by_telegram/'),
            ('download_files', '/telegram/download_files/'),
            ('get_combofiles_from_tg', '/telegram/get_combofiles_from_tg/'),
            ('get_from_tg', '/telegram/get_from_tg/')
        ]
        
        for url_name, expected_path in urls_to_test:
            url = reverse(f'telegram:{url_name}')
            self.assertEqual(url, expected_path)


class TelegramUtilsTest(TestCase):
    def test_valid_telegram_username(self):
        """Test Telegram username validation"""
        valid_usernames = [
            '@validuser',
            'https://t.me/validuser',
            'validuser12345'
        ]
        invalid_usernames = [
            '@inv',  # too short
            'invalid@user',  # invalid character
            'https://invalid.com/user'  # wrong domain
        ]
        
        for username in valid_usernames:
            self.assertTrue(is_valid_telegram_username(username))
            
        for username in invalid_usernames:
            self.assertFalse(is_valid_telegram_username(username))    

    @patch('aiofiles.open')
    @patch('os.path.exists')
    async def test_read_existing_messages(self, mock_exists, mock_open):
        """Test reading messages from file"""
        test_messages = [{'text': 'test message'}]
        mock_exists.return_value = True
        mock_open.return_value.__aenter__.return_value.read.return_value = json.dumps(test_messages)
        
        result = await read_existing_messages('test.json')
        self.assertEqual(result, test_messages)

    @patch('aiofiles.open')
    async def test_write_messages(self, mock_open):
        """Test writing messages to file"""
        test_messages = [{'text': 'test message'}]
        mock_file = AsyncMock()
        mock_open.return_value.__aenter__.return_value = mock_file
        
        await write_messages('test.json', test_messages)
        mock_file.write.assert_called_once()

    @patch('telethon.TelegramClient', new_callable=AsyncMock)
    async def test_parse_messages(self, mock_client):
        """Test parsing messages from Telegram channel"""
        mock_message = AsyncMock()
        mock_message.sender_id = 12345
        mock_message.text = "Test message"
        mock_message.date = datetime.now()
        mock_message.media = None

        async def async_generator():
            yield mock_message

        mock_client.iter_messages = AsyncMock(return_value=async_generator())

        response = await parse_messages(mock_client, "@testchannel")

        expected_messages = [
            {
                'sender': mock_message.sender_id,
                'date': mock_message.date.strftime('%Y-%m-%d %H:%M:%S'),
                'text': mock_message.text,
            }
        ]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), expected_messages)

        mock_client.iter_messages.assert_called_once_with("@testchannel", limit=10)

class TelegramViewsTest(APITestCase):
    def setUp(self):
        self.valid_channel = '@testchannel'
        self.valid_token = '7430783381:AAFEw0LJsRZj8598mOGQ8wh9REXIvVqAczQ'
        self.get_combofiles_from_tg_url = reverse('telegram:get_combofiles_from_tg')
        self.get_from_tg_url = reverse('telegram:get_from_tg')

    @patch('telegram.views.TelegramClient')
    def test_telegram_add_channel(self, mock_client):
        """Test adding Telegram channel"""
        mock_telegram_instance = AsyncMock()
        mock_client.return_value = mock_telegram_instance

        mock_telegram_instance.add_channel.return_value = {'status': 'success'}

        url = reverse('telegram:upload_file_by_telegram')
        data = {'channel': self.valid_channel}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)
        
    @patch('telegram.views.TelegramClient')
    def test_download_files_from_tg(self, mock_client):
        """Test downloading files from Telegram"""
        
        url = reverse('telegram:download_files')
        data = {
            'links': ['https://t.me/test/1'],
            'date': '2024-01-22',
            'max_size': 10
        }

        mock_client.download_files.return_value = {'status': 'success', 'files': ['file1.txt']}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('files', response.json())

    @patch("builtins.open", new_callable=mock_open, read_data="link1\nlink2\nlink3")
    @patch("telegram.views.download_files_from_tg", new_callable=AsyncMock)
    @patch('telegram.views.TelegramClient')
    def test_get_combofiles_from_tg(self, mock_download_files, mock_open, mock_client):
        """Test getting combo files from Telegram"""
        mock_download_files.return_value = ["/path/to/file1.txt", "/path/to/file2.txt"]

        response = self.client.get(self.get_combofiles_from_tg_url, {"date": "2025-01-01", "max_size": "100"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_from_tg_invalid_date(self):
        """Test getting files with invalid date format"""
        url = reverse('telegram:get_from_tg')
        response = self.client.get(url, {'date': 'invalid-date'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("builtins.open", new_callable=mock_open, read_data="link1\nlink2\nlink3")
    @patch("telegram.views.download_files_from_tg", new_callable=AsyncMock)
    @patch('telegram.views.TelegramClient')
    def test_get_from_tg_success(self, mock_download_files, mock_open, mock_client):
        mock_download_files.return_value = ["/path/to/file1.txt", "/path/to/file2.txt"]

        response = self.client.get(self.get_from_tg_url, {"date": "2025-01-01", "max_size": "100"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
