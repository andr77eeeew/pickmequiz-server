import logging

from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Quiz, QuizAttempt
from .permissions import IsCreator
from .serializers import (
    QuizAttemptStartSerializer,
    QuizAttemptSubmitSerializer,
    QuizDetailSerializer,
    QuizListSerializer,
)

logger = logging.getLogger(__name__)


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
        logger.info(f"Getting serializer class for action: {self.action}")
        if self.action != "list":
            if hasattr(self, "detail_serializer_class"):
                return self.detail_serializer_class

        return super().get_serializer_class()

    def get_queryset(self) -> QuerySet:
        logger.info(f"Getting queryset for action: {self.action}")
        if self.action == "list":
            return Quiz.objects.all().select_related("creator")
        elif self.action in ["retrieve", "update", "partial_update", "destroy"]:
            return Quiz.objects.prefetch_related("questions__answer_options")

        return Quiz.objects.all()


class QuizAttemptViewSet(viewsets.ModelViewSet):

    def get_queryset(self) -> QuerySet:
        return (
            QuizAttempt.objects.filter(user=self.request.user)
            .select_related("quiz")
            .prefetch_related("user_answers__selected_options")
        )

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

        quiz_id = request.data["quiz"]

        active_attempt = QuizAttempt.objects.filter(
            user=request.user,
            quiz_id=quiz_id,
            completed_at__isnull=True,
        ).first()

        if active_attempt:
            logger.warning(
                f"User {request.user} already has an active attempt for Quiz ID {quiz_id}"
            )
            return Response(
                {
                    "detail": "You already have an active attempt for this quiz.",
                    "attempt_id": active_attempt.id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt = serializer.save(user=self.request.user)

        quiz_serializer = QuizDetailSerializer(attempt.quiz)

        return Response(
            {
                "attempt_id": attempt.id,
                "quiz": quiz_serializer.data,
                "started_at": attempt.started_at,
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Submit a Quiz Attempt",
        description="Submit answers for a quiz attempt.",
        tags=["Quiz Attempts"],
    )
    @action(detail=True, methods=["patch"])
    def submit(self, request: Request, pk=None) -> Response:
        attempt = self.get_object()
        logger.info(f"Attempt ID: {attempt.id}")
        if attempt.completed_at is not None:
            logger.warning(f"Attempt ID: {attempt.id} already completed")
            return Response(
                {"detail": "This attempt has already been completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(attempt, data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            serializer.save()
        except Exception as e:
            logger.error(f"Error submitting attempt ID: {attempt.id} - {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.data)
