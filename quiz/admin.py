from django.contrib import admin

from .models import AnswerOption, Question, Quiz, QuizAttempt, UserAnswer


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 1
    min_num = 2


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    show_change_link = True
    fields = ("title", "answer_type", "order")


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "creator", "created_at", "is_time_limited")
    list_filter = ("is_time_limited", "category", "created_at")
    search_fields = ("title", "description")
    inlines = [QuestionInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("questions__answer_options")

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.creator = request.user
        super().save_model(request, obj, form, change)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("title", "quiz", "answer_type", "order")
    list_filter = ("quiz", "answer_type")
    search_fields = ("title",)
    inlines = [AnswerOptionInline]

    ordering = ("quiz", "order")


class UserAnswerInline(admin.TabularInline):
    model = UserAnswer
    readonly_fields = ("question", "selected_options", "answered_at")
    can_delete = False
    extra = 0

    def has_add_permission(self, request, obj):
        return False


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "quiz", "started_at", "completed_at")
    list_filter = ("quiz", "started_at")
    inlines = [UserAnswerInline]
