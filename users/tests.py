import shutil
import tempfile
from io import BytesIO

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from quiz.models import Quiz, QuizAttempt

User = get_user_model()

MEDIA_ROOT = tempfile.mkdtemp()

class AuthTests(APITestCase):
    def setUp(self):

        self.register_url = reverse("users:register")
        self.login_url = reverse("users:login")
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "strongpassword123",
        }

    def generate_photo_file(self, name="test_image.jpg"):
        file_obj = BytesIO()

        image = Image.new("RGB", (100, 100), "red")
        image.save(file_obj, "JPEG")
        file_obj.seek(0)

        return SimpleUploadedFile(name, file_obj.read(), content_type="image/jpeg")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def authenticate_user(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_registration(self):

        response = self.client.post(self.register_url, self.user_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertIn("access", response.data)

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, "testuser")

    def test_registration_with_existing_username(self):
        User.objects.create_user(
            username="testuser", email="test1@example.com", password="strongpassword123"
        )

        response = self.client.post(self.register_url, self.user_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_with_existing_email(self):
        User.objects.create_user(
            username="test1user", email="test@example.com", password="strongpassword123"
        )

        response = self.client.post(self.register_url, self.user_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_with_weak_password(self):
        weak_password_data = self.user_data.copy()
        weak_password_data["password"] = "123"

        response = self.client.post(self.register_url, weak_password_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_missing_fields(self):
        incomplete_data = {"username": "testuser", "password": "strongpassword123"}

        response = self.client.post(self.register_url, incomplete_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login(self):

        User.objects.create_user(**self.user_data)

        login_data = {
            "username": self.user_data["username"],
            "password": self.user_data["password"],
        }
        response = self.client.post(self.login_url, login_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

        self.assertIn("refresh", response.cookies)

    def test_login_with_incorrect_password(self):
        User.objects.create_user(**self.user_data)

        login_data = {
            "username": self.user_data["username"],
            "password": "wrongpassword",
        }
        response = self.client.post(self.login_url, login_data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout(self):

        logout_user = User.objects.create_user(**self.user_data)

        refresh = RefreshToken.for_user(logout_user)

        self.authenticate_user(logout_user)

        self.client.cookies["refresh"] = str(refresh)

        response = self.client.post(reverse("users:logout"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.cookies.get("refresh").value, "")

    def test_logout_without_token(self):

        response = self.client.post(reverse("users:logout"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_profile_update(self):

        profile_user = User.objects.create_user(**self.user_data)

        self.authenticate_user(profile_user)

        update_data = {
            "first_name": "Test",
            "last_name": "User",
            "about": "This is a test user.",
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

        self.client.cookies["refresh"] = str(refresh)

        response = self.client.post(reverse("users:token_refresh"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_invalid_refresh_token(self):

        self.client.cookies["refresh"] = "invalidtoken"

        response = self.client.post(reverse("users:token_refresh"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_leaderboard_sorting_and_content(self):

        user_low = User.objects.create_user(username="Loser", email="l@t.com", password="pwd")
        user_mid = User.objects.create_user(username="Middle", email="m@t.com", password="pwd")
        user_top = User.objects.create_user(username="Winner", email="w@t.com", password="pwd")

        quiz = Quiz.objects.create(title="Q1", creator=user_top, description="d")

        QuizAttempt.objects.create(user=user_top, quiz=quiz, score=100, completed_at=timezone.now())
        QuizAttempt.objects.create(user=user_mid, quiz=quiz, score=50, completed_at=timezone.now())
        QuizAttempt.objects.create(user=user_low, quiz=quiz, score=10, completed_at=timezone.now())

        url = reverse("users:leaderboard")

        response = self.client.get(url, {"ordering": "fake_ordering"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data

        self.assertEqual(len(data), 3)

        self.assertEqual(data[0]["username"], "Winner")
        self.assertEqual(data[0]["total_score"], 100.0)

        self.assertEqual(data[1]["username"], "Middle")
        self.assertEqual(data[1]["total_score"], 50.0)

        self.assertEqual(data[2]["username"], "Loser")
        self.assertEqual(data[2]["total_score"], 10.0)

    def test_leaderboard_tests_passed_ordering(self):
        u1 = User.objects.create_user(username="ManyTests", email="1@t.com", password="p")
        u2 = User.objects.create_user(username="FewTests", email="2@t.com", password="p")

        q1 = Quiz.objects.create(title="Q1", creator=u1, description="d")
        q2 = Quiz.objects.create(title="Q2", creator=u1, description="d")

        QuizAttempt.objects.create(user=u1, quiz=q1, score=10, completed_at=timezone.now())
        QuizAttempt.objects.create(user=u1, quiz=q2, score=10, completed_at=timezone.now())

        QuizAttempt.objects.create(user=u2, quiz=q1, score=100, completed_at=timezone.now())

        url = reverse("users:leaderboard")
        response = self.client.get(url, {"ordering": "tests_passed"})

        data = response.data

        self.assertEqual(len(data), 2)

        self.assertEqual(data[0]["username"], "ManyTests")
        self.assertEqual(data[0]["tests_passed"], 2)

        self.assertEqual(data[1]["username"], "FewTests")
        self.assertEqual(data[1]["tests_passed"], 1)

    def test_upload_photo(self):
        user = User.objects.create_user(username="photomodel", email="p@t.com", password="pwd")
        self.authenticate_user(user=user)
        url = reverse("users:profile")

        photo = self.generate_photo_file()

        data = {
            "first_name": "Model",
            "last_name": "Photo",
            "avatar": photo,
        }

        response = self.client.put(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn("avatar", response.data)
        self.assertTrue(response.data["avatar"].startswith("http"))

        user.refresh_from_db()
        self.assertTrue(bool(user.avatar))
        expected_path = f"avatars/user_{user.id}/{user.username}_avatar"

        self.assertIn(expected_path, user.avatar.name)