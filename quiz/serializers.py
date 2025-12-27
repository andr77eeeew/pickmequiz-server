from typing import Any, Dict

from django.db import transaction
from rest_framework import serializers

from .models import AnswerOption, Question, QuestionType, Quiz


class AnswerOptionSerializer(serializers.ModelSerializer):

    class Meta:
        model = AnswerOption
        fields = ["id", "text", "is_correct"]


class QuestionSerializer(serializers.ModelSerializer):

    answer_options = AnswerOptionSerializer(many=True)

    answer_type = serializers.ChoiceField(choices=QuestionType.choices)

    class Meta:
        model = Question
        fields = [
            "id",
            "title",
            "answer_type",
            "order",
            "question_photo",
            "answer_options",
        ]

    def validate_answer_options(self, value):
        if not value:
            raise serializers.ValidationError(
                "Question must have at least one answer option"
            )
        return value


class QuizSerializer(serializers.ModelSerializer):

    questions = QuestionSerializer(many=True)

    creator = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "is_time_limited",
            "time_limit",
            "created_at",
            "creator",
            "questions",
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data: Dict[str, Any]) -> Quiz:

        questions_data = validated_data.pop("questions")

        with transaction.atomic():
            quiz = Quiz.objects.create(**validated_data)

            for question_data in questions_data:
                options_data = question_data.pop("answer_options")

                question = Question.objects.create(quiz=quiz, **question_data)

                answer_options_objs = [
                    AnswerOption(question=question, **option_data)
                    for option_data in options_data
                ]
                AnswerOption.objects.bulk_create(answer_options_objs)
        return quiz
