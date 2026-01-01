from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.http import urlencode
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from quiz.models import Quiz, QuizAttempt

User = get_user_model()


class QuizCRUDTests(APITestCase):
    def setUp(self):
        # ИСПРАВЛЕНИЕ ЗДЕСЬ: Добавляем уникальные email для каждого юзера
        self.author = User.objects.create_user(
            username="author", email="author@test.com", password="password"
        )
        self.other_user = User.objects.create_user(
            username="other", email="other@test.com", password="password"
        )

        self.url_list = reverse("quiz:quiz-list")

        self.quiz_data = {
            "title": "Test Quiz",
            "description": "Description",
            "is_time_limited": False,
            "questions": [
                {
                    "title": "Question 1",
                    "answer_options": [
                        {"text": "Option 1", "is_correct": True},
                        {"text": "Option 2", "is_correct": False},
                    ],
                }
            ],
        }

    def authenticate_user(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_create_quiz_authenticated(self):
        self.authenticate_user(self.author)
        response = self.client.post(self.url_list, self.quiz_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Quiz.objects.count(), 1)
        self.assertEqual(Quiz.objects.get().creator, self.author)

    def test_create_quiz_unauthenticated(self):
        self.client.logout()
        self.client.credentials()
        response = self.client.post(self.url_list, self.quiz_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_quiz_permission(self):
        quiz = Quiz.objects.create(
            title="Old Title", creator=self.author, description="Desc"
        )
        url = reverse("quiz:quiz-detail", kwargs={"pk": quiz.pk})

        self.authenticate_user(self.other_user)
        response = self.client.patch(url, {"title": "Hacked Title"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.authenticate_user(self.author)
        response = self.client.patch(url, {"title": "New Title"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        quiz.refresh_from_db()
        self.assertEqual(quiz.title, "New Title")

    def test_delete_quiz_permission(self):
        quiz = Quiz.objects.create(
            title="To Delete", creator=self.author, description="Desc"
        )
        url = reverse("quiz:quiz-detail", kwargs={"pk": quiz.pk})

        self.authenticate_user(self.other_user)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Quiz.objects.count(), 1)

        self.authenticate_user(self.author)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Quiz.objects.count(), 0)

    def test_list_optimization(self):
        Quiz.objects.create(title="Q1", creator=self.author, description="Desc")

        self.authenticate_user(self.author)
        response = self.client.get(self.url_list)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("questions", response.data["results"][0])

    def test_validation_question_limit(self):
        self.authenticate_user(self.author)

        many_questions = []
        for i in range(21):
            many_questions.append(
                {
                    "title": f"Q {i}",
                    "answer_options": [{"text": "A", "is_correct": True}],
                }
            )

        data = self.quiz_data.copy()
        data["questions"] = many_questions

        response = self.client.post(self.url_list, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIn("questions", response.data)

    def test_start_attempt_quiz(self):
        self.authenticate_user(self.author)
        create_response = self.client.post(self.url_list, self.quiz_data, format="json")

        quiz_id = create_response.data["id"]

        url = reverse("quiz:quiz-attempt-list")

        quiz_attempt = {"quiz": quiz_id}

        response = self.client.post(url, quiz_attempt, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_submit_attempt_quiz(self):
        self.authenticate_user(self.author)

        response_create = self.client.post(self.url_list, self.quiz_data, format="json")

        quiz_id = response_create.data["id"]

        quiz = Quiz.objects.get(pk=quiz_id)

        attempt = QuizAttempt.objects.create(quiz=quiz, user=self.author)

        question = quiz.questions.first()
        option = question.answer_options.first()

        url = reverse("quiz:quiz-attempt-detail", kwargs={"pk": attempt.pk}) + "submit/"

        quiz_data = {
            "answers": [{"question_id": question.id, "selected_options": [option.id]}]
        }

        response = self.client.patch(url, quiz_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIsNotNone(response.data["completed_at"])

    def test_submit_attempt_invalid_question_id(self):
        self.authenticate_user(self.author)

        response_create = self.client.post(self.url_list, self.quiz_data, format="json")

        quiz_id = response_create.data["id"]

        quiz = Quiz.objects.get(pk=quiz_id)

        attempt = QuizAttempt.objects.create(quiz=quiz, user=self.author)

        url = reverse("quiz:quiz-attempt-detail", kwargs={"pk": attempt.pk}) + "submit/"

        invalid_q_id = quiz.questions.first().id + 999
        quiz_data = {
            "answers": [{"question_id": invalid_q_id, "selected_options": [1]}]
        }

        response = self.client.patch(url, quiz_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_answer_option_validation(self):
        self.authenticate_user(self.author)

        self.client.post(self.url_list, self.quiz_data, format="json")

        QuizAttempt.objects.create(quiz=Quiz.objects.get(pk=1), user=self.author)

        url = reverse("quiz:quiz-attempt-detail", kwargs={"pk": 1}) + "submit/"

        quiz_data = {"answers": [{"question_id": 1, "selected_options": []}]}

        response = self.client.patch(url, quiz_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_quiz_without_time_limit(self):
        self.authenticate_user(self.author)
        quiz_data = self.quiz_data.copy()
        quiz_data["is_time_limited"] = True

        response = self.client.post(self.url_list, quiz_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_quiz(self):
        self.authenticate_user(self.author)

        quiz1_data = self.quiz_data.copy()
        quiz1_data["title"] = "Python Basics"
        quiz1_data["description"] = "Learn Python fundamentals"
        self.client.post(self.url_list, quiz1_data, format="json")

        quiz2_data = self.quiz_data.copy()
        quiz2_data["title"] = "Django Advanced"
        quiz2_data["description"] = "Master Django framework"
        self.client.post(self.url_list, quiz2_data, format="json")

        url = f"{self. url_list}?search=Python"
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Python Basics")

        url = f"{self.url_list}?search=Django"
        response = self.client.get(url, format="json")

        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Django Advanced")

        url = f"{self.url_list}?search=JavaScript"
        response = self.client.get(url, format="json")

        self.assertEqual(len(response.data["results"]), 0)

    def test_get_quiz_filter(self):
        self.authenticate_user(self.author)

        categories = ["general", "science", "history"]
        created_quizzes = {}

        for category in categories:
            quiz_data = self.quiz_data.copy()
            quiz_data["category"] = category
            quiz_data["title"] = f"{category. title()} Quiz"
            response = self.client.post(self.url_list, quiz_data, format="json")
            created_quizzes[category] = response.data["id"]

        for category in categories:
            url = f"{self.url_list}?category={category}"
            response = self.client.get(url, format="json")

            self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]

        self.assertGreater(len(results), 0, f"No quizzes found for category {category}")
        for quiz in results:
            self.assertEqual(
                quiz["category"],
                category,
                f"Expected category {category}, got {quiz['category']}",
            )

        quiz_ids = [q["id"] for q in results]
        self.assertIn(created_quizzes[category], quiz_ids)

    def test_filter_nonexistent_category(self):
        self.authenticate_user(self.author)

        self.client.post(self.url_list, self.quiz_data, format="json")

        url = f"{self.url_list}?category=science"
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_filter_invalid_category(self):
        self.authenticate_user(self.author)

        url = f"{self.url_list}?category=invalid_category"
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_combined_search_and_filter(self):
        self.authenticate_user(self.author)

        quiz1 = self.quiz_data.copy()
        quiz1["title"] = "Python Science"
        quiz1["category"] = "science"
        self.client.post(self.url_list, quiz1, format="json")

        quiz2 = self.quiz_data.copy()
        quiz2["title"] = "Python History"
        quiz2["category"] = "history"
        self.client.post(self.url_list, quiz2, format="json")

        params = {"category": "science", "search": "Python"}
        url = f"{self.url_list}?{urlencode(params)}"
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Python Science")
        self.assertEqual(results[0]["category"], "science")
