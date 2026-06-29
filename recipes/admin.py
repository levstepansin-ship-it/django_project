from django.contrib import admin
from .models import Category, Subcategory, Recipe, Comment, CommentLike, Rating, Favorite, UserPreferences, UserProfile, PushSubscription

admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(Recipe)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'user', 'created_at', 'is_approved')
    list_filter = ('is_approved', 'recipe')
    search_fields = ('user__username', 'text')
    list_editable = ('is_approved',)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'user', 'score', 'created_at')
    list_filter = ('score',)
    search_fields = ('recipe__title', 'user__username')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'created_at')
    search_fields = ('user__username', 'recipe__title')


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ('user', 'timer_format')
    search_fields = ('user__username',)


admin.site.register(CommentLike)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio', 'show_email')
    search_fields = ('user__username',)


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'endpoint', 'created_at')
    search_fields = ('user__username',)