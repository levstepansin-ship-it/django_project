# Hand-written transition migration: anonymous (author/fingerprint) → auth (User FK) + Favorite model.
# Generated 2026-06-27 to switch comments and likes to authenticated users.

import django.db.models.deletion
from django.db import migrations, models


def get_or_create_admin(apps, schema_editor):
    """Resolve the admin user id; create it if missing (mirrors views.create_admin_if_not_exists)."""
    User = apps.get_model('auth', 'User')
    admin = User.objects.filter(username='admin').first()
    if admin is None:
        admin = User.objects.create_superuser('admin', '', 'admin123')
    return admin.id


def assign_comments_to_admin(apps, schema_editor):
    admin_id = get_or_create_admin(apps, schema_editor)
    Comment = apps.get_model('recipes', 'Comment')
    Comment.objects.filter(user__isnull=True).update(user=admin_id)


def assign_likes_to_admin(apps, schema_editor):
    admin_id = get_or_create_admin(apps, schema_editor)
    CommentLike = apps.get_model('recipes', 'CommentLike')
    CommentLike.objects.filter(user__isnull=True).update(user=admin_id)


def assign_ratings_to_admin(apps, schema_editor):
    admin_id = get_or_create_admin(apps, schema_editor)
    Rating = apps.get_model('recipes', 'Rating')
    Rating.objects.filter(user__isnull=True).update(user=admin_id)


def assign_prefs_to_admin(apps, schema_editor):
    admin_id = get_or_create_admin(apps, schema_editor)
    UserPreferences = apps.get_model('recipes', 'UserPreferences')
    UserPreferences.objects.filter(user__isnull=True).update(user=admin_id)


def noop_reverse(apps, schema_editor):
    """Reverse is not meaningfully supported (we drop author/fingerprint)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('recipes', '0005_comment_parent_commentlike'),
    ]

    operations = [
        # ----- Comment: add user FK (nullable first) -----
        migrations.AddField(
            model_name='comment',
            name='user',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='comments',
                to='auth.user',
            ),
        ),
        # Backfill existing rows → admin
        migrations.RunPython(assign_comments_to_admin, noop_reverse),
        # Promote to NOT NULL
        migrations.AlterField(
            model_name='comment',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='comments',
                to='auth.user',
            ),
        ),
        # Drop the old anonymous author column
        migrations.RemoveField(
            model_name='comment',
            name='author',
        ),

        # ----- CommentLike: add user FK (nullable first) -----
        migrations.AddField(
            model_name='commentlike',
            name='user',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='auth.user',
            ),
        ),
        migrations.RunPython(assign_likes_to_admin, noop_reverse),
        migrations.AlterField(
            model_name='commentlike',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='auth.user',
            ),
        ),
        # Drop the old fingerprint column and its unique constraint
        migrations.AlterUniqueTogether(
            name='commentlike',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='commentlike',
            name='fingerprint',
        ),
        migrations.AlterUniqueTogether(
            name='commentlike',
            unique_together={('comment', 'user')},
        ),

        # ----- Favorite: new model -----
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorited_by', to='recipes.recipe')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorites', to='auth.user')),
            ],
            options={
                'unique_together': {('user', 'recipe')},
            },
        ),

        # ----- Rating: fingerprint → user -----
        migrations.AddField(
            model_name='rating',
            name='user',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='auth.user',
            ),
        ),
        migrations.RunPython(assign_ratings_to_admin, noop_reverse),
        migrations.AlterField(
            model_name='rating',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='auth.user',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='rating',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='rating',
            name='fingerprint',
        ),
        migrations.AlterUniqueTogether(
            name='rating',
            unique_together={('recipe', 'user')},
        ),

        # ----- UserPreferences: fingerprint → OneToOne(user) -----
        migrations.AddField(
            model_name='userpreferences',
            name='user',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='prefs',
                to='auth.user',
            ),
        ),
        migrations.RunPython(assign_prefs_to_admin, noop_reverse),
        migrations.AlterField(
            model_name='userpreferences',
            name='user',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='prefs',
                to='auth.user',
            ),
        ),
        migrations.RemoveField(
            model_name='userpreferences',
            name='fingerprint',
        ),
    ]
