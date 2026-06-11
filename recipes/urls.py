from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('recipe/<int:recipe_id>/', views.recipe_detail, name='recipe_detail'),
    path('privacy/', views.privacy, name='privacy'),
    path('search/', views.search, name='search'),
    path('terms/', views.terms, name='terms'),
    path('send-feedback/', views.send_feedback, name='send-feedback'),
    path('suggest/', views.suggest_recipe, name='suggest_recipe'),
]