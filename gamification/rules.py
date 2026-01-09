def check_first_blood(user, attempt):
    return user.quiz_attempts.filter(completed_at__isnull=False).count() >= 1


def check_sniper(user, attempt):
    return attempt.score >= 100.0


def check_trendsetter(user, attempt):

    return attempt.quiz.quiz_attempts.count() >= 100


def check_explorer(user, attempt):
    return attempt.quiz.quiz_attempts.count() <= 10


ACHIEVEMENT_RULES = {
    "first_blood": check_first_blood,
    "sniper": check_sniper,
    "trendsetter": check_trendsetter,
    "explorer": check_explorer,
}
