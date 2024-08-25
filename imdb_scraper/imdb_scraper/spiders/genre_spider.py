import scrapy
import sqlite3
from media.models import Genre 
from asgiref.sync import sync_to_async
from django.db.utils import IntegrityError

class GenreSpider(scrapy.Spider):
    name = 'genre_spider'
    start_urls = ['https://www.imdb.com/interest/all/']

    async def parse(self, response):

        genres = response.css('h3.ipc-title__text::text').getall()[1:-3]
        for genre_name in genres:
            genre_name = genre_name.strip()
            print(f"Processing genre: {genre_name}")  # Debugging print

            # Save genre using sync_to_async
            await sync_to_async(self.save_genre)(genre_name)

    def save_genre(self, genre_name):
        try:
            genre, created = Genre.objects.get_or_create(name=genre_name)
            if created:
                print(f"Created new genre: {genre.name}")
            else:
                print(f"Genre already exists: {genre.name}")
        except Exception as e:
            print(f"Error saving genre {genre_name}: {e}")