#!/bin/bash

# Устанавливаем зависимости
pip install -r requirements.txt

# Собираем статику
python manage.py collectstatic --noinput

# Применяем миграции (создаём структуру таблиц)
python manage.py migrate

# Удаляем старого админа, чтобы не было конфликта
python manage.py shell << EOF
from django.contrib.auth.models import User
User.objects.filter(username='admin').delete()
print("✅ Старый админ удалён")
EOF

# Загружаем все данные (категории, подкатегории, рецепты, пользователей)
python manage.py loaddata full_data.json