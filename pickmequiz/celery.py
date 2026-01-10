import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pickmequiz.settings")

app = Celery("pickmequiz")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
