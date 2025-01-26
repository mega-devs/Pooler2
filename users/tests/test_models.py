import pytest
from users.models import User


@pytest.mark.django_db
def test_create_user():
    user = User.objects.create_user(
        username='root', 
        email='root@example.com', 
        password='root'
    )
    assert user.username == 'root'
