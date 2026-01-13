from django.db import transaction
from django.utils import timezone

from .models import AnswerOption, Question, UserAnswer


def update_quiz_full(quiz_instance, questions_data):

    with transaction.atomic():

        current_question_ids = {q.id for q in quiz_instance.questions.all()}
        incoming_question_ids = {
            item.get("id") for item in questions_data if item.get("id")
        }

        ids_to_delete = current_question_ids - incoming_question_ids
        Question.objects.filter(id__in=ids_to_delete).delete()

        for index, q_data in enumerate(questions_data, start=1):
            q_id = q_data.get("id")
            options_data = q_data.pop("answer_options", [])

            question, _ = Question.objects.update_or_create(
                id=q_id, quiz=quiz_instance, defaults={**q_data, "order": index}
            )

            _update_answer_options(question, options_data)


def _update_answer_options(question, options_data):

    current_opt_ids = {opt.id for opt in question.answer_options.all()}
    incoming_opt_ids = {item.get("id") for item in options_data if item.get("id")}

    AnswerOption.objects.filter(id__in=current_opt_ids - incoming_opt_ids).delete()

    for opt_data in options_data:
        opt_id = opt_data.get("id")
        AnswerOption.objects.update_or_create(
            id=opt_id, question=question, defaults=opt_data
        )

def submit_attempt(quiz_attempt, user_answers_data):
    user_answers_to_create = []
    with transaction.atomic():
        for answer_data in user_answers_data:
            q_id = answer_data["question_id"]
            selected_ids = set(answer_data["selected_options"])

            user_answer = UserAnswer(
                attempt=quiz_attempt,
                question_id=q_id,
            )
            user_answers_to_create.append((user_answer, selected_ids))

        total_score = _calculate_score(quiz_attempt, user_answers_data)
        if quiz_attempt.is_expired():
            quiz_attempt.score = 0.0
        else:
            quiz_attempt.score = total_score
        quiz_attempt.completed_at = timezone.now()
        quiz_attempt.save()

        created_answers = UserAnswer.objects.bulk_create(
            [x[0] for x in user_answers_to_create]
        )

        for ua, ids in zip(created_answers, [x[1] for x in user_answers_to_create]):
            ua.selected_options.set(ids)


def _calculate_score(quiz_attempt, user_answers_data):
    question_score = quiz_attempt.quiz.get_question_score()

    correct_answers_map = {}

    questions = quiz_attempt.quiz.questions.prefetch_related("answer_options")

    for q in questions:
        correct_opts = set(
            opt.id for opt in q.answer_options.all() if opt.is_correct
        )
        correct_answers_map[q.id] = correct_opts

    total_score = 0.0

    for answer_data in user_answers_data:
        q_id = answer_data["question_id"]
        selected_ids = set(answer_data["selected_options"])

        correct_ids = correct_answers_map.get(q_id, set())

        if selected_ids == correct_ids and correct_ids:
            total_score += question_score

    return total_score