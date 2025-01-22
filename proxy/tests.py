from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.utils import timezone
from unittest.mock import Mock, patch
from rest_framework.test import APITestCase
from concurrent.futures import ThreadPoolExecutor

from .admin import ProxyAdmin
from .models import Proxy
from .serializers import ProxySerizalizer, TextFileUploadSerializer
from .checker import ProxyChecker
from .tasks import check_proxy_health


class ProxyAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = ProxyAdmin(Proxy, self.site)
        self.proxy = Proxy.objects.create(
            host='192.168.1.1',
            port=8080,
            is_active=True,
            country='United States',
            country_code='US',
            anonymity='Elite',
            timeout=100
        )

    def test_list_display(self):
        self.assertEqual(
            self.admin.list_display,
            ('host', 'port', 'is_active', 'country', 'country_code', 'anonymity', 'timeout')
        )

    def test_list_filter(self):
        self.assertEqual(
            self.admin.list_filter,
            ('is_active', 'country', 'anonymity')
        )

    def test_search_fields(self):
        self.assertEqual(
            self.admin.search_fields,
            ('host', 'country', 'country_code')
        )


class ProxyModelTest(TestCase):
    def setUp(self):
        self.proxy_data = {
            'host': '192.168.1.1',
            'port': 8080,
            'is_active': True,
            'country': 'United States',
            'country_code': 'US',
            'anonymity': 'Elite',
            'timeout': 100,
            'username': 'user',
            'password': 'pass'
        }
        
    def test_proxy_creation(self):
        proxy = Proxy.objects.create(**self.proxy_data)
        self.assertEqual(proxy.host, self.proxy_data['host'])
        self.assertEqual(proxy.port, self.proxy_data['port'])
        self.assertEqual(proxy.country_code, self.proxy_data['country_code'])

    def test_proxy_str_representation(self):
        proxy = Proxy.objects.create(**self.proxy_data)
        expected_str = f"{proxy.host}:{proxy.port}"
        self.assertEqual(str(proxy), expected_str)


class ProxySerializerTest(APITestCase):
    def setUp(self):
        self.proxy_data = {
            'host': '192.168.1.1',
            'port': 8080,
            'username': 'user',
            'password': 'pass'
        }
        
    def test_proxy_serializer_valid(self):
        serializer = ProxySerizalizer(data=self.proxy_data)
        self.assertTrue(serializer.is_valid())
        
    def test_proxy_serializer_missing_required(self):
        invalid_data = {'host': '192.168.1.1'}
        serializer = ProxySerizalizer(data=invalid_data)
        self.assertFalse(serializer.is_valid())

class TextFileUploadSerializerTest(APITestCase):
    def test_file_upload_serializer(self):
        mock_file = Mock()
        mock_file.name = 'test.txt'
        serializer = TextFileUploadSerializer(data={'file': mock_file})
        self.assertTrue(serializer.is_valid())


class ProxyCheckerTest(TestCase):
    def setUp(self):
        self.checker = ProxyChecker()
        
    @patch('proxy.checker.pycurl.Curl')
    def test_get_ip(self, mock_curl):
        mock_curl.return_value.getinfo.return_value = 200
        result = self.checker.get_ip()
        self.assertIsInstance(result, str)
        
    def test_parse_anonymity(self):
        transparent_response = f"Some headers with {self.checker.ip}"
        self.assertEqual(self.checker.parse_anonymity(transparent_response), 'Transparent')
        
        anonymous_response = "Some headers with VIA and X-FORWARDED-FOR"
        self.assertEqual(self.checker.parse_anonymity(anonymous_response), 'Anonymous')
        
        elite_response = "Clean headers"
        self.assertEqual(self.checker.parse_anonymity(elite_response), 'Elite')

    @patch('proxy.checker.ProxyChecker.send_query')
    def test_check_proxy(self, mock_send_query):
        mock_send_query.return_value = {
            'timeout': 100,
            'response': 'Test response'
        }
        result = self.checker.check_proxy('192.168.1.1:8080')
        self.assertIsInstance(result, dict)
        self.assertIn('protocols', result)
        self.assertIn('anonymity', result)

class ProxyTasksTest(TestCase):
    @patch('proxy.tasks.check_single_proxy')
    def test_check_proxy_health(self, mock_check):
        proxy = Proxy.objects.create(
            host='192.168.1.1',
            port=8080
        )
        
        check_proxy_health()
        mock_check.assert_called_once()
        
    @patch('concurrent.futures.ThreadPoolExecutor')
    def test_thread_pool_execution(self, mock_executor):
        mock_executor.return_value.__enter__.return_value.submit.return_value.result.return_value = True
        check_proxy_health()
        mock_executor.assert_called_once_with(max_workers=100)
