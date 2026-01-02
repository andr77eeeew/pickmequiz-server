# PickMeQuiz Server

[![Django CI with Coverage](https://github.com/andr77eeeew/pickmequiz-server/actions/workflows/ci.yml/badge.svg)](https://github.com/andr77eeeew/pickmequiz-server/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/andr77eeeew/pickmequiz-server/branch/dev/graph/badge.svg)](https://codecov.io/gh/andr77eeeew/pickmequiz-server)

Backend для приложения PickMeQuiz — платформы для создания и прохождения тестов.

## Tech Stack
- Django 5.2
- Django REST Framework
- PostgreSQL
- JWT Authentication
- Docker

## Installation

```bash
git clone https://github.com/andr77eeeew/pickmequiz-server.git
cd pickmequiz-server
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Running Tests

```bash
python manage.py test
```

## API Documentation

Swagger UI: `http://localhost:8000/api/docs/`
