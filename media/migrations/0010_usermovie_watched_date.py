# Generated by Django 5.0.7 on 2024-08-14 20:50

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('media', '0009_rename_added_count_movie_users_added_count_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='usermovie',
            name='watched_date',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
