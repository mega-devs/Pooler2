import pytest
from rest_framework.test import APIClient
from django.urls import reverse

@pytest.mark.django_db
def test_user_login():
    client = APIClient()
    login_data = {
        'username': 'root',
        'password': 'root'
    }
    response = client.post(reverse('token_obtain_pair'), login_data)
    assert response.status_code == 200
    assert 'access' in response.data
