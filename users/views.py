from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.renderers import JSONRenderer

from django.urls import reverse_lazy
from django.contrib.auth import authenticate
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.views.generic import CreateView

from users.serializers import UserSigninSerializer, UserSignupSerializer
from .forms import UserRegisterForm
from .models import User
from drf_yasg.utils import swagger_auto_schema


class RegisterView(CreateView):
    model = User
    form_class = UserRegisterForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:login')


@api_view(['POST'])
@renderer_classes([JSONRenderer])
def custom_logout_view(request):
    """
    Handles user logout functionality.

    Logs out the current user from the system.
    Returns success message after logout.
    """    
    request.session.flush()
    logout(request)
    return Response({
        'message': 'Successfully logged out'
    }, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@renderer_classes([JSONRenderer])
def signup(request):
    """Handles user registration functionality.
    Provides signup instructions on GET request.
    Creates new user account and returns JWT tokens on POST request."""

    if request.method == 'GET':
        return Response({
            "message": "Welcome to signup endpoint",
            "instructions": {
                "method": "POST",
                "required_fields": {
                    "username": "string",
                    "password": "string"
                }
            }
        })
    
    elif request.method == 'POST':
        serializer = UserSignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': serializer.data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
@renderer_classes([JSONRenderer])
def signin(request):
    """Signin user with username and password.    
    Returns JWT refresh and access tokens on successful authentication.
    Returns error message if credentials are invalid or request data is malformed."""

    serializer = UserSigninSerializer(data=request.data)
    if serializer.is_valid():
        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSignupSerializer

    @swagger_auto_schema(
        operation_description="""Get list of items.
            This endpoint retrieves all user records from the database.
            Returns a paginated list of user objects.""",
        responses={200: UserSignupSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="""Create new item.
            This endpoint creates a new user record in the database.
            Requires user data to be provided in the request body.""",
        request_body=UserSignupSerializer,
        responses={201: UserSignupSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
