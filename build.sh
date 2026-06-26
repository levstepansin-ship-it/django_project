#!/bin/bash

# Устанавливаем зависимости
pip install -r requirements.txt

# Собираем статику
python manage.py collectstatic --noinput

# Применяем миграции
python manage.py migrate

# Создаём суперпользователя (гарантированно)
python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("✅ Суперпользователь создан!")
else:
    print("⚠️ Суперпользователь уже существует")
EOF