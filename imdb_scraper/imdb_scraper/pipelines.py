# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
import requests
from datetime import datetime
from urllib.parse import urlparse
from scrapy.exceptions import DropItem
from media.models import Actor, Episode, Movie, Genre, Show
from asgiref.sync import sync_to_async

class ImdbScraperPipeline:
    def process_item(self, item, spider):
        return item

class ActorPipeline:

    async def process_item(self, item, spider):
        try:
            if 'birth_date' in item and item['birth_date']:
                # Convert to date format accept in database
                item['birth_date'] = datetime.strptime(item['birth_date'], '%B %d, %Y').date()

            if 'profile_photo' in item and item['profile_photo']:
                # Download the image
                image_url = item['profile_photo']
                response = requests.get(image_url)
                if response.status_code == 200:
                    # Get a name for the file from the URL
                    filename = os.path.basename(urlparse(image_url).path)
                    # Define the path where you want to save the image
                    save_path = os.path.join('../photos/actors/', filename)
                    
                    # Save the image to the local filesystem
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Replace the URL with the local path
                    item['profile_photo'] = save_path[2:]
                else:
                    raise DropItem(f"Failed to download image {image_url}")

            # Save the item to the Django model
            actor_item = Actor(
                name=item['name'],
                bio=item['bio'],
                birth_date=item['birth_date'],
                birth_city=item['birth_city'],
                profile_photo=item.get('profile_photo', None)
            )
            
            # Save the item to the database asynchronously
            await sync_to_async(actor_item.save)()

        except Exception as e:
            print(f'error: {str(e)}')
        
        return item


class MoviePipeline:

    async def process_item(self, item, spider):
        try:
            if item['is_released']:
                item['is_released'] = False

            else:
                item['is_released'] = True
            
            if 'imdb_rate' in item and item['imdb_rate']:
                item['imdb_rate'] = float(item['imdb_rate'])
            
            if 'duration' in item and item['duration']:
                duration_parts = item['duration']
                hours = int(duration_parts[0]) if 'h' in duration_parts[2] else 0
                minutes = int(duration_parts[4]) if 'minutes' in duration_parts[6] else 0
                item['duration'] = hours * 60 + minutes

            if 'release_date' in item and item['release_date']:
                item['release_date'] = datetime.strptime(item['release_date'], '%B %d, %Y').date()
            
            genre_ids = []
            if 'genres' in item and item['genres']:
                for genre in item['genres']:
                    genre_instance = await sync_to_async(Genre.objects.get)(name=genre)
                    genre_ids.append(genre_instance.id)

            if 'cover_photo' in item and item['cover_photo']:
                # Download the image
                image_url = item['cover_photo']
                response = requests.get(image_url)
                if response.status_code == 200:
                    # Get a name for the file from the URL
                    filename = os.path.basename(urlparse(image_url).path)
                    # Define the path where you want to save the image
                    save_path = os.path.join('../photos/movies/', filename)
                    
                    # Save the image to the local filesystem
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Replace the URL with the local path
                    item['cover_photo'] = save_path[2:]
                else:
                    raise DropItem(f"Failed to download image {image_url}")
            
            movie_item = Movie(
                name = item['name'],
                duration = item['duration'],
                imdb_rate = item['imdb_rate'],
                description = item['description'],
                release_date = item['release_date'],
                is_released = item['is_released'],
                cover_photo = item['cover_photo']
            )
            await sync_to_async(movie_item.save)()
            for genre_id in genre_ids:
                await sync_to_async(movie_item.genres.add)(genre_id)
        
        except Exception as e:
            print(f'error: {str(e)}')
        
        return item


