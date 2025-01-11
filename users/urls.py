from django.urls import path
from . import views
from .apps import UsersConfig


app_name = UsersConfig.name

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('signin/', views.signin, name='signin'),
]