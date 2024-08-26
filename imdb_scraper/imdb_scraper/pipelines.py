# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import os
import scrapy
from scrapy.pipelines.images import ImagesPipeline
from urllib.parse import urlparse
from django.core.files.base import ContentFile
from media.models import Actor

class ImdbScraperPipeline:
    def process_item(self, item, spider):
        return item


class ActorImagePipeline(ImagesPipeline):
    def file_path(self, request, response=None, info=None, *, item=None):
        actor_name = item['name'].replace(' ', '_')
        return f'actors/photos/{actor_name}.jpg'

    def get_media_requests(self, item, info):
        if item.get('profile_photo'):
            yield scrapy.Request(item['profile_photo'])

    def item_completed(self, results, item, info):
        if results[0][0]:  # Successful download
            item['profile_photo'] = results[0][1]['path']
        return item
