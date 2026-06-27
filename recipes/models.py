from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    slug = models.SlugField()

    def __str__(self):
        return f'{self.category.name} - {self.name}'


class Recipe(models.Model):
    subcategory = models.OneToOneField(Subcategory, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    steps = models.JSONField()
    final_message = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return self.title

    @property
    def avg_rating(self):
        ratings = self.ratings.all()
        if ratings:
            return sum(r.score for r in ratings) / len(ratings)
        return 0

    @property
    def rating_count(self):
        return self.ratings.count()


class Comment(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username}: {self.text[:50]}'

    @property
    def author_name(self):
        return self.user.username

    @property
    def likes_count(self):
        return self.likes.count()


class CommentLike(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('comment', 'user')

    def __str__(self):
        return f'Like by {self.user.username} on comment {self.comment.id}'


class Rating(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.PositiveSmallIntegerField()  # 1-5
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('recipe', 'user')  # один голос с одного пользователя

    def __str__(self):
        return f'{self.recipe.title}: {self.score}⭐ by {self.user.username}'


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'recipe')

    def __str__(self):
        return f'{self.user.username} → {self.recipe.title}'


class UserPreferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='prefs')
    timer_format = models.CharField(max_length=10, default='mm:ss')  # 'mm:ss' или 'seconds'

    class Meta:
        verbose_name = 'Настройки пользователя'
        verbose_name_plural = 'Настройки пользователей'

    def __str__(self):
        return f'Настройки: {self.user.username} ({self.timer_format})'
