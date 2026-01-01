from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count

from quiz.models import QuizAttempt

from .models import User


class QuizAttemptInline(admin.TabularInline):
    model = QuizAttempt
    fk_name = "user"
    fields = ("quiz", "started_at", "completed_at")
    readonly_fields = ("quiz", "started_at", "completed_at")
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj):
        return False


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Extra Fields", {"fields": ("avatar", "about", "favourite_tests")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Extra Fields", {"fields": ("avatar", "about", "favourite_tests")}),
    )

    inlines = [QuizAttemptInline]
    list_display = UserAdmin.list_display + ("quiz_attempts_count",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(attempts_count=Count("quiz_attempts"))

    def quiz_attempts_count(self, obj):
        return obj.attempts_count

    quiz_attempts_count.short_description = "Quiz Attempts Count"
