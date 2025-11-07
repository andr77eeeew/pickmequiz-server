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
        operation_id='login_user',
        description='Authenticate user and return access token (refresh in cookie)',
        request=inline_serializer(
            name='LoginRequest',
            fields={
                'username': serializers.CharField(required=True, max_length=150),
                'password': serializers.CharField(required=True, min_length=8, write_only=True),
            }
        ),
        responses={
            200: inline_serializer(
                name='LoginResponse',
                fields={
                    'access': serializers.CharField(),
                }
            ),
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                'Valid login',
                value={'username': 'testuser', 'password': 'testpass'},
                request_only=True
            )
        ],
        tags=['Authentication']
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
        response = Response(status=status.HTTP_200_OK)
        response.set_cookie(
            key='refresh',
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite='Lax',

        )
        response.data = {
            'access': str(refresh.access_token),
        }

        return response

class RegistrationAPIView(APIView):

    @extend_schema(
        operation_id='register_user',
        description='Register new user and return access token (refresh in cookie)',
        request=RegisterSerializer,  # Используем ваш сериализатор: поля из fields в Meta
        responses={
            201: inline_serializer(
                name='RegistrationResponse',
                fields={
                    'access': serializers.CharField(),
                }
            ),
            400: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                'Valid registration',
                value={'username': 'newuser', 'password': 'strongpass', 'email': 'new@example.com'},
                request_only=True
            )
        ],
        tags=['Authentication']
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)

            response = Response(status=status.HTTP_201_CREATED)
            response.set_cookie(
                key='refresh',
                value=str(refresh),
                httponly=True,
                secure=True,
                samesite='Lax',

            )
            response.data = {
                'access': str(refresh.access_token),
            }

            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutAPIView(APIView):

    @extend_schema(
        operation_id='logout_user',
        description='Blacklist refresh token from cookie and logout user',
        request=None,  # Нет body, только cookie
        responses={
            200: inline_serializer(
                name='LogoutResponse',
                fields={
                    'success': serializers.CharField(default='Logout complete'),
                }
            ),
            400: OpenApiTypes.OBJECT,
        },
        tags=['Authentication']
    )
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh', None)

        if not refresh_token:
            return Response({'error': 'No refresh token'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception as e:
            return Response({'error': 'Invalid Refresh token'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'success': 'Logout complete'}, status=status.HTTP_200_OK)

class UserProfileAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id='get_user_profile',
        description='Retrieve current user profile',
        responses={
            200: UserSerializer,  # Используем ваш сериализатор: только поля из fields
        },
        tags=['User Profile']
    )
    def get(self, request):
        user = User.objects.get(id=request.user.id)
        user = UserSerializer(user)
        return Response(user.data)

    @extend_schema(
        operation_id='update_user_profile',
        description='Update current user profile (partial update allowed)',
        request=UserSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                'Partial update',
                value={'first_name': 'Updated Name', 'email': 'updated@example.com'},
                request_only=True
            )
        ],
        tags=['User Profile']
    )
    def put(self, request):
        user = User.objects.get(id=request.user.id)
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        # Извлекаем refresh-токен из куков (предполагаем, что ключ куки - 'refresh')
        refresh_token = request.COOKIES.get('refresh')

        if not refresh_token:
            return Response({"detail": "Refresh token not found in cookies."}, status=status.HTTP_400_BAD_REQUEST)

        # Создаём данные для сериалайзера (имитируем, как будто refresh пришёл в теле)
        data = {'refresh': refresh_token}

        # Получаем сериалайзер и валидируем
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        # Возвращаем новый access-токен в теле ответа
        return Response(serializer.validated_data, status=status.HTTP_200_OK)