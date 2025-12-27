from django.contrib.auth import authenticate
from drf_spectacular.utils import inline_serializer, extend_schema, OpenApiTypes, OpenApiExample
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from users.models import User
from users.serializers import RegisterSerializer, UserSerializer


class LoginAPIView(APIView):
    authentication_classes = []

    @extend_schema(
       summary = "User Login",
        description='Authenticate user and return access token (refresh in cookie)',
        tags=['Authentication'],
        request=inline_serializer(
            name='LoginRequest',
            fields={
                'username': serializers.CharField(),
                'password': serializers.CharField(style={'input_type': 'password'}),
            }
        ),
        responses={
            200: inline_serializer(
                name='LoginResponse',
                fields={
                    'access': serializers.CharField(),
                }
            ),
            401: OpenApiTypes.OBJECT,
        }
    )
    def post(self, request):

        data = request.data
        username = data.get('username', None)
        password = data.get('password', None)

        if username is None or password is None:
            return Response({'error': 'No login or password'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)

        if user is None:
            return Response({'error': 'Invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        response = Response({'access': str(refresh.access_token)}, status=status.HTTP_200_OK)

        response.set_cookie(
            key='refresh',
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite='Lax',

        )

        return response

class RegistrationAPIView(APIView):

    @extend_schema(
        summary="User Registration",
        description='Register new user',
        tags=['Authentication'],
        request=RegisterSerializer,
        responses={
            201: inline_serializer(
                name='RegistrationResponse',
                fields={
                    'access': serializers.CharField(),
                }
            ),
            400: OpenApiTypes.OBJECT,
        }
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)

            response = Response({'access': str(refresh.access_token)}, status=status.HTTP_201_CREATED)
            response.set_cookie(
                key='refresh',
                value=str(refresh),
                httponly=True,
                secure=True,
                samesite='Lax',

            )

            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutAPIView(APIView):

    @extend_schema(
        summary="Logout User",
        description="Logout user by blacklisting refresh token",
        tags=['Authentication'],
        request=None,
        responses={
            200: inline_serializer(
                name='LogoutResponse',
                fields={
                    'success': serializers.CharField(),
                }
            ),
            400: OpenApiTypes.OBJECT,
        }
    )
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh', None)

        if not refresh_token:
            return Response({'error': 'No refresh token found in cookies'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response({'error': 'Invalid or expired refresh token'}, status=status.HTTP_400_BAD_REQUEST)

        response = Response({'success': 'Logout complete'}, status=status.HTTP_200_OK)
        response.delete_cookie('refresh')
        return response

class UserProfileAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Get User Profile",
        description="Retrieve the profile of the authenticated user",
        tags=['User Profile'],
        responses={200: UserSerializer}
    )

    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Update User Profile",
        description="Update the profile of the authenticated user",
        tags=['User Profile'],
        request=UserSerializer,
        responses={200: UserSerializer}
    )
    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom Token Refresh View that reads the refresh token from HttpOnly cookie.
    """
    @extend_schema(
        summary="Refresh Access Token",
        description="Refresh access token using refresh token from HttpOnly cookie",
        tags=['Authentication'],
        request=None,
        responses={
            200: inline_serializer(
                name='TokenRefreshResponse',
                fields={
                    'access': serializers.CharField(),
                }
            ),
            401: OpenApiTypes.OBJECT
        }
    )
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh')

        if not refresh_token:
            return Response({"detail": "Refresh token not found in cookies."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data={'refresh': refresh_token})

        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response({"detail": "Invalid or expired refresh token."}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)