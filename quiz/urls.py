from django.urls import include, path
from rest_framework import routers

from .views import QuizViewSet, QuizAttemptViewSet

app_name = "quiz"

router = routers.DefaultRouter()
router.register(r"quizzes", QuizViewSet, basename="quiz")
router.register(r"quiz-attempts", QuizAttemptViewSet, basename="quiz-attempt")

urlpatterns = [
    path("api/", include(router.urls)),
]
