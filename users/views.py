from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User
from users.serializers import RegisterSerializer, UserSerializer


class LoginAPIView(APIView):
    authentication_classes = []

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

    def get(self, request):
        user = User.objects.get(id=request.user.id)
        user = UserSerializer(user)
        return Response(user.data)

    def put(self, request):
        user = User.objects.get(id=request.user.id)
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)