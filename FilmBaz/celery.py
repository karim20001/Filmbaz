import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FilmBaz.settings')

app = Celery('FilmBaz')

# Load task modules from all registered Django app configs.
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.update(
    worker_concurrency=1,
)

# Load task modules from all registered Django apps.
app.autodiscover_tasks(['imdb_scraper.imdb_scraper'])
