import os

from django.conf import settings
from django.db import models

# Create your models here.

def achievement_icon_path(instance, filename):
    ext = os.path.splitext(filename)[1] or ".png"
    return f"achievements/icons/{instance.code}{ext}"

class Achievement(models.Model):
    code = models.CharField(unique=True, max_length=50)
    title = models.CharField(unique=True, max_length=50)
    description = models.TextField()
    icon = models.ImageField(upload_to=achievement_icon_path, null=True, blank=True)

    is_secret = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class UserAchievement(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="achievements")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "achievement")

    def __str__(self):
        return f"{self.user.username} - {self.achievement.title}"
