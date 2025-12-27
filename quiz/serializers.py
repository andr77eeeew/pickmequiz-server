from rest_framework import serializers
from .models import Quiz

class QuizSerializer(serializers.ModelSerializer):


    class Meta:
        model = Quiz
        fields = ['id', 'title', 'description', 'is_time_limited', 'time_limit', 'created_at', 'creator', 'data', 'last_modified']
        read_only_fields = ['id', 'created_at', 'last_modified', 'creator']

    def validate_data(self, value):
        if value and 'questions' not in value:
            raise serializers.ValidationError("Data must contain 'questions' array.")
        return value

    def create(self, validated_data):
        validated_data['creator'] = self.context['request'].user
        return super().create(validated_data)
