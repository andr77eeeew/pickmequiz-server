from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets


from .models import Quiz
from .serializers import QuizSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List Quiz",
        description="Retrieve a list of all quizzes.",
        tags=["Quizzes"],
    ),
    retrieve=extend_schema(
        summary="Retrieve a Quiz",
        description="Retrieve a Quiz include questions.",
        tags=["Quizzes"],
    ),
    create=extend_schema(
        summary="Create a new Quiz",
        description="Create a new Quiz with questions and answer options.",
        tags=["Quizzes"],
    ),
    update=extend_schema(
        summary="Update a Quiz",
        description="Update an existing Quiz along with its questions and answer options.",
        tags=["Quizzes"],
    ),
    partial_update=extend_schema(
        summary="Partially Update a Quiz",
        description="Partially update an existing Quiz.",
        tags=["Quizzes"],
    ),
    destroy=extend_schema(
        summary="Delete a Quiz",
        description="Delete an existing Quiz.",
        tags=["Quizzes"],
    ),
)
class QuizViewSet(viewsets.ModelViewSet):
    serializer_class = QuizSerializer

    def get_queryset(self) -> QuerySet:
        queryset = Quiz.objects.prefetch_related("questions__answer_options").all()

        if self.request.user.is_authenticated:
            return queryset
        return queryset.none()
