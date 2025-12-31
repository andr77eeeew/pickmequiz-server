from django.core.serializers import get_serializer
from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Quiz, QuizAttempt
from .permissions import IsCreator
from .serializers import QuizListSerializer, QuizDetailSerializer, QuizAttemptStartSerializer, \
    QuizAttemptSubmitSerializer


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

        if self.action == "list":
            queryset = Quiz.objects.all().select_related("creator")
        elif self.action == ["retrieve", "update", "partial_update"]:
            queryset = Quiz.objects.prefetch_related("questions__answer_options")

        return queryset

class QuizAttemptViewSet(viewsets.ModelViewSet):

    def get_queryset(self) -> QuerySet:
        return QuizAttempt.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "submit":
            return QuizAttemptSubmitSerializer
        return QuizAttemptStartSerializer
    @extend_schema(
        summary="Start a Quiz Attempt",
        description="Start a new attempt for a quiz.",
        tags=["Quiz Attempts"],
    )
    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt = serializer.save(user=self.request.user)

        quiz_serializer = QuizDetailSerializer(attempt.quiz)

        return Response({
            'attempt_id': attempt.id,
            'quiz': quiz_serializer.data,
            'strted_at': attempt.started_at,
        }, status = status.HTTP_201_CREATED)


    @extend_schema(
        summary="Submit a Quiz Attempt",
        description="Submit answers for a quiz attempt.",
        tags=["Quiz Attempts"],
    )
    @action(detail=True, methods=["patch"])
    def submit(self, request: Request, pk=None) -> Response:
        attempt = self.get_object()

        if attempt.completed_at is not None:
            return Response(
                {"detail": "This attempt has already been completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(attempt, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)