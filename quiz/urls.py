from django.urls import include, path
from rest_framework import routers

from .views import QuizViewSet

app_name = "quiz"

router = routers.DefaultRouter()
router.register(r"quizzes", QuizViewSet, basename="quiz")

urlpatterns = [
    path("api/", include(router.urls)),
]
