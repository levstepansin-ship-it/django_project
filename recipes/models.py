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