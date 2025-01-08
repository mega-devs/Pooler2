FROM python:3.11-slim

WORKDIR /app

ENV DOCKERIZE_VERSION v0.6.1
RUN apt-get update \
    && apt-get install -y wget \
    && wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && rm dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && apt-get clean

# RUN useradd -m appuser && chown -R appuser:appuser /app
RUN useradd -m appuser
RUN mkdir -p /app/data/temp_logs /app/data/full_logs /app/uploads && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R appuser:appuser /app

USER appuser

CMD ["dockerize", "-wait", "tcp://db:5432", "-timeout", "30s", "bash", "-c", "python manage.py makemigrations && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
