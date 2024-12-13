# Используем базовый образ
FROM python:3.12-slim

# Установка необходимых зависимостей
RUN apt-get update && apt-get install -y \
    libpq-dev curl && \
    apt-get clean && \
    curl -L https://github.com/jwilder/dockerize/releases/download/v0.6.1/dockerize-linux-amd64-v0.6.1.tar.gz \
    | tar -C /usr/local/bin -xz && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Скопировать файл зависимостей и установить зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Скопировать исходный код приложения
COPY . .

# Установка переменных окружения
ENV PYTHONUNBUFFERED=1

# Команда запуска приложения
CMD ["dockerize", "-wait", "tcp://db:5432", "-timeout", "30s", "bash", "-c", "python manage.py makemigrations && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]