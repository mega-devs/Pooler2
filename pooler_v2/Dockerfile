# Базовый образ Python
FROM python:3.12-slim

# Установка необходимых зависимостей и скачивание dockerize
RUN apt-get update && apt-get install -y \
    libpq-dev gcc curl && \
    apt-get clean && \
    curl -L https://github.com/jwilder/dockerize/releases/download/v0.6.1/dockerize-linux-amd64-v0.6.1.tar.gz \
    | tar -C /usr/local/bin -xz

# Установка рабочей директории
WORKDIR /app

# Копирование зависимостей
COPY requirements.txt .

# Установка зависимостей Python
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода приложения
COPY . .

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=root.settings

# Сборка статических файлов
RUN python manage.py collectstatic --noinput

# Команда запуска контейнера
CMD ["dockerize", "-wait", "tcp://db:5432", "-timeout", "30s", "bash", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]