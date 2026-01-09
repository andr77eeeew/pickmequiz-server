from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test import APITestCase
from gamification.models import Achievement, UserAchievement
from quiz.models import Quiz, QuizAttempt, Question, QuestionType, AnswerOption

User = get_user_model()

# Create your tests here.

class AchievementTests(APITestCase):

    @classmethod
    def setUpTestData(cls):

        cls.user = User.objects.create(username="gamer", password="pwd")

        cls.ach_first_blood = Achievement.objects.create(
            code = "first_blood",
            title="First Blood",
            description="First Blood"
        )

        cls.ach_sniper = Achievement.objects.create(
            code = "sniper",
            title="Sniper",
            description="Sniper"
        )

        cls.quiz = Quiz.objects.create(
            title="Quiz",
            creator=cls.user,
            description="Test Your Skills"
        )

        cls.q1 = Question.objects.create(
            quiz=cls.quiz,
            title = "2 + 2 - ?",
            order = 1,
            answer_type = QuestionType.SINGLE,
        )

        cls.q1_opt_correct = AnswerOption.objects.create(question=cls.q1, text="4", is_correct=True)
        cls.q1_opt_wrong = AnswerOption.objects.create(question=cls.q1, text="5", is_correct=False)

        cls.q2 = Question.objects.create(
            quiz=cls.quiz,
            title="Select red fruits",
            order=2,
            answer_type=QuestionType.MULTIPLE
        )

        cls.q2_opt_correct1 = AnswerOption.objects.create(question=cls.q2, text="Apple", is_correct=True)
        cls.q2_opt_correct2 = AnswerOption.objects.create(question=cls.q2, text="Cherry", is_correct=True)
        cls.q2_opt_wrong = AnswerOption.objects.create(question=cls.q2, text="Banana", is_correct=False)

    def setUp(self):
        self.authenticate_user(self.user)

    def authenticate_user(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")


    def test_first_blood(self):

        attempt = QuizAttempt.objects.create(user=self.user, quiz=self.quiz)

        url = reverse("quiz:quiz-attempt-detail", kwargs={"pk": attempt.pk}) + "submit/"

        data = {
            "answers": [
                {
                    "question_id": self.q1.id,
                    "selected_options": [self.q1_opt_wrong.id]
                },
                {
                    "question_id": self.q2.id,
                    "selected_options": [
                        self.q2_opt_correct1.id,
                        self.q2_opt_wrong.id
                    ]
                }
            ]
        }

        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        has_achievement = UserAchievement.objects.filter(
            user=self.user,
            achievement=self.ach_first_blood
        ).exists()

        self.assertTrue(has_achievement, "Пользователь должен получить ачивку First Blood!")

    def test_sniper(self):
        attempt = QuizAttempt.objects.create(user=self.user, quiz=self.quiz)

        url = reverse("quiz:quiz-attempt-detail", kwargs={"pk": attempt.pk}) + "submit/"
        data = {
            "answers": [
                {
                    "question_id": self.q1.id,
                    "selected_options": [self.q1_opt_correct.id]
                },
                {
                    "question_id": self.q2.id,
                    "selected_options": [
                        self.q2_opt_correct1.id,
                        self.q2_opt_correct2.id
                    ]
                }
            ]
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["score"], 100.0)

        has_achievement = UserAchievement.objects.filter(
            user=self.user,
            achievement=self.ach_sniper
        ).exists()

        self.assertTrue(has_achievement, "Пользователь должен получить ачивку Sniper!")
