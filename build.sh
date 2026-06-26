#!/bin/bash

# Устанавливаем зависимости
pip install -r requirements.txt

# Собираем статику (картинки, CSS, JS)
python manage.py collectstatic --noinput

# Применяем миграции к базе данных
python manage.py migrate

# Создаём суперпользователя (если его нет)
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell