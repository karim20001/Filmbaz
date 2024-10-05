from django.apps import AppConfig
from django.db import connection
from django.db.transaction import on_commit


class ImdbScraperConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'imdb_scraper'

    def ready(self):
        # Ensures this code is run after the app registry is ready and the database is available.
        on_commit(self.start_celery_task)

    def start_celery_task(self):
        """This method runs the Celery task once the app is fully loaded."""
        from .tasks import run_update_episode_spider
        run_update_episode_spider.delay()  # Start the Celery task after Django is ready
