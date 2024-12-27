from django.test import TestCase
from .models import EmailCheck


class EmailCheckModelTest(TestCase):
    def setUp(self):
        EmailCheck.objects.create(email="test@example.com", status="valid", check_type="SMTP")

    def test_email_check_creation(self):
        email_check = EmailCheck.objects.get(email="test@example.com")
        self.assertEqual(email_check.status, "valid")
        self.assertEqual(email_check.check_type, "SMTP")



