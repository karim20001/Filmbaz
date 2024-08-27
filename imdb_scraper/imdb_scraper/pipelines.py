# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import os
import requests
from datetime import datetime
from urllib.parse import urlparse
from scrapy.exceptions import DropItem
from media.models import Actor
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
