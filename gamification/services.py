import logging

from .models import Achievement, UserAchievement
from .rules import ACHIEVEMENT_RULES

logger = logging.getLogger(__name__)


def check_new_achievements(user, attempt):
    exist_user_achievements = UserAchievement.objects.filter(user=user)
    exist_achievement_codes = set(ua.achievement.code for ua in exist_user_achievements)
    new_achievements = []

    for code, rule_func in ACHIEVEMENT_RULES.items():
        if code in exist_achievement_codes:
            continue
        if rule_func(user, attempt):
            try:
                achievement = Achievement.objects.get(code=code)
                user_achievement = UserAchievement.objects.create(
                    user=user, achievement=achievement
                )
                new_achievements.append(user_achievement)
            except Achievement.DoesNotExist:
                logger.error(f"Achievement with code {code} does not exist.")
