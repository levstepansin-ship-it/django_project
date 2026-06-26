#!/bin/bash

# Устанавливаем зависимости
pip install -r requirements.txt

# Собираем статику
python manage.py collectstatic --noinput

# Применяем миграции
python manage.py migrate

# Загружаем все данные (категории, подкатегории, рецепты, пользователей)
python manage.py loaddata full_data.json