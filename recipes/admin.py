from django.contrib import admin
from .models import Category, Subcategory, Recipe, Comment

admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(Recipe)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'author', 'created_at', 'is_approved')
    list_filter = ('is_approved', 'recipe')
    search_fields = ('author', 'text')
    list_editable = ('is_approved',)