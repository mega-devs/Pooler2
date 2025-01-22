from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.urls import reverse
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.management import call_command

from .models import UFWRule
from .admin import UFWRuleAdmin


class MockRequest:
    def __init__(self):
        self.META = {'HTTP_REFERER': '/admin/ufw_manager/ufwrule/'}


class UFWRuleModelTest(TestCase):
    def setUp(self):
        self.rule_data = {
            'direction': 'in',
            'protocol': 'tcp',
            'port': 80,
            'from_ip': '192.168.1.1',
            'to_ip': '10.0.0.1',
            'action': 'allow',
            'description': 'Test rule'
        }
        
    def test_rule_creation(self):
        """Test UFW rule creation with all fields"""
        rule = UFWRule.objects.create(**self.rule_data)
        self.assertEqual(rule.direction, self.rule_data['direction'])
        self.assertEqual(rule.protocol, self.rule_data['protocol'])
        self.assertEqual(rule.port, self.rule_data['port'])
        self.assertEqual(rule.action, self.rule_data['action'])

    def test_rule_string_representation(self):
        """Test string representation of UFW rule"""
        rule = UFWRule.objects.create(**self.rule_data)
        expected_str = f"in tcp port 80 from 192.168.1.1 to 10.0.0.1 - allow"
        self.assertEqual(str(rule), expected_str)

    def test_optional_fields(self):
        """Test UFW rule creation with optional fields omitted"""
        minimal_data = {
            'direction': 'in',
            'protocol': 'tcp',
            'action': 'allow'
        }
        rule = UFWRule.objects.create(**minimal_data)
        self.assertIsNone(rule.port)
        self.assertIsNone(rule.from_ip)
        self.assertIsNone(rule.to_ip)
        self.assertIsNone(rule.description)


class UFWRuleAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = UFWRuleAdmin(UFWRule, self.site)
        self.factory = RequestFactory()
        self.rule = UFWRule.objects.create(
            direction='in',
            protocol='tcp',
            port=80,
            action='allow'
        )

    def test_list_display(self):
        """Test admin list display configuration"""
        expected_fields = ('direction', 'protocol', 'port', 'from_ip', 'to_ip', 'action', 'description')
        self.assertEqual(self.admin.list_display, expected_fields)

    def test_list_filter(self):
        """Test admin list filter configuration"""
        expected_filters = ('direction', 'protocol', 'action')
        self.assertEqual(self.admin.list_filter, expected_filters)

    def test_search_fields(self):
        """Test admin search fields configuration"""
        expected_search = ('from_ip', 'to_ip', 'description')
        self.assertEqual(self.admin.search_fields, expected_search)

    def test_apply_rules_action(self):
        """Test apply rules admin action"""
        request = self.factory.get('/')
        request.META['HTTP_REFERER'] = '/admin/ufw_manager/ufwrule/'
        
        # Add message storage to request
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        with patch('django.core.management.call_command') as mock_call:
            response = self.admin.apply_rules(request)
            mock_call.assert_called_once_with('apply_ufw_rules')
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, '/admin/ufw_manager/ufwrule/')

    def test_changelist_view(self):
        """Test changelist view with apply rules button"""
        request = self.factory.get('/')
        response = self.admin.changelist_view(request)
        self.assertTrue(response.context_data['apply_rules_button'])
