from django.db import transaction
from .models import Question, AnswerOption

def update_quiz_full(quiz_instance,  questions_data):

   with transaction.atomic():

       current_question_ids = {q.id for q in quiz_instance.questions.all()}
       incoming_question_ids = {item.get("id") for item in questions_data if item.get("id")}

       ids_to_delete = current_question_ids - incoming_question_ids
       Question.objects.filter(id__in=ids_to_delete).delete()

       for index, q_data in enumerate(questions_data, start=1):
           q_id = q_data.get("id")
           options_data = q_data.pop("answer_options", [])

           question, _ = Question.objects.update_or_create(
               id=q_id,
               quiz=quiz_instance,
               defaults={**q_data, "order": index}
           )

           _update_answer_options(question, options_data)

def _update_answer_options(question, options_data):

    current_opt_ids = {opt.id for opt in question.answer_options.all()}
    incoming_opt_ids = {item.get("id") for item in options_data if item.get("id")}

    AnswerOption.objects.filter(id__in=current_opt_ids - incoming_opt_ids).delete()

    for opt_data in options_data:
        opt_id = opt_data.get("id")
        AnswerOption.objects.update_or_create(
            id=opt_id,
            question=question,
            defaults=opt_data
        )