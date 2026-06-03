from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Recipe
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def index(request):
    return render(request, 'recipes/index.html')

def recipe_detail(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    return render(request, 'recipes/recipe_detail.html', {'recipe': recipe})

def privacy(request):
    return render(request, 'recipes/privacy.html')

def search(request):
    query = request.GET.get('q', '')
    results = []
    if query:
        results = Recipe.objects.filter(
            Q(title__icontains=query) |
            Q(subcategory__name__icontains=query) |
            Q(subcategory__category__name__icontains=query)
        )
    return render(request, 'recipes/search_results.html', {'query': query, 'results': results})

def terms(request):
    return render(request, 'recipes/terms.html')

@csrf_exempt
def send_feedback(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            timer_name = data.get('timer_name', 'Неизвестно')
            success = data.get('success', True)
            comment = data.get('comment', '')
        except:
            return JsonResponse({'error': 'Ошибка формата запроса'}, status=400)
        
        emoji = '✅' if success else '❌'
        result_text = 'ГОТОВО' if success else 'НЕ ГОТОВО'
        message = f"{emoji} НОВЫЙ ОТЗЫВ\n\nРецепт: {timer_name}\nРезультат: {result_text}\n\n📝 Комментарий:\n{comment or '—'}\n\n🔒 Анонимный отзыв. Личные данные не указаны."
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
        
        try:
            requests.post(url, json=payload, timeout=10)
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Метод не поддерживается'}, status=405)