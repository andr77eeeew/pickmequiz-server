from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from gamification.models import Achievement, UserAchievement
from rest_framework import serializers

from quiz.models import Quiz

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
        )

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value

    def create(self, validated_data):
        user = User(
            username=validated_data["username"],
            email=validated_data["email"],
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class FavouriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = ("id", "title", "description")


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = ("title", "description", "icon", "code")


class UserAchievementSerializer(serializers.ModelSerializer):
    achievement = AchievementSerializer()

    class Meta:
        model = UserAchievement
        fields = ("achievement", "received_at")


class UserSerializer(serializers.ModelSerializer):
    favourite_tests = FavouriteSerializer(many=True)
    passed_tests_count = serializers.SerializerMethodField()
    achievements = UserAchievementSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "avatar",
            "about",
            "favourite_tests",
            "passed_tests_count",
            "achievements",
        )
        read_only_fields = (
            "id",
            "username",
            "email",
            "passed_tests_count",
            "achievements",
        )

    def get_passed_tests_count(self, obj):
        return (
            obj.quiz_attempts.filter(completed_at__isnull=False)
            .values("quiz")
            .distinct()
            .count()
        )


class LeaderboardUserSerializer(serializers.ModelSerializer):
    total_score = serializers.FloatField(read_only=True)
    tests_passed = serializers.IntegerField(read_only=True)
    average_time = serializers.DurationField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "avatar",
            "total_score",
            "tests_passed",
            "average_time",
        ]
