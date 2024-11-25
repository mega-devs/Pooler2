FROM python:3.12-slim

# Установка необходимых зависимостей и скачивание dockerize
RUN apt-get update && apt-get install -y \
    libpq-dev gcc curl && \
    apt-get clean && \
    curl -L https://github.com/jwilder/dockerize/releases/download/v0.6.1/dockerize-linux-amd64-v0.6.1.tar.gz \
    | tar -C /usr/local/bin -xz

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

# Команда запуска с использованием dockerize для ожидания базы данных
CMD ["dockerize", "-wait", "tcp://db:5432", "-timeout", "30s", "bash", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]