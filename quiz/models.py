from django.core.exceptions import ValidationError
from django.db import models

from users.models import User


# Create your models here.

class Quiz(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    is_time_limited = models.BooleanField(default=False)
    time_limit = models.DurationField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_creator')
    data = models.JSONField(default=dict)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quiz'
        ordering = ['-created_at']
        verbose_name = 'Quiz'
        verbose_name_plural = 'Quizzes'

    def __str__(self):
        return self.title

    def clean(self):
        if self.data and 'questions' not in self.data:
            raise ValidationError("Data must contain 'questions' array.")
        if self.is_time_limited and not self.time_limit:
            raise ValidationError("Time limit is required if is_time_limited is True.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
