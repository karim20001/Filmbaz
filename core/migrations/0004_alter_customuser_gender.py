# Generated by Django 5.0.7 on 2024-07-27 11:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_alter_customuser_gender'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='gender',
            field=models.CharField(blank=True, choices=[('زن', 'زن'), ('مرد', 'مرد')], max_length=10, null=True),
        ),
    ]
