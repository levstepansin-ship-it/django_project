#!/bin/bash

# Устанавливаем зависимости
pip install -r requirements.txt

# Собираем статику
python manage.py collectstatic --noinput

# Применяем миграции
python manage.py migrate

# Пересоздаём суперпользователя (гарантированно)
python manage.py shell << EOF
from django.contrib.auth.models import User
User.objects.filter(username='admin').delete()
User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
print("✅ Админ пересоздан!")
EOF

# Загружаем рецепты из дампа
python manage.py loaddata full_data.json