from django.contrib.auth.views import LoginView
from django.urls import path

from . import views
from .apps import UsersConfig
from .views import RegisterView

app_name = UsersConfig.name

urlpatterns = [
    path("", LoginView.as_view(template_name='users/login.html'), name="login"),
    path('logout/', views.custom_logout_view, name='logout'),
    path("register/", RegisterView.as_view(), name="register"),
]
