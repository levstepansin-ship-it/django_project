#!/bin/bash

# Устанавливаем зависимости
pip install -r requirements.txt

# Собираем статику (картинки, CSS, JS)
python manage.py collectstatic --noinput

# Применяем миграции к базе данных
python manage.py migrate