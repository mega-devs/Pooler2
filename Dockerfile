FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p app/data/temp_logs
RUN touch app/data/temp_logs/temp_smtp.log \
         app/data/temp_logs/temp_imap.log \
         app/data/temp_logs/socks.log \
         app/data/temp_logs/url_fetch.log \
         app/data/temp_logs/telegram_fetch.log


COPY . .

CMD ["sh", "-c", "python manage.py makemigrations && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
