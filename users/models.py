from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    avatar = models.ImageField(upload_to="avatar", null=True, blank=True)
    about = models.TextField(null=True, blank=True)
    favourite_tests = models.ManyToManyField("quiz.Quiz", blank=True, related_name="favoured_by")