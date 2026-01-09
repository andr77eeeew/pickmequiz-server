from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count
from gamification.models import UserAchievement

from quiz.models import QuizAttempt

from .models import User


class QuizAttemptInline(admin.TabularInline):
    model = QuizAttempt
    fk_name = "user"
    fields = ("quiz", "started_at", "completed_at", "score")
    readonly_fields = ("quiz", "started_at", "completed_at", "score")
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj):
        return False


class AchievementInline(admin.TabularInline):
    model = UserAchievement
    fk_name = "user"
    fields = ("achievement", "received_at")
    readonly_fields = ("received_at",)
    extra = 0
    can_delete = True


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Extra Fields", {"fields": ("avatar", "about", "favourite_tests")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Extra Fields", {"fields": ("avatar", "about", "favourite_tests")}),
    )

    inlines = [QuizAttemptInline, AchievementInline]
    list_display = UserAdmin.list_display + (
        "quiz_attempts_count",
        "achievements_count",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            attempts_count=Count("quiz_attempts", distinct=True),
            achieved_count=Count("achievements", distinct=True),
        )

    def quiz_attempts_count(self, obj):
        return obj.attempts_count

    quiz_attempts_count.short_description = "Attempts"

    def achievements_count(self, obj):
        return obj.achieved_count

    achievements_count.short_description = "Achievements"
