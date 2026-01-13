from datetime import timedelta

from django.utils import timezone

from celery import shared_task
from quiz.models import QuizAttempt


@shared_task
def check_expired_attempts():
    now = timezone.now()
    expired_attempts = QuizAttempt.objects.filter(
        completed_at__isnull=True,
        quiz__is_time_limited=True,
    ).select_related("quiz")
    for attempt in expired_attempts:
        if attempt.is_expired():
            attempt.score = 0.0
            attempt.completed_at = now
            attempt.save()
