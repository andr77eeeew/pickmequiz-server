from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
from quiz.models import QuizAttempt

class QuizAttemptInline(admin.TabularInline):
    model = QuizAttempt
    fk_name = 'user'
    fields = ('quiz', 'started_at', 'completed_at')
    readonly_fields = ('quiz', 'started_at', 'completed_at')
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj):
        return False

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
    ('Extra Fields', {'fields': ('avatar',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
    ('Extra Fields', {'fields': ('avatar',)}),
    )

    inlines = [QuizAttemptInline]
    list_display = UserAdmin.list_display + ('quiz_attempts_count',)

    def quiz_attempts_count(self, obj):
        return obj.quiz_attempts.count()
    quiz_attempts_count.short_description = 'Quiz Attempts Count'