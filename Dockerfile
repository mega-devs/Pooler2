FROM python:3.11-slim

WORKDIR /app

RUN apt update && apt install -y wget gnupg2

RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && echo "deb http://apt.postgresql.org/pub/repos/apt/ bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list

RUN apt update && apt install -y postgresql-client-16 libpq-dev

COPY requirements.txt .

RUN pip install --trusted-host=pypi.python.org --trusted-host=pypi.org --trusted-host=files.pythonhosted.org --no-cache-dir -r requirements.txt

COPY entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

RUN mkdir -p app/data/temp_logs
RUN touch app/data/temp_logs/temp_smtp.log \
         app/data/temp_logs/temp_imap.log \
         app/data/temp_logs/socks.log \
         app/data/temp_logs/url_fetch.log \
         app/data/temp_logs/telegram_fetch.log

COPY . .

# commands
RUN mkdir -p coverage_reports

CMD ["sh", "-c", "python manage.py makemigrations && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]