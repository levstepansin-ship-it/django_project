from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('recipe/<int:recipe_id>/', views.recipe_detail, name='recipe_detail'),
    path('recipe/<int:recipe_id>/rate/', views.rate_recipe, name='rate_recipe'),
    path('recipe/random/', views.random_recipe, name='random_recipe'),
    path('privacy/', views.privacy, name='privacy'),
    path('search/', views.search, name='search'),
    path('terms/', views.terms, name='terms'),
    path('send-feedback/', views.send_feedback, name='send-feedback'),
    path('suggest/', views.suggest_recipe, name='suggest_recipe'),
    path('recipe/<int:recipe_id>/comment/', views.add_comment, name='add_comment'),
    path('comment/<int:comment_id>/like/', views.toggle_comment_like, name='toggle_comment_like'),
    path('favorites/', views.favorites, name='favorites'),
    path('settings/', views.settings_page, name='settings'),
    path('api/settings/', views.api_settings, name='api_settings'),
]