from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class AuthTests(APITestCase):
    def setUp(self):

        self.register_url = reverse("users:register")
        self.login_url = reverse("users:login")
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "strongpassword123"
        }

    def authenticate_user(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_registration(self):

        response = self.client.post(self.register_url, self.user_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertIn('access', response.data)

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, "testuser")


    def test_registration_with_existing_username(self):
        User.objects.create_user(username="testuser", email="test1@example.com", password="strongpassword123")

        response = self.client.post(self.register_url, self.user_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_with_existing_email(self):
        User.objects.create_user(username="test1user", email="test@example.com", password="strongpassword123")

        response = self.client.post(self.register_url, self.user_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_with_weak_password(self):
        weak_password_data = self.user_data.copy()
        weak_password_data['password'] = '123'

        response = self.client.post(self.register_url, weak_password_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_missing_fields(self):
        incomplete_data = {
            "username": "testuser",
            "password": "strongpassword123"
        }

        response = self.client.post(self.register_url, incomplete_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login(self):

        User.objects.create_user(**self.user_data)

        login_data = {
            "username": self.user_data['username'],
            "password": self.user_data['password']
        }
        response = self.client.post(self.login_url, login_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

        self.assertIn('refresh', response.cookies)

    def test_login_with_incorrect_password(self):
        User.objects.create_user(**self.user_data)

        login_data = {
            "username": self.user_data['username'],
            "password": "wrongpassword"
        }
        response = self.client.post(self.login_url, login_data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout(self):

        logout_user = User.objects.create_user(**self.user_data)

        refresh = RefreshToken.for_user(logout_user)

        self.authenticate_user(logout_user)

        self.client.cookies['refresh'] = str(refresh)

        response = self.client.post(reverse("users:logout"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.cookies.get('refresh').value, '')

    def test_logout_without_token(self):

        response = self.client.post(reverse("users:logout"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_profile_update(self):

        profile_user = User.objects.create_user(**self.user_data)

        self.authenticate_user(profile_user)

        update_data = {
            "first_name": "Test",
            "last_name": "User",
            "about": "This is a test user."
        }
        response = self.client.put(reverse("users:profile"), update_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        profile_user.refresh_from_db()
        self.assertEqual(profile_user.first_name, "Test")
        self.assertEqual(profile_user.last_name, "User")
        self.assertEqual(profile_user.about, "This is a test user.")

    def test_get_profile_unauthenticated(self):

        response = self.client.get(reverse("users:profile"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token(self):

        refresh_user = User.objects.create_user(**self.user_data)

        refresh = RefreshToken.for_user(refresh_user)

        self.client.cookies['refresh'] = str(refresh)

        response = self.client.post(reverse("users:token_refresh"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)