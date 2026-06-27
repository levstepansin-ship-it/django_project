from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .models import Recipe, Comment, CommentLike, Rating, Favorite, UserPreferences
from .forms import RegisterForm, LoginForm
import os
import requests
import json
from dotenv import load_dotenv
from django.db import connection
from django.db.utils import OperationalError

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


# ===== СОЗДАНИЕ АДМИНА =====
def create_admin_if_not_exists():
    from django.contrib.auth.models import User
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', '', 'admin123')
        print("✅ Админ создан через views.py!")
    else:
        print("⚠️ Админ уже существует")


# ===== ПРОВЕРКА ТАБЛИЦ КОММЕНТАРИЕВ =====
def ensure_comments_table():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM recipes_comment LIMIT 1")
    except OperationalError:
        from django.core.management import call_command
        call_command('migrate', verbosity=0)


# ===== ГЛАВНАЯ СТРАНИЦА =====
def index(request):
    create_admin_if_not_exists()
    return render(request, 'recipes/index.html', {
        'total_recipes': Recipe.objects.count(),
    })


# ===== СТРАНИЦА РЕЦЕПТА =====
def recipe_detail(request, recipe_id):
    ensure_comments_table()
    recipe = get_object_or_404(Recipe, id=recipe_id)

    related = Recipe.objects.filter(
        subcategory__category=recipe.subcategory.category
    ).exclude(id=recipe.id)[:3]

    sort_order = request.GET.get('sort', 'new')
    if sort_order == 'old':
        comments = recipe.comments.filter(parent=None).order_by('created_at')
    else:
        comments = recipe.comments.filter(parent=None).order_by('-created_at')

    # Собираем ответы для каждого комментария
    comments_data = []
    for c in comments:
        replies_list = list(c.replies.all().order_by('created_at'))
        # Отмечаем лайки текущего пользователя
        user_liked = False
        reply_liked_ids = []
        if request.user.is_authenticated:
            user_liked = CommentLike.objects.filter(comment=c, user=request.user).exists()
            liked_replies = CommentLike.objects.filter(
                comment__in=replies_list, user=request.user
            ).values_list('comment_id', flat=True)
            reply_liked_ids = list(liked_replies)

        comments_data.append({
            'comment': c,
            'replies': replies_list,
            'user_liked': user_liked,
            'reply_liked_ids': reply_liked_ids,
        })

    # Проверяем, в избранном ли рецепт
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, recipe=recipe).exists()

    return render(request, 'recipes/recipe_detail.html', {
        'recipe': recipe,
        'related': related,
        'comments_data': comments_data,
        'sort_order': sort_order,
        'is_favorited': is_favorited,
    })


# ===== СЛУЧАЙНЫЙ РЕЦЕПТ =====
def random_recipe(request):
    recipe = Recipe.objects.order_by('?').first()
    if recipe:
        return redirect('recipe_detail', recipe_id=recipe.id)
    return redirect('index')


# ===== ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ =====
def privacy(request):
    return render(request, 'recipes/privacy.html')


# ===== ПОИСК =====
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


# ===== УСЛОВИЯ ИСПОЛЬЗОВАНИЯ =====
def terms(request):
    return render(request, 'recipes/terms.html')


# ===== ОТПРАВКА ОТЗЫВА В TELEGRAM =====
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


