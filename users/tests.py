from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

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

    def test_registration(self):

        response = self.client.post(self.register_url, self.user_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertIn('access', response.data)

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, "testuser")

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