class ShowPipeline:

    async def process_item(self, item, spider):
        try:
            if not item['season_count']:
                item['is_released'] = False

            else:
                item['is_released'] = True
            
            if 'imdb_rate' in item and item['imdb_rate']:
                item['imdb_rate'] = float(item['imdb_rate'])
            
            if 'season_count' in item and item['season_count']:
                item['season_count'] = int(item['season_count'])
            
            if 'duration' in item and item['duration']:
                duration_parts = item['duration']
                hours = int(duration_parts[0]) if 'hours' in duration_parts[2] else 0
                minutes = int(duration_parts[0])
                if hours > 0:
                    minutes = int(duration_parts[4]) if 'minutes' in duration_parts[6] else 0
                
                item['duration'] = hours * 60 + minutes

            if 'release_year' in item and item['release_year']:
                if item['season_count']:
                    item['release_year'] = int(item['release_year'])
                else:
                    item['release_year'] = None
            
            if 'end_year' in item and item['end_year']:
                if item['end_year'] == ' ':
                    item['end_year'] = None
                else:
                    item['end_year'] = int(item['end_year'])
            
            genre_ids = []
            if 'genres' in item and item['genres']:
                for genre in item['genres']:
                    genre_instance = await sync_to_async(Genre.objects.get)(name=genre)
                    genre_ids.append(genre_instance.id)
            
            if 'networks' in item and item['networks']:
                item['networks'] = ', '.join(item['networks'])

            if 'cover_photo' in item and item['cover_photo']:
                # Download the image
                image_url = item['cover_photo']
                response = requests.get(image_url)
                if response.status_code == 200:
                    # Get a name for the file from the URL
                    filename = os.path.basename(urlparse(image_url).path)
                    # Define the path where you want to save the image
                    save_path = os.path.join(f"../photos/shows/{item['name']}/", filename)
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    
                    # Save the image to the local filesystem
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Replace the URL with the local path
                    item['cover_photo'] = save_path[2:]
                else:
                    raise DropItem(f"Failed to download image {image_url}")
            
            show_item = Show(
                name = item['name'],
                imdb_url = item['source'],
                season_count = item['season_count'],
                duration = item['duration'],
                imdb_rate = item['imdb_rate'],
                description = item['description'],
                release_year = item['release_year'],
                end_year = item['end_year'],
                is_released = item['is_released'],
                network = item['networks'],
                cover_photo = item['cover_photo']
            )
            await sync_to_async(show_item.save)()
            for genre_id in genre_ids:
                await sync_to_async(show_item.genres.add)(genre_id)
        
        except Exception as e:
            print(f'error: {str(e)}')
        
        return item


class EpisodePipeline:

    async def process_item(self, item, spider):
        try:
            if 'imdb_rate' in item and item['imdb_rate']:
                item['imdb_rate'] = float(item['imdb_rate'])
            
            if 'season_episode' in item and item['season_episode']:
                item['season'] = item['season_episode'][0][1]
                item['episode'] = item['season_episode'][0][1]
            
            if 'duration' in item and item['duration']:
                duration_parts = item['duration']
                hours = int(duration_parts[0]) if 'hours' in duration_parts[2] else 0
                minutes = int(duration_parts[0])
                if hours > 0:
                    minutes = int(duration_parts[4]) if 'minutes' in duration_parts[6] else 0
                
                item['duration'] = hours * 60 + minutes

            if 'release_date' in item and item['release_date']:
                item['release_date'] = datetime.strptime(item['release_date'], '%B %d, %Y').date()
                if item['release_date'] > datetime.now():
                    item['is_released'] = False
            else:
                item['is_released'] = False
            
            show = await sync_to_async(Show.objects.get)(imdb_url=item['show_url'])

            if 'cover_photo' in item and item['cover_photo']:
                # Download the image
                image_url = item['cover_photo']
                response = requests.get(image_url)
                if response.status_code == 200:
                    # Get a name for the file from the URL
                    filename = os.path.basename(urlparse(image_url).path)
                    # Define the path where you want to save the image
                    save_path = os.path.join(f"../photos/shows/{show.name}/episodes/S{item['season']}", filename)
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    
                    # Save the image to the local filesystem
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Replace the URL with the local path
                    item['cover_photo'] = save_path[2:]

                else:
                    raise DropItem(f"Failed to download image {image_url}")

            episode_item = Episode(
                name = item['name'],
                imdb_url = item['episode_url'],
                description = item['description'],
                show = show,
                season = item['season'],
                duration = item['duration'],
                imdb_rate = item['imdb_rate'],
                episode_number = item['episode'],
                release_date = item['release_date'],
                is_released = item['is_released'],
                cover_photo = item['cover_photo']
            )

            await sync_to_async(episode_item.save)()

        except Exception as e:
            print(f'error: {str(e)}')
        
        return item