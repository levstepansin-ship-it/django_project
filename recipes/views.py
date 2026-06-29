from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .models import Recipe, Comment, CommentLike, Rating, Favorite, UserPreferences, UserProfile, PushSubscription
from .forms import RegisterForm, LoginForm, ProfileForm, ChangePasswordForm
import os
import requests
import json
from dotenv import load_dotenv
from django.db import connection
from django.db.utils import OperationalError

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY', '')
VAPID_SUBJECT = os.getenv('VAPID_SUBJECT', 'mailto:admin@wajos.app')


# ===== СОЗДАНИЕ АДМИНА =====
def create_admin_if_not_exists():
    from django.contrib.auth.models import User
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', '', 'admin123')
        print("✅ Админ создан через views.py!")


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

    comments_data = []
    for c in comments:
        replies_list = list(c.replies.all().order_by('created_at'))
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
            comment = Comment.objects.create(recipe=recipe, user=request.user, text=text, parent=parent)
            if not parent:
                fav_users = Favorite.objects.filter(recipe=recipe).select_related('user').values_list('user', flat=True).distinct()
                for uid in fav_users:
                    if uid != request.user.id:
                        from django.contrib.auth.models import User as AuthUser
                        fav_user = AuthUser.objects.get(id=uid)
                        send_push_notification(
                            fav_user,
                            title=f'💬 Новый комментарий к «{recipe.title}»',
                            body=f'{request.user.username}: {text[:80]}',
                            url=reverse('recipe_detail', kwargs={'recipe_id': recipe_id}),
                        )
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


# ===== ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ =====
def profile_view(request, username):
    user = get_object_or_404(User, username=username)
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = None

    prefs = UserPreferences.objects.filter(user=user).first()
    if prefs and not prefs.public_profile and request.user != user:
        messages.warning(request, 'Этот профиль закрыт')
        return redirect('index')

    comments_count = Comment.objects.filter(user=user).count()
    favorites_count = Favorite.objects.filter(user=user).count()
    likes_received = CommentLike.objects.filter(comment__user=user).count()
    recent_comments = Comment.objects.filter(user=user).select_related('recipe').order_by('-created_at')[:10]

    return render(request, 'recipes/profile.html', {
        'profile_user': user,
        'profile': profile,
        'comments_count': comments_count,
        'favorites_count': favorites_count,
        'likes_received': likes_received,
        'recent_comments': recent_comments,
    })


# ===== РЕДАКТИРОВАНИЕ ПРОФИЛЯ =====
@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'profile')

        if form_type == 'password':
            password_form = ChangePasswordForm(data=request.POST, user=request.user)
            if password_form.is_valid():
                request.user.set_password(password_form.cleaned_data['new_password1'])
                request.user.save()
                messages.success(request, 'Пароль успешно изменён! 🔄')
                return redirect('edit_profile')

            profile_form = ProfileForm(instance=request.user)
            return render(request, 'recipes/edit_profile.html', {
                'profile_form': profile_form,
                'password_form': password_form,
            })
        else:
            profile_form = ProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                profile, created = UserProfile.objects.get_or_create(user=request.user)
                profile.bio = request.POST.get('bio', '')
                profile.show_email = request.POST.get('show_email', '') == 'on'
                profile.save()
                messages.success(request, 'Профиль обновлён! ✨')
                return redirect('profile', username=request.user.username)

            password_form = ChangePasswordForm(user=request.user)
            return render(request, 'recipes/edit_profile.html', {
                'profile_form': profile_form,
                'password_form': password_form,
            })

    profile_form = ProfileForm(instance=request.user)
    password_form = ChangePasswordForm(user=request.user)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    return render(request, 'recipes/edit_profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
        'profile': profile,
    })


# ===== PUSH-УВЕДОМЛЕНИЯ =====
@login_required
@csrf_exempt
def api_push_subscribe(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
        endpoint = data.get('endpoint', '')
        p256dh_key = data.get('keys', {}).get('p256dh', '')
        auth_key = data.get('keys', {}).get('auth', '')
        if not endpoint or not p256dh_key or not auth_key:
            return JsonResponse({'error': 'Missing data'}, status=400)

        PushSubscription.objects.update_or_create(
            user=request.user, endpoint=endpoint,
            defaults={'p256dh_key': p256dh_key, 'auth_key': auth_key}
        )
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
def api_push_unsubscribe(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
        endpoint = data.get('endpoint', '')
        if endpoint:
            PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
        else:
            PushSubscription.objects.filter(user=request.user).delete()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
def api_notification_settings(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            receive = data.get('receive_notifications', True)
            UserPreferences.objects.update_or_create(
                user=request.user,
                defaults={'receive_notifications': bool(receive)},
            )
            return JsonResponse({'status': 'ok', 'receive_notifications': bool(receive)})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    elif request.method == 'GET':
        prefs = UserPreferences.objects.filter(user=request.user).first()
        receive = prefs.receive_notifications if prefs else True
        return JsonResponse({'receive_notifications': receive})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def send_push_notification(user, title, body, url='/'):
    if VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY:
        prefs = UserPreferences.objects.filter(user=user).first()
        if prefs and not prefs.receive_notifications:
            return
    try:
        from pywebpush import webpush, WebPushException
        subscriptions = PushSubscription.objects.filter(user=user)
        if not subscriptions.exists():
            return
        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={
                        'endpoint': sub.endpoint,
                        'keys': {
                            'p256dh': sub.p256dh_key,
                            'auth': sub.auth_key,
                        }
                    },
                    data=json.dumps({'title': title, 'body': body, 'url': url}),
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims={'sub': VAPID_SUBJECT},
                )
            except WebPushException:
                sub.delete()
    except ImportError:
        pass
    except Exception:
        pass


@login_required
def vapid_public_key(request):
    return JsonResponse({'key': VAPID_PUBLIC_KEY})


# ===== AI ПОМОЩНИК (Mistral) =====
@csrf_exempt
def ai_ask(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не разрешён'}, status=405)

    query = request.POST.get('query', '').strip()
    if not query:
        return JsonResponse({'error': 'Пустой запрос'}, status=400)

    try:
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "mistral-tiny",
            "messages": [{"role": "user", "content": query}]
        }
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        answer = data['choices'][0]['message']['content']
        return JsonResponse({'answer': answer})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)