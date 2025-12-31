from django.utils import timezone
from typing import Any, Dict

from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from quiz.models import QuizAttempt, Quiz
from .models import AnswerOption, Question, Quiz, QuizAttempt, UserAnswer


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
        if not value:
            raise serializers.ValidationError(
                "Question must have at least one answer option"
            )
        if len(value) < 2:
            raise serializers.ValidationError(
                "Question must have at least two answer options"
            )
        correct_options = [option for option in value if option.get("is_correct")]
        if not correct_options:
            raise serializers.ValidationError(
                "Question must have at least one correct answer option"
            )

        return value


class QuizDetailSerializer(serializers.ModelSerializer):

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

    def validate_questions(self, value):
        if not value:
            raise serializers.ValidationError(
                "Quiz must have at least one question."
            )
        if len(value) > 20 :
            raise serializers.ValidationError(
                "Quiz must have no more 20 questions."
            )
        return value

    def create(self, validated_data: Dict[str, Any]) -> Quiz:

        questions_data = validated_data.pop("questions")

        with transaction.atomic():
            quiz = Quiz.objects.create(**validated_data)
            for index, question_data in enumerate(questions_data, start=1):
                options_data = question_data.pop("answer_options")
                question = Question.objects.create(quiz=quiz, **question_data, order=index)
                answer_options_objs = [
                    AnswerOption(question=question, **option_data)
                    for option_data in options_data
                ]
                AnswerOption.objects.bulk_create(answer_options_objs)
        return quiz

    def update(self, instance: Quiz, validated_data: Dict[str, Any]) -> Quiz:

        questions_data = validated_data.pop("questions", None)

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if questions_data is None:
                return instance

            current_question_ids = {q.id for q in instance.questions.all()}

            incoming_question_ids = {
                item.get("id") for item in questions_data if item.get("id") is not None
            }

            ids_to_delete = current_question_ids - incoming_question_ids
            if ids_to_delete:
                Question.objects.filter(id__in=ids_to_delete).delete()

            for index, question_data in enumerate(questions_data, start=1):
                question_id = question_data.get("id")
                options_data = question_data.pop("answer_options", [])

                if question_id and question_id in current_question_ids:

                    question = Question.objects.get(id=question_id)

                    for attr, value in question_data.items():
                        setattr(question, attr, value)
                    question.order = index
                    question.save()
                else:
                    question = Question.objects.create(
                        quiz=instance, order=index, **question_data
                    )

                question.answer_options.all().delete()
                new_options = [
                    AnswerOption(question=question, **opt)
                    for opt in options_data
                ]
                AnswerOption.objects.bulk_create(new_options)
        return instance

class QuizListSerializer(serializers.ModelSerializer):
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
        fields = ['answers', 'completed_at']
        read_only_fields = ['completed_at']

    def validate_answers(self, values):
        valid_questions_ids = set(self.instance.quiz.questions.values_list('id', flat=True))

        for answer_item in values:
            q_id = answer_item['question_id']
            if q_id not in valid_questions_ids:
                raise ValidationError(f"Question with id {q_id} does not belong to this quiz.")
        return values


    def update(self, instance, validated_data: Dict[str, Any]) -> QuizAttempt:
        answers_data = validated_data.pop('answers')

        with transaction.atomic():

            instance.completed_at = timezone.now()
            instance.save()


            for answer_data in answers_data:
                question_id = answer_data['question_id']
                selected_option_ids = answer_data['selected_options']

                user_answer = UserAnswer.objects.create(
                    attempt=instance,
                    question_id=question_id,
                )
                user_answer.selected_options.set(selected_option_ids)

        return instance

