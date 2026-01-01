from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from drf_spectacular.utils import OpenApiTypes, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from users.serializers import RegisterSerializer, UserSerializer, LoginSerializer
from users.throttling import LoginRateThrottle
import logging
User = get_user_model()

logger = logging.getLogger(__name__)
class LoginAPIView(APIView):
    authentication_classes = []
    throttle_classes = [LoginRateThrottle]

    @extend_schema(
        summary="User Login",
        description="Authenticate user and return access token (refresh in cookie)",
        tags=["Authentication"],
        request=inline_serializer(
            name="LoginRequest",
            fields={
                "username": serializers.CharField(),
                "password": serializers.CharField(style={"input_type": "password"}),
            },
        ),
        responses={
            200: inline_serializer(
                name="LoginResponse",
                fields={
                    "access": serializers.CharField(),
                },
            ),
            401: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request: Request) -> Response:

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        logger.info(f"Login attempt for user: {username}")

        user = authenticate(username=username, password=password)

        if user is None:
            logger.warning(f"Failed login attempt for user: {username}")
            return Response(
                {"error": "Invalid username or password"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        logger.info(f"Successful login for user: {username}")

        refresh = RefreshToken.for_user(user)
        response = Response(
            {"access": str(refresh.access_token)}, status=status.HTTP_200_OK
        )

        response.set_cookie(
            key="refresh",
            value=str(refresh),
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
        )

        return response


class RegistrationAPIView(APIView):

    @extend_schema(
        summary="User Registration",
        description="Register new user",
        tags=["Authentication"],
        request=RegisterSerializer,
        responses={
            201: inline_serializer(
                name="RegistrationResponse",
                fields={
                    "access": serializers.CharField(),
                },
            ),
            400: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        logger.info(f"Registration attempt with data: {request.data}")
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)

            logger.info(f"Successful registration for user: {user}")

            response = Response(
                {"access": str(refresh.access_token)}, status=status.HTTP_201_CREATED
            )
            response.set_cookie(
                key="refresh",
                value=str(refresh),
                httponly=True,
                secure=not settings.DEBUG,
                samesite="Lax",
            )

            return response
        logger.warning(f"Failed registration attempt with errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutAPIView(APIView):

    @extend_schema(
        summary="Logout User",
        description="Logout user by blacklisting refresh token",
        tags=["Authentication"],
        request=None,
        responses={
            200: inline_serializer(
                name="LogoutResponse",
                fields={
                    "success": serializers.CharField(),
                },
            ),
            400: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request: Request) -> Response:
        refresh_token = request.COOKIES.get("refresh", None)
        logger.info(f"Logout attempt with refresh token: {refresh_token}")
        if not refresh_token:
            logger.warning(f"Failed logout attempt with refresh token: {refresh_token}")
            return Response(
                {"error": "No refresh token found in cookies"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            logger.info(f"Blacklisting refresh token: {refresh_token}")
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            logger.warning(f"Failed to blacklist refresh token: {refresh_token}")
            return Response(
                {"error": "Invalid or expired refresh token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        logger.info(f"Successful logout for refresh token: {refresh_token}")
        response = Response({"success": "Logout complete"}, status=status.HTTP_200_OK)
        response.delete_cookie("refresh")
        return response


class UserProfileAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Get User Profile",
        description="Retrieve the profile of the authenticated user",
        tags=["User Profile"],
        responses={200: UserSerializer},
    )
    def get(self, request: Request) -> Response:
        user = User.objects.prefetch_related("favourite_tests", "quiz_attempts").get(user=request.user)
        serializer = UserSerializer(user, context={"request": request})
        logger.info(f"Retrieved profile for user: {request.user}")
        return Response(serializer.data)

    @extend_schema(
        summary="Update User Profile",
        description="Update the profile of the authenticated user",
        tags=["User Profile"],
        request=UserSerializer,
        responses={200: UserSerializer},
    )
    def put(self, request: Request) -> Response:
        serializer = UserSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            logger.info(f"Updating profile for user: {request.user} with data: {request.data}")
            serializer.save()
            return Response(serializer.data)
        logger.warning(f"Failed to update profile for user: {request.user} with errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom Token Refresh View that reads the refresh token from HttpOnly cookie.
    """

    @extend_schema(
        summary="Refresh Access Token",
        description="Refresh access token using refresh token from HttpOnly cookie",
        tags=["Authentication"],
        request=None,
        responses={
            200: inline_serializer(
                name="TokenRefreshResponse",
                fields={
                    "access": serializers.CharField(),
                },
            ),
            401: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request: Request, *args, **kwargs) -> Response:
        refresh_token = request.COOKIES.get("refresh")
        logger.info(f"Token refresh attempt with refresh token: {refresh_token}")
        if not refresh_token:
            logger.warning(f"Failed token refresh attempt with refresh token: {refresh_token}")
            return Response(
                {"detail": "Refresh token not found in cookies."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data={"refresh": refresh_token})

        try:
            logger.info(f"Refreshing access token with refresh token: {refresh_token}")
            serializer.is_valid(raise_exception=True)
        except TokenError:
            logger.warning(f"Failed to refresh access token with refresh token: {refresh_token}")
            return Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        logger.info(f"Successful token refresh with refresh token: {refresh_token}")
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
