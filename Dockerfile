# Используем официальный образ Python
FROM python:3.9-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта в контейнер
COPY . .

# Открываем порт, на котором будет работать приложение
EXPOSE 5000

# Определяем команду для запуска приложения
CMD ["python", "manage.py", "runserver", "-h", "0.0.0.0"]
