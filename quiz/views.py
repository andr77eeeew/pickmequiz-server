from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Quiz
from .permissions import IsCreator
from .serializers import QuizListSerializer, QuizDetailSerializer


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
    serializer_class = QuizListSerializer
    detail_serializer_class = QuizDetailSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsCreator]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["category"]
    search_fields = ["title", "description"]

    def get_serializer_class(self):
        if self.action != "list":
            if hasattr(self, "detail_serializer_class"):
                return self.detail_serializer_class

        return super().get_serializer_class()

    def get_queryset(self) -> QuerySet:
        queryset = Quiz.objects.all()

        if self.request.user.is_authenticated:
            if self.action == "list":
                queryset = Quiz.objects.all().select_related("creator")
                return queryset
            queryset = Quiz.objects.prefetch_related("questions__answer_options").all()
            return queryset
        return queryset.none()
