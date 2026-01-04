from typing import Any, Dict

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import AnswerOption, Question, Quiz, QuizAttempt, UserAnswer
from .services import update_quiz_full


class AnswerOptionSerializer(serializers.ModelSerializer):

    class Meta:
        model = AnswerOption
        fields = ["id", "text", "is_correct"]


class QuestionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    answer_options = AnswerOptionSerializer(many=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "title",
            "answer_type",
            "question_photo",
            "answer_options",
        ]

    def validate_answer_options(self, value):
        if len(value) < 2:
            raise serializers.ValidationError(
                "Question must have at least 2 answer options"
            )
        if len(value) > 10:
            raise serializers.ValidationError(
                "Question must have no more than 10 answer options"
            )
        correct_answer = [opt for opt in value if opt.get("is_correct")]
        if not correct_answer:
            raise serializers.ValidationError(
                "At least one answer option must be marked as correct."
            )
        return value

    def validate(self, data):
        answer_type = data.get("answer_type")
        answer_options = data.get("answer_options", [])

        correct_count = sum(1 for opt in answer_options if opt.get("is_correct"))

        if answer_type == "single" and correct_count != 1:
            raise serializers.ValidationError(
                "For 'single' answer type, there must be exactly one correct answer option."
            )
        if answer_type == "multiple" and correct_count < 2:
            raise serializers.ValidationError(
                "For 'multiple' answer type, there must be at least two correct answer options."
            )
        return data


class QuizDetailSerializer(serializers.ModelSerializer):

    questions = QuestionSerializer(many=True)

    creator = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "category",
            "is_time_limited",
            "time_limit",
            "created_at",
            "creator",
            "questions",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        if data.get("is_time_limited") and not data.get("time_limit"):
            raise serializers.ValidationError(
                {"time_limit": "Time limit is required when quiz is time limited"}
            )

        if self.instance and self.instance.quiz_attempts.exists():
            if 'questions' in data:
                raise serializers.ValidationError(
                    "Cannot modify questions of a quiz that has attempts."
                )
        return data

    def validate_questions(self, value):
        if not value:
            raise serializers.ValidationError("Quiz must have at least one question.")
        if len(value) > 20:
            raise serializers.ValidationError("Quiz must have no more 20 questions.")
        return value

    def create(self, validated_data: Dict[str, Any]) -> Quiz:

        questions_data = validated_data.pop("questions")

        with transaction.atomic():
            quiz = Quiz.objects.create(**validated_data)
            for index, question_data in enumerate(questions_data, start=1):
                options_data = question_data.pop("answer_options")
                question = Question.objects.create(
                    quiz=quiz, **question_data, order=index
                )
                answer_options_objs = [
                    AnswerOption(question=question, **option_data)
                    for option_data in options_data
                ]
                AnswerOption.objects.bulk_create(answer_options_objs)
        return quiz

    def update(self, instance: Quiz, validated_data: Dict[str, Any]) -> Quiz:
        questions_data = validated_data.pop("questions", None)

        super().update(instance, validated_data)

        if questions_data is not None:
            update_quiz_full(instance, questions_data)

        return instance


class QuizListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "category",
            "is_time_limited",
            "time_limit",
            "created_at",
            "creator",
        ]
        read_only_fields = ["id", "created_at"]


class UserAnswerInputSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_options = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )


class QuizAttemptStartSerializer(serializers.ModelSerializer):

    class Meta:
        model = QuizAttempt
        fields = ["id", "quiz", "user", "started_at"]
        read_only_fields = ["id", "user", "started_at"]


class QuizAttemptSubmitSerializer(serializers.ModelSerializer):
    answers = UserAnswerInputSerializer(many=True, write_only=True)

    class Meta:
        model = QuizAttempt
        fields = ["answers", "completed_at", "score"]
        read_only_fields = ["completed_at", "score"]

    def validate_selected_options(self, value, selected_option):
        if value.answer_type == "single" and len(selected_option) != 1:
            raise ValidationError(
                "Single answer question must have exactly one selected option."
            )

        if not selected_option:
            raise ValidationError("At least one answer option must be selected.")

        valid_options = set(value.answer_options.value_list("id", flat=True))
        selected_ids = set(opt.id for opt in selected_option)

        if not selected_ids.issubset(valid_options):
            raise ValidationError(
                "One or more selected options are invalid for the question."
            )
        return value

    def validate_answers(self, values):
        quiz_questions = self.instance.quiz.questions.all()
        valid_questions_ids = set(
            self.instance.quiz.questions.values_list("id", flat=True)
        )

        questions_map = {q.id: q for q in quiz_questions}

        seen_questions = set()

        for answer_item in values:
            q_id = answer_item["question_id"]
            selected_ids = answer_item["selected_options"]

            if q_id not in valid_questions_ids:
                raise ValidationError(
                    f"Question with id {q_id} does not belong to this quiz."
                )

            if q_id in seen_questions:
                raise ValidationError(
                    f"Duplicate answers found for question id {q_id}."
                )
            seen_questions.add(q_id)

            question = questions_map[q_id]

            valid_options_ids = set(question.answer_options.values_list('id', flat=True))

            if not set(selected_ids).issubset(valid_options_ids):
                raise ValidationError(
                    f"One or more selected options are invalid for question id {q_id}."
                )
            if question.answer_type == "single" and len(selected_ids) != 1:
                raise ValidationError(
                    f"Question id {q_id} requires exactly one selected option."
                )

        return values

    def update(self, instance, validated_data: Dict[str, Any]) -> QuizAttempt:
        answers_data = validated_data.pop("answers")

        question_score = instance.quiz.get_question_score()

        correct_answers_map = {}

        questions = instance.quiz.questions.prefetch_related("answer_options")

        for q in questions:
            correct_opts = set(opt.id for opt in q.answer_options.all() if opt.is_correct)
            correct_answers_map[q.id] = correct_opts

        total_score = 0.0
        user_answers_to_create = []
        with transaction.atomic():
            for answer_data in answers_data:
                q_id = answer_data["question_id"]
                selected_ids = set(answer_data["selected_options"])

                correct_ids = correct_answers_map.get(q_id, set())

                if selected_ids == correct_ids and correct_ids:
                    total_score += question_score

                user_answer = UserAnswer(
                    attempt=instance,
                    question_id=q_id,
                )
                user_answers_to_create.append((user_answer, selected_ids))

            instance.score = total_score
            instance.completed_at = timezone.now()
            instance.save()

            created_answers = UserAnswer.objects.bulk_create([x[0] for x in user_answers_to_create])

            for ua, ids in zip(created_answers, [x[1] for x in user_answers_to_create]):
                ua.selected_options.set(ids)

        return instance
