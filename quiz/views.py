from rest_framework import viewsets, status
from .serializers import QuizSerializer
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample
from .models import Quiz

class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Quiz.objects.all()
        return Quiz.objects.none()

    @extend_schema(
        operation_id='quiz_list',
        description='Получить список всех доступных тестов, отсортированных по дате создания (новые первыми). '
                              'Для анонимных пользователей возвращается пустой список.',
        tags=['Quizzes'],
        responses={200: QuizSerializer(many=True)},
        examples=[
            OpenApiExample(
                'Пустой список (аноним)',
                value={
                    'count': 0,
                    'next': None,
                    'previous': None,
                    'results': []
                },
                status_codes=['200']
            ),
            OpenApiExample(
                'Список тестов',
                value={
                    'count': 2,
                    'next': None,
                    'previous': None,
                    'results': [
                        {
                            'quiz_id': 1,
                            'title': 'Тестовый квиз 1',
                            'is_time_limited': False,
                            'time_limit': None,
                            'created_at': '2025-11-07T20:00:00Z',
                            'creator': 'user1',
                            'data': {
                                'questions': [
                                    {
                                        'title': 'Вопрос 1',
                                        'answer_type': 'single',
                                        'answer_options': ['A', 'B'],
                                        'correct_answer_index': 0,
                                        'order': 1,
                                        'question_photo': None
                                    }
                                ]
                            },
                            'last_update': '2025-11-07T20:00:00Z'
                        }
                    ]
                },
                status_codes=['200']
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        # Дефолтный list, но с документацией
        return super().list(request, *args, **kwargs)


    @extend_schema(
        operation_id='quiz_update',
        description='Полностью обновить тест. Только автор может обновлять свой тест.',
        tags=['Quizzes'],
        request=QuizSerializer,
        responses={200: QuizSerializer},
        # Добавь permission в реальности: например, IsOwner
        examples=[
            OpenApiExample(
                'Обновление',
                value={
                    'title': 'Обновленный квиз',
                    'is_time_limited': False,
                    'time_limit': None,
                    'data': {  # Обновленные questions
                        'questions': ['A1', 'A5', 'A7']
                    }
                },
                request_only=True,
                status_codes=['200']
            )
        ]
    )
    def update(self, request, *args, **kwargs):
        # Дефолтный update с документацией
        return super().update(request, *args, **kwargs)


    @extend_schema(
        operation_id='quiz_create',
        description='Создать новый тест. Требует аутентификации. Автор автоматически устанавливается как текущий пользователь.',
        tags=['Quizzes'],
        request=QuizSerializer,
        responses={201: QuizSerializer},
        examples=[
            OpenApiExample(
                'Создание теста',
                value={
                    'title': 'Новый квиз',
                    'is_time_limited': True,
                    'time_limit': '00:30:00',
                    'data': {
                        'questions': [
                            {
                                'title': 'Новый вопрос',
                                'answer_type': 'multiple',
                                'answer_options': ['A', 'B', 'C', 'D'],
                                'correct_answer_index': [1, 3],
                                'order': 1,
                                'question_photo': 'null'
                            }
                        ]
                    }
                },
                request_only=True,
                status_codes=['201']
            ),
            OpenApiExample(
                'Успешный ответ',
                value={
                    'quiz_id': 3,
                    'title': 'Новый квиз',
                    'is_time_limited': True,
                    'time_limit': '00:30:00',
                    'created_at': '2025-11-07T20:05:00Z',
                    'creator': 'current_user',
                    'data': {
                        'questions': [
                            {
                                'title': 'Новый вопрос',
                                'answer_type': 'multiple',
                                'answer_options': ['A', 'B', 'C', 'D'],
                                'correct_answer_index': [1, 3],
                                'order': 1,
                                'question_photo': 'null'
                            }
                        ]
                    },
                    'last_update': '2025-11-07T20:05:00Z'
                },
                status_codes=['201']
            )
        ]
    )
    def create(self, validated_data):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

