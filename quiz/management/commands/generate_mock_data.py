import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker

from quiz.models import (
    AnswerOption,
    Question,
    QuestionType,
    Quiz,
    QuizAttempt,
    QuizCategory,
)

User = get_user_model()
fake = Faker()


class Command(BaseCommand):
    help = "Generates fake data for testing"

    def handle(self, *args, **kwargs):
        self.stdout.write("Generating fake data...")

        USER_COUNT = 20
        QUIZZES_COUNT = 10
        ATTEMPTS_PRE_USER = 5

        with transaction.atomic():

            self.stdout.write(f"Creating {USER_COUNT} users...")
            users = []
            for _ in range(USER_COUNT):
                user = User.objects.create_user(
                    username=fake.user_name(),
                    email=fake.unique.email(),
                    password="password123",
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    about=fake.text(max_nb_chars=100),
                )
                users.append(user)

            self.stdout.write(f"Creating {QUIZZES_COUNT} quizzes...")
            quizzes = []
            categories = [choice[0] for choice in QuizCategory.choices]

            author = users[0]

            for i in range(QUIZZES_COUNT):
                quiz = Quiz.objects.create(
                    title=fake.sentence(nb_words=5).rstrip("."),
                    description=fake.text(max_nb_chars=200),
                    category=random.choice(categories),
                    creator=author,
                    is_time_limited=random.choice([True, False]),
                    time_limit=(
                        timezone.timedelta(minutes=random.randint(5, 30))
                        if random.choice([True, False])
                        else None
                    ),
                )

                for q_idx in range(random.randint(5, 10)):
                    question = Question.objects.create(
                        quiz=quiz,
                        title=fake.sentence(nb_words=5).rstrip(".") + "?",
                        answer_type=QuestionType.SINGLE,
                        order=q_idx + 1,
                    )

                    for opt_idx in range(4):
                        AnswerOption.objects.create(
                            question=question,
                            text=fake.word(),
                            is_correct=(opt_idx == 0),
                        )
                    quizzes.append(quiz)

            self.stdout.write("Simulating quiz attempts...")
            for user in users:
                passed_quizzes = random.sample(
                    quizzes, k=min(len(quizzes), ATTEMPTS_PRE_USER)
                )

                for quiz in passed_quizzes:
                    random_score = random.randint(0, 10) * 10.0

                    QuizAttempt.objects.create(
                        user=user,
                        quiz=quiz,
                        score=random_score,
                        completed_at=timezone.now(),
                    )

            self.stdout.write("Adding favourites...")
            for user in users:
                fav_quizzes = random.sample(quizzes, k=random.randint(0, 3))
                user.favourite_tests.set(fav_quizzes)

        self.stdout.write(self.style.SUCCESS("Data generation completed successfully!"))
