import logging

from django.db import transaction
from django.db.models import Count, QuerySet
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from environs import ValidationError

from gamification.services import check_new_achievements
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Quiz, QuizAttempt, UserAnswer, AnswerOption
from .permissions import IsCreator
from .serializers import (
    QuizAttemptStartSerializer,
    QuizAttemptSubmitSerializer,
    QuizDetailSerializer,
    QuizListSerializer, StepByStepAnswerSerializer, QuestionPublicSerializer,
)
from .services import _calculate_score

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
    ordering_fields = ["created_at", "likes_count"]

    def get_serializer_class(self):
        logger.info(f"Getting serializer class for action: {self.action}")
        if self.action != "list":
            if hasattr(self, "detail_serializer_class"):
                return self.detail_serializer_class

        return super().get_serializer_class()

    def get_queryset(self) -> QuerySet:
        logger.info(f"Getting queryset for action: {self.action}")
        queryset = Quiz.objects.annotate(likes_count=Count("favoured_by"))
        if self.action == "list":
            queryset = queryset.select_related("creator")
        elif self.action in ["retrieve", "update", "partial_update", "destroy"]:
            queryset = queryset.prefetch_related("questions__answer_options")

        return queryset

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def favorite(self, request: Request, pk=None) -> Response:
        quiz = self.get_object()
        user = request.user

        if user.favourite_tests.filter(pk=pk).exists():
            user.favourite_tests.remove(quiz)
            return Response(
                {"is_favorite": user.favourite_tests.filter(pk=pk).exists()},
                status=status.HTTP_200_OK,
            )
        else:
            user.favourite_tests.add(quiz)
            return Response(
                {"is_favorite": user.favourite_tests.filter(pk=pk).exists()},
                status=status.HTTP_200_OK,
            )


class QuizAttemptViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

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

        first_question = attempt.quiz.questions.order_by("order").first()
        first_question_data = None
        if first_question:
            first_question_data = QuestionPublicSerializer(first_question).data

        return Response(
            {
                "attempt_id": attempt.id,
                "quiz": quiz_serializer.data,
                "started_at": attempt.started_at,
                "first_question": first_question_data,
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
        except ValidationError as e:
            logger.error(f"Error submitting attempt ID: {attempt.id} - {str(e)}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        try:
            logger.info(f"Checking achievements for user ID: {request.user.id}")
            check_new_achievements(user=request.user, attempt=attempt)
        except Exception as e:
            logger.error(
                f"Error checking achievements for user ID: {request.user.id} - {str(e)}"
            )
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="answer", url_name="answer")
    def submit_single_answer(self, request: Request, pk=None) -> Response:
        attempt = self.get_object()
        if attempt.completed_at is not None:
            return Response(
                {"detail": "This attempt is completed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = StepByStepAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        answer_data = serializer.validated_data

        if attempt.quiz.questions.filter(id=answer_data["question_id"]).exists() is False:
            return Response(
                {"detail": "Question does not belong to this quiz."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if attempt.user_answers.filter(
            question_id=answer_data["question_id"]
        ).exists():
            return Response(
                {"detail": "This question has already been answered."},
                status=status.HTTP_400_BAD_REQUEST
            )
        with transaction.atomic():
            correct_set = set(
                AnswerOption.objects.filter(
                    question_id=answer_data["question_id"],
                    is_correct=True
                ).values_list('id', flat=True)
            )
            user_set = set(answer_data["selected_options"])

            is_correct = (user_set == correct_set)

            user_answer = UserAnswer.objects.create(
                attempt=attempt,
                question_id=answer_data["question_id"],
            )
            user_answer.selected_options.set(user_set)

        all_questions_ids = attempt.quiz.questions.values_list("id", flat=True).order_by("order")
        answered_questions_ids = set(attempt.user_answers.values_list("question_id", flat=True))
        next_question_data = None
        for q_id in all_questions_ids:
            if q_id not in answered_questions_ids:
                next_question = attempt.quiz.questions.get(id=q_id)
                next_question_data = QuestionPublicSerializer(next_question).data
                break

        return Response(
            {
                "is_correct": is_correct,
                "correct_options": list(correct_set),
                "next_question": next_question_data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"], url_path="finish", url_name="finish")
    def finish_attempt(self, request: Request, pk=None) -> Response:
        attempt = self.get_object()
        if attempt.completed_at is not None:
            return Response(
                {"detail": "This attempt has already been completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user_answer_db = attempt.user_answers.prefetch_related("selected_options")
        answer_data = []
        for ua in user_answer_db:
            answer_data.append(
                {
                    "question_id": ua.question_id,
                    "selected_options": [opt.id for opt in ua.selected_options.all()],
                }
            )
        final_score = _calculate_score(attempt, answer_data)
        attempt.score = final_score
        attempt.completed_at = timezone.now()
        attempt.save()

        return Response(
            {
                "detail": "Attempt finished successfully.",
                "score": final_score
            },
            status=status.HTTP_200_OK,
        )