# ===== РЕЙТИНГ =====
@login_required
@csrf_exempt
def rate_recipe(request, recipe_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        recipe = get_object_or_404(Recipe, id=recipe_id)
        data = json.loads(request.body)
        score = int(data.get('score', 0))
        if not (1 <= score <= 5):
            return JsonResponse({'error': 'Invalid data'}, status=400)
        Rating.objects.update_or_create(
            recipe=recipe, user=request.user,
            defaults={'score': score}
        )
        return JsonResponse({
            'avg': round(recipe.avg_rating, 1),
            'count': recipe.rating_count,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ===== ПРЕДЛОЖЕНИЕ РЕЦЕПТА =====
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


# ===== ДОБАВЛЕНИЕ КОММЕНТАРИЯ =====
@login_required
def add_comment(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        parent_id = request.POST.get('parent_id', '').strip()
        if text:
            parent = None
            if parent_id:
                try:
                    parent = Comment.objects.get(id=int(parent_id), recipe=recipe)
                except (Comment.DoesNotExist, ValueError):
                    pass
            Comment.objects.create(recipe=recipe, user=request.user, text=text, parent=parent)
    sort_order = request.POST.get('sort', 'new')
    return redirect(f"{reverse('recipe_detail', kwargs={'recipe_id': recipe_id})}?sort={sort_order}")


# ===== ЛАЙК КОММЕНТАРИЯ =====
@login_required
@csrf_exempt
def toggle_comment_like(request, comment_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        comment = get_object_or_404(Comment, id=comment_id)
        like, created = CommentLike.objects.get_or_create(
            comment=comment, user=request.user
        )
        if created:
            return JsonResponse({'liked': True, 'count': comment.likes.count()})
        else:
            like.delete()
            return JsonResponse({'liked': False, 'count': comment.likes.count()})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ===== ИЗБРАННОЕ (страница) =====
@login_required
def favorites(request):
    favs = Favorite.objects.filter(user=request.user).select_related('recipe').order_by('-created_at')
    return render(request, 'recipes/favorites.html', {'favorites': favs})


# ===== ИЗБРАННОЕ — ДОБАВИТЬ (API) =====
@login_required
@csrf_exempt
def api_favorite_add(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
        recipe_id = int(data.get('recipe_id', 0))
        recipe = get_object_or_404(Recipe, id=recipe_id)
        fav, created = Favorite.objects.get_or_create(user=request.user, recipe=recipe)
        return JsonResponse({'status': 'ok', 'created': created})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ===== ИЗБРАННОЕ — УДАЛИТЬ (API) =====
@login_required
@csrf_exempt
def api_favorite_remove(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
        recipe_id = int(data.get('recipe_id', 0))
        deleted, _ = Favorite.objects.filter(user=request.user, recipe_id=recipe_id).delete()
        return JsonResponse({'status': 'ok', 'deleted': deleted > 0})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ===== НАСТРОЙКИ (страница) =====
@login_required
def settings_page(request):
    return render(request, 'recipes/settings.html')


# ===== API ДЛЯ НАСТРОЕК =====
@login_required
@csrf_exempt
def api_settings(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            timer_format = data.get('timer_format', 'mm:ss')
            if timer_format not in ('mm:ss', 'seconds'):
                timer_format = 'mm:ss'
            UserPreferences.objects.update_or_create(
                user=request.user,
                defaults={'timer_format': timer_format},
            )
            return JsonResponse({'status': 'ok', 'timer_format': timer_format})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    elif request.method == 'GET':
        prefs = UserPreferences.objects.filter(user=request.user).first()
        if prefs:
            return JsonResponse({'timer_format': prefs.timer_format})
        return JsonResponse({'timer_format': 'mm:ss'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ===== РЕГИСТРАЦИЯ =====
def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            if not form.cleaned_data.get('agree_privacy'):
                form.add_error('agree_privacy', 'Необходимо принять соглашение')
            else:
                user = form.save()
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, f'Добро пожаловать, {user.username}! 🎉')
                return redirect('index')
    else:
        form = RegisterForm()
    return render(request, 'recipes/register.html', {'form': form})


# ===== ВХОД =====
def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    next_url = request.GET.get('next', '/')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, f'С возвращением, {request.user.username}! 👋')
            return redirect(next_url)
    else:
        form = LoginForm()
    return render(request, 'recipes/login.html', {'form': form, 'next': next_url})


# ===== ВЫХОД =====
def logout_view(request):
    logout(request)
    messages.info(request, 'Вы вышли из аккаунта')
    return redirect('index')
