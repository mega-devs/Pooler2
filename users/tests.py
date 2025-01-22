from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .admin import CustomUserAdmin
from .serializers import UserSignupSerializer, UserSigninSerializer


class UserAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = CustomUserAdmin(User, self.site)
        self.user = User.objects.create_user(
            username='testadmin',
            password='adminpass123'
        )
        self.superuser = User.objects.create_superuser(
            username='superadmin',
            password='superpass123'
        )

    def test_list_display(self):
        """Verify admin list display configuration"""
        expected_fields = ('username', 'is_active', 'is_staff', 'is_superuser')
        self.assertEqual(self.admin.list_display, expected_fields)

    def test_fieldsets(self):
        """Verify admin fieldsets configuration"""
        self.assertEqual(len(self.admin.fieldsets), 2)
        self.assertIn('Permissions', [fieldset[0] for fieldset in self.admin.fieldsets])

    def test_add_fieldsets(self):
        """Verify add form fieldsets configuration"""
        expected_fields = ('username', 'password1', 'password2')
        self.assertEqual(
            self.admin.add_fieldsets[0][1]['fields'],
            expected_fields
        )


class UserModelTest(TestCase):
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }

    def test_create_user(self):
        """Test regular user creation"""
        user = User.objects.create_user(**self.user_data)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_superuser(self):
        """Test superuser creation"""
        superuser = User.objects.create_superuser(**self.user_data)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_active)

    def test_user_str_representation(self):
        """Test string representation of user"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), self.user_data['username'])


class UserSerializerTest(TestCase):
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }

    def test_signup_serializer(self):
        """Test user signup serializer"""
        serializer = UserSignupSerializer(data=self.user_data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertEqual(user.username, self.user_data['username'])

    def test_signin_serializer(self):
        """Test user signin serializer"""
        serializer = UserSigninSerializer(data=self.user_data)
        self.assertTrue(serializer.is_valid())


class UserViewsTest(APITestCase):
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        self.user = User.objects.create_user(**self.user_data)
        self.refresh = RefreshToken.for_user(self.user)
        self.access_token = str(self.refresh.access_token)

    def test_signup_view(self):
        """Test user signup endpoint"""
        url = reverse('signup')
        response = self.client.post(url, {
            'username': 'newuser',
            'password': 'newpass123'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_signin_view(self):
        """Test user signin endpoint"""
        url = reverse('signin')
        response = self.client.post(url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('session_key', response.data)

    def test_logout_view(self):
        """Test user logout endpoint"""
        url = reverse('custom-logout')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_details_view(self):
        """Test user details endpoint"""
        url = reverse('details', kwargs={'user_id': self.user.id})  # Updated URL name
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all expected fields are present
        expected_fields = {'id', 'username', 'email', 'last_login', 'role'}
        self.assertEqual(set(response.data.keys()), expected_fields)
        
        # Verify field values
        self.assertEqual(response.data['id'], self.user.id)
        self.assertEqual(response.data['username'], self.user.username)
        self.assertEqual(response.data['role'], 'user')  # Since this is a regular user

    def test_get_session_by_token(self):
        """Test session retrieval by token"""
        url = reverse('get_session_by_token', kwargs={'token': self.access_token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all expected fields are present
        expected_fields = {'user_id', 'session_key', 'username'}
        self.assertEqual(set(response.json().keys()), expected_fields)
        
        # Verify field values
        self.assertEqual(response.json()['user_id'], self.user.id)
        self.assertEqual(response.json()['username'], self.user.username)
        self.assertTrue(response.json()['session_key'])
   