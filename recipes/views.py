from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Recipe, Comment, Rating, UserPreferences
import os
import requests
import json
from dotenv import load_dotenv
from django.db import connection
from django.db.utils import OperationalError

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


def ensure_comments_table():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM recipes_comment LIMIT 1")
    except OperationalError:
        from django.core.management import call_command
        call_command('migrate', verbosity=0)


def index(request):
    return render(request, 'recipes/index.html', {
        'total_recipes': Recipe.objects.count(),
    })


def recipe_detail(request, recipe_id):
    ensure_comments_table()
    recipe = get_object_or_404(Recipe, id=recipe_id)

    # Похожие рецепты — из той же категории
    related = Recipe.objects.filter(
        subcategory__category=recipe.subcategory.category
    ).exclude(id=recipe.id)[:3]

    return render(request, 'recipes/recipe_detail.html', {
        'recipe': recipe,
        'related': related,
    })


def random_recipe(request):
    recipe = Recipe.objects.order_by('?').first()
    if recipe:
        return redirect('recipe_detail', recipe_id=recipe.id)
    return redirect('index')


def privacy(request):
    return render(request, 'recipes/privacy.html')


def search(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        results = Recipe.objects.filter(
            Q(title__icontains=query) |
            Q(subcategory__name__icontains=query) |
            Q(subcategory__category__name__icontains=query)
        )
    if query and not results:
        return render(request, 'recipes/no_results.html', {'query': query})
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
        except Exception:
            return JsonResponse({'error': 'Invalid request format'}, status=400)

        emoji = '✅' if success else '❌'
        result_text = 'SUCCESS' if success else 'FAILED'
        message = (
            f"{emoji} NEW FEEDBACK\n\nRecipe: {timer_name}\n"
            f"Result: {result_text}\n\nComment:\n{comment or '—'}\n\n"
            f"Anonymous feedback."
        )

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': message}, timeout=10)
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def rate_recipe(request, recipe_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        recipe = get_object_or_404(Recipe, id=recipe_id)
        data = json.loads(request.body)
        score = int(data.get('score', 0))
        fingerprint = data.get('fingerprint', '').strip()
        if not (1 <= score <= 5) or not fingerprint:
            return JsonResponse({'error': 'Invalid data'}, status=400)
        Rating.objects.update_or_create(
            recipe=recipe, fingerprint=fingerprint,
            defaults={'score': score}
        )
        return JsonResponse({
            'avg': round(recipe.avg_rating, 1),
            'count': recipe.rating_count,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def suggest_recipe(request):
    if request.method == 'POST':
        query = request.POST.get('query', '')
        message = request.POST.get('message', '')
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            telegram_message = f"RECIPE SUGGESTION\n\nSearched: {query}\n\nSuggestion:\n{message}\n\nAnonymous"
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            try:
                requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': telegram_message}, timeout=10)
            except Exception:
                pass
        return render(request, 'recipes/suggest_thanks.html', {'query': query})
    return redirect('index')


def add_comment(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    if request.method == 'POST':
        author = request.POST.get('author', '').strip()
        text = request.POST.get('text', '').strip()
        if text:
            if not author:
                author = 'Anonymous'
            Comment.objects.create(recipe=recipe, author=author, text=text)
    return redirect('recipe_detail', recipe_id=recipe_id)


def favorites(request):
    return render(request, 'recipes/favorites.html')


def settings_page(request):
    return render(request, 'recipes/settings.html')


@csrf_exempt
def api_settings(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            fingerprint = data.get('fingerprint', '').strip()
            timer_format = data.get('timer_format', 'mm:ss')
            if not fingerprint:
                return JsonResponse({'error': 'No fingerprint'}, status=400)
            if timer_format not in ('mm:ss', 'seconds'):
                timer_format = 'mm:ss'
            UserPreferences.objects.update_or_create(
                fingerprint=fingerprint,
                defaults={'timer_format': timer_format},
            )
            return JsonResponse({'status': 'ok', 'timer_format': timer_format})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    elif request.method == 'GET':
        fp = request.GET.get('fingerprint', '').strip()
        if not fp:
            return JsonResponse({'error': 'No fingerprint'}, status=400)
        prefs = UserPreferences.objects.filter(fingerprint=fp).first()
        if prefs:
            return JsonResponse({'timer_format': prefs.timer_format})
        return JsonResponse({'timer_format': 'mm:ss'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)