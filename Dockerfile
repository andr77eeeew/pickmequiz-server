FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    netcat-openbsd  \
    && rm -rf /var/lib/apt/lists/*

# Переменные окружения для Django dev
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=pickmequiz.settings

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .
COPY entrypoint.sh /app/

RUN useradd -m -u 1000 admin \
     && chown -R admin:admin /app \
     && chmod +x /app/entrypoint.sh

USER admin

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


