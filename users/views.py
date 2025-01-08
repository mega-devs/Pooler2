from django.urls import reverse_lazy
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.generic import CreateView

from users.serializers import UserSerializer
from .forms import UserRegisterForm
from .models import User
from rest_framework.decorators import api_view
from rest_framework import viewsets
from drf_yasg.utils import swagger_auto_schema


class RegisterView(CreateView):
    model = User
    form_class = UserRegisterForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:login')


@api_view(['POST'])
def custom_logout_view(request):
    """
    Handles user logout functionality.

    Logs out the current user from the system.
    Redirects to the home page after successful logout.
    """    
    logout(request)
    return redirect('/')


# viewset for 'users' model, >Swagger documentation
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @swagger_auto_schema(
        operation_description="""Get list of items.
            This endpoint retrieves all user records from the database.
            Returns a paginated list of user objects.""",
        responses={200: UserSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="""Create new item.
            This endpoint creates a new user record in the database.
            Requires user data to be provided in the request body.""",
        request_body=UserSerializer,
        responses={201: UserSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
