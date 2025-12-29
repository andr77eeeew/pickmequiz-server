from django.contrib.auth import get_user_model
from rest_framework import serializers
from quiz.models import Quiz
User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
        )

    def create(self, validated_data):
        user = User(
            username=validated_data["username"],
            email=validated_data["email"],
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


class FavouriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = ("id", 'title', "description")

class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    favourite_tests = FavouriteSerializer(many=True)

    passed_tests_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "avatar", "about", "favourite_tests", "passed_tests_count")

    def get_avatar(self, obj):
        request = self.context.get("request")
        if obj.avatar:
            return request.build_absolute_uri(obj.avatar.url)
        return None

    def get_passed_tests_count(self, obj):
        return obj.quiz_attempts.filter(completed_at__isnull=False).values("quiz").distinct().count()
