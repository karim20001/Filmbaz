# Generated by Django 5.0.7 on 2024-10-14 09:08

import django.core.validators
import django.db.models.deletion
import media.models
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Actor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('bio', models.TextField(blank=True, null=True)),
                ('birth_date', models.DateField()),
                ('birth_city', models.CharField(max_length=255)),
                ('profile_photo', models.ImageField(blank=True, null=True, upload_to='actors/photos/')),
            ],
        ),
        migrations.CreateModel(
            name='Genre',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Cast',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.UUIDField()),
                ('name', models.CharField(max_length=255)),
                ('likes', models.PositiveIntegerField(default=0)),
                ('photo', models.ImageField(blank=True, null=True, upload_to='cast/photos/')),
                ('actor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cast', to='media.actor')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.UUIDField()),
                ('detail', models.TextField()),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=False)),
                ('is_spoiler', models.BooleanField(default=False)),
                ('is_proved', models.BooleanField(default=False)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('likes', models.ManyToManyField(blank=True, related_name='liked_comments', to=settings.AUTH_USER_MODEL)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='media.comment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Movie',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('duration', models.IntegerField()),
                ('imdb_rate', models.DecimalField(decimal_places=1, max_digits=2)),
                ('users_rate', models.DecimalField(blank=True, decimal_places=1, max_digits=2, null=True)),
                ('description', models.TextField()),
                ('release_date', models.DateField()),
                ('is_released', models.BooleanField()),
                ('users_rate_count', models.PositiveIntegerField(default=0)),
                ('users_added_count', models.PositiveIntegerField(default=0)),
                ('cover_photo', models.ImageField(blank=True, null=True, upload_to='movies/photos/')),
                ('genres', models.ManyToManyField(to='media.genre')),
            ],
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(max_length=50)),
                ('object_id', models.UUIDField(blank=True, null=True)),
                ('message', models.CharField(max_length=255)),
                ('is_read', models.BooleanField(default=False)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('content_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Show',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('imdb_url', models.URLField(blank=True, null=True, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('season_count', models.IntegerField(blank=True, default=1, null=True)),
                ('imdb_rate', models.DecimalField(decimal_places=1, max_digits=2)),
                ('users_rate', models.DecimalField(blank=True, decimal_places=1, max_digits=2, null=True)),
                ('release_year', models.IntegerField(blank=True, null=True)),
                ('end_year', models.IntegerField(blank=True, default=None, null=True)),
                ('duration', models.IntegerField(blank=True, null=True)),
                ('release_time', models.TimeField(blank=True, null=True)),
                ('release_day', models.CharField(max_length=50)),
                ('is_released', models.BooleanField()),
                ('network', models.CharField(blank=True, max_length=255, null=True)),
                ('users_added_count', models.PositiveIntegerField(default=0)),
                ('users_rate_count', models.PositiveIntegerField(default=0)),
                ('cover_photo', models.ImageField(blank=True, max_length=255, null=True, upload_to=media.models.show_cover_upload_to)),
                ('genres', models.ManyToManyField(to='media.genre')),
            ],
        ),
        migrations.CreateModel(
            name='Episode',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('imdb_url', models.URLField(blank=True, null=True, unique=True)),
                ('season', models.IntegerField()),
                ('duration', models.IntegerField(blank=True, null=True)),
                ('imdb_rate', models.DecimalField(decimal_places=1, max_digits=2)),
                ('users_rate', models.DecimalField(blank=True, decimal_places=1, max_digits=2, null=True)),
                ('episode_number', models.IntegerField()),
                ('release_date', models.DateField()),
                ('is_released', models.BooleanField()),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('cover_photo', models.ImageField(blank=True, null=True, upload_to=media.models.episode_cover_upload_to)),
                ('show', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='episodes', to='media.show')),
            ],
        ),
        migrations.CreateModel(
            name='UserEpisode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_rate', models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(5)])),
                ('watch_date', models.DateTimeField(auto_now_add=True)),
                ('emoji', models.CharField(blank=True, max_length=50, null=True)),
                ('episode', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_episodes', to='media.episode')),
                ('favorite_cast', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='favorite_episode_cast', to='media.cast')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_episodes', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserMovie',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('watched', models.BooleanField(default=False)),
                ('watched_date', models.DateTimeField(blank=True, default=None, null=True)),
                ('user_rate', models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(5)])),
                ('emoji', models.CharField(blank=True, max_length=50, null=True)),
                ('is_favorite', models.BooleanField(default=False)),
                ('added_date', models.DateTimeField(auto_now_add=True)),
                ('favorite_cast', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='favorite_movie_cast', to='media.cast')),
                ('movie', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_movies', to='media.movie')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_movies', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserShow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('added_date', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[(None, None), ('در حال تماشا', 'در حال تماشا'), ('متوقف شده', 'متوقف شده'), ('برای بعد', 'برای بعد')], default=None, max_length=50, null=True)),
                ('is_favorite', models.BooleanField(default=False)),
                ('user_rate', models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(5)])),
                ('show', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_shows', to='media.show')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_shows', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Follow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_accepted', models.BooleanField(default=True)),
                ('follow_date', models.DateField(auto_now_add=True)),
                ('follow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='followers', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='following', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'follow')},
            },
        ),
    ]
