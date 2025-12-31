import os

from django.contrib.auth.models import AbstractUser
from django.db import models

def user_avatar_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    if not ext:
        ext = '.jpg'
    filename = f"{instance.username}_avatar{ext}"
    return f'avatars/user_{instance.id}/{filename}'


class User(AbstractUser):
    email = models.EmailField(unique=True, blank=False, null=False)
    avatar = models.ImageField(upload_to=user_avatar_path, null=True, blank=True)
    about = models.TextField(null=True, blank=True)
    favourite_tests = models.ManyToManyField(
        "quiz.Quiz",
        blank=True,
        related_name="favoured_by"
    )