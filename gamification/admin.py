from django.contrib import admin

from .models import Achievement, UserAchievement


class UsersWithAchievementInline(admin.TabularInline):
    model = UserAchievement

    fields = ("user", "received_at")
    readonly_fields = ("received_at",)
    extra = 0
    can_delete = True
    verbose_name = "User with this achievement"
    verbose_name_plural = "Users with this achievement"


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "is_secret", "users_count")
    search_fields = ("title", "code", "description")
    list_filter = ("is_secret",)
    inlines = [UsersWithAchievementInline]

    def users_count(self, obj):
        return obj.userachievement_set.count()

    users_count.short_description = "Received Count"


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ("user", "achievement", "received_at")
    list_filter = ("achievement", "received_at")
    search_fields = ("user__username", "achievement__title")
