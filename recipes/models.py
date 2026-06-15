from django.db import models


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
    author = models.CharField(max_length=100, blank=True, default='Аноним')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.author}: {self.text[:50]}'


class Rating(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ratings')
    score = models.PositiveSmallIntegerField()  # 1-5
    fingerprint = models.CharField(max_length=64)  # уникальный ID браузера
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('recipe', 'fingerprint')  # один голос с одного браузера

    def __str__(self):
        return f'{self.recipe.title}: {self.score}⭐'


class UserPreferences(models.Model):
    fingerprint = models.CharField(max_length=64, unique=True)
    timer_format = models.CharField(max_length=10, default='mm:ss')  # 'mm:ss' или 'seconds'

    class Meta:
        verbose_name = 'Настройки пользователя'
        verbose_name_plural = 'Настройки пользователей'

    def __str__(self):
        return f'Настройки: {self.fingerprint[:12]}… ({self.timer_format})'