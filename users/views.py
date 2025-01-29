import logging

from django.contrib.auth import authenticate, logout
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from drf_yasg.utils import swagger_auto_schema

from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

from users.serializers import UserSigninSerializer, UserSignupSerializer
from .models import User

logger = logging.getLogger(__name__)


@api_view(['POST'])
@renderer_classes([JSONRenderer])
def custom_logout_view(request):
    """
    Handles user logout functionality.

    Logs out the current user from the system.
    Returns success message after logout.
    """    
    logger.info("Logout request received")
    request.session.flush()
    logout(request)
    logger.info("User successfully logged out")
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

    logger.info("Signup request received with method: %s", request.method)
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
            logger.info("User signed up successfully: %s", user.username)
            return Response({
                'user': serializer.data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        logger.error("Signup failed with errors: %s", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
@renderer_classes([JSONRenderer])
def signin(request):
    """Signin user with username and password.    
    Returns JWT refresh and access tokens on successful authentication.
    Returns error message if credentials are invalid or request data is malformed."""

    logger.info("Signin request received")
    serializer = UserSigninSerializer(data=request.data)
    if serializer.is_valid():
        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )
        if user:
            if not request.session.session_key:
                request.session.create()
            refresh = RefreshToken.for_user(user)
            logger.info("User signed in successfully: %s", user.username)
            return Response({
                'user_id': user.id,
                'session_key': request.session.session_key,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        logger.warning("Invalid credentials provided for signin")
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    logger.error("Signin failed with errors: %s", serializer.errors)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@renderer_classes([JSONRenderer])
def get_session_by_token(request, token):
    logger.info("Get session by token request received")
    try:
        # Decode the token
        decoded_token = AccessToken(token)
        user_id = decoded_token['user_id']
        user = User.objects.get(id=user_id)
        
        # Create session if needed
        if not request.session.session_key:
            request.session.create()
            
        logger.info("Session retrieved successfully for user: %s", user.username)
        return JsonResponse({
            'user_id': user.id,
            'session_key': request.session.session_key,
            'username': user.username
        })
    except Exception as e:
        logger.error("Failed to retrieve session by token: %s", str(e))
        return JsonResponse({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
    

@api_view(['GET'])
def user_details(request, user_id):
    """
    API endpoint to retrieve user details by user ID.

    Returns the username, email, profile picture URL, last login time,
    and user role for the user associated with the provided user ID.
    """
    logger.info("User details request received for user_id: %s", user_id)
    try:
        user = User.objects.get(id=user_id)

        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email if hasattr(user, 'email') else None,
            "last_login": user.last_login,
            "role": "admin" if user.is_superuser else "staff" if user.is_staff else "user"
        }
        logger.info("User details retrieved successfully for user: %s", user.username)
        return Response(user_data, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        logger.warning("User not found for user_id: %s", user_id)
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)    


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSignupSerializer

    @swagger_auto_schema(
        operation_description="""Get list of items.
            This endpoint retrieves all user records from the database.
            Returns a paginated list of user objects.""",
        responses={200: UserSignupSerializer(many=True)}
    )
    @method_decorator(cache_page(60 * 2))
    def list(self, request, *args, **kwargs):
        logger.info("User list request received")
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="""Create new item.
            This endpoint creates a new user record in the database.
            Requires user data to be provided in the request body.""",
        request_body=UserSignupSerializer,
        responses={201: UserSignupSerializer()}
    )
    def create(self, request, *args, **kwargs):
        logger.info("User create request received")
        return super().create(request, *args, **kwargs)
