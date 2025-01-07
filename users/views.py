from django.urls import reverse_lazy
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.generic import CreateView
from .forms import UserRegisterForm
from .models import User
from rest_framework.decorators import api_view


class RegisterView(CreateView):
    model = User
    form_class = UserRegisterForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:login')


@api_view(['POST'])
def custom_logout_view(request):
    """
    Handles user logout functionality.
    """    
    logout(request)
    return redirect('/')