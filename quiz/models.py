import os

from django.conf import settings
from django.db import models

# Create your models here.


def question_photo_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    if not ext:
        ext = ".jpg"
    return f"questions/{instance.quiz.id}/{instance.order}{ext}"


class QuizCategory(models.TextChoices):
    GENERAL = "general", "General Knowledge"
    SCIENCE = "science", "Science"
    HISTORY = "history", "History"
    LITERATURE = "literature", "Literature"
    MATH = "math", "Mathematics"
    SPORTS = "sports", "Sports"
    ENTERTAINMENT = "entertainment", "Entertainment"


class Quiz(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(
        max_length=100, choices=QuizCategory.choices, default=QuizCategory.GENERAL
    )
    is_time_limited = models.BooleanField(default=False)
    time_limit = models.DurationField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_quizzes",
    )
    last_modified = models.DateTimeField(auto_now=True)

    MAX_SCORE = 100

    class Meta:
        db_table = "quiz"
        ordering = ["-created_at"]
        verbose_name = "Quiz"
        verbose_name_plural = "Quizzes"

    def __str__(self):
        return self.title

    def get_question_score(self):
        """Возвращает "цену" одного вопроса в этом тесте"""
        question_count = self.questions.count()
        if question_count == 0:
            return 0
        return self.MAX_SCORE / question_count

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class QuestionType(models.TextChoices):
    SINGLE = "single", "Single Choice"
    MULTIPLE = "multiple", "Multiple Choice"


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    title = models.CharField(max_length=500)
    answer_type = models.CharField(
        max_length=50, choices=QuestionType.choices, default=QuestionType.SINGLE
    )  # e.g., 'single', 'multiple's
    order = models.IntegerField()
    question_photo = models.ImageField(
        upload_to=question_photo_path, null=True, blank=True
    )

    class Meta:
        db_table = "question"
        ordering = ["order"]
        verbose_name = "Question"
        verbose_name_plural = "Questions"

        constraints = [
            models.UniqueConstraint(
                fields=["quiz", "order"], name="unique_order_per_quiz"
            ),
        ]

    def __str__(self):
        return f"Question {self.order} for Quiz {self.quiz.title}"


class AnswerOption(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="answer_options"
    )
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    class Meta:
        db_table = "answer_option"
        verbose_name = "Answer Option"
        verbose_name_plural = "Answer Options"

    def __str__(self):
        return f"{self.text[: 50]} ({'✓' if self.is_correct else '✗'})"


class QuizAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts"
    )
    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name="quiz_attempts"
    )
    score = models.FloatField(default=0.0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "quiz_attempt"
        verbose_name = "Quiz Attempt"
        verbose_name_plural = "Quiz Attempts"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "quiz"],
                condition=models.Q(completed_at__isnull=True),
                name="unique_quiz_per_user",
            )
        ]

    def __str__(self):
        return f"Attempt by {self.user.username} for Quiz {self.quiz.title}"


class UserAnswer(models.Model):
    attempt = models.ForeignKey(
        QuizAttempt, on_delete=models.CASCADE, related_name="user_answers"
    )
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="user_answers"
    )
    selected_options = models.ManyToManyField(AnswerOption, related_name="user_answers")
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_answer"
        verbose_name = "User Answer"
        verbose_name_plural = "User Answers"

        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="unique_answer_per_attempt_question",
            ),
        ]

    def __str__(self):
        return (
            f"Answer by {self.attempt.user.username} "
            f"for Question {self.question.order} in Quiz {self.question.quiz.title}"
        )
