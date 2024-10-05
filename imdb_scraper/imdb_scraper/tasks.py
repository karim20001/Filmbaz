import logging
import os
import traceback
from scrapy.utils.project import get_project_settings
from multiprocessing import Process
from scrapy.crawler import CrawlerProcess
# from scrapy.crawler import CrawlerRunner
# from twisted.internet import reactor
# from twisted.internet.defer import inlineCallbacks
from celery import shared_task
from .spiders.update_episode import UpdateEpisodeSpider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_spider():
    os.environ['SCRAPY_SETTINGS_MODULE'] = 'imdb_scraper.imdb_scraper.settings'
    process = CrawlerProcess(get_project_settings())
    process.crawl(UpdateEpisodeSpider)
    process.start()  # This starts the Twisted reactor

@shared_task
def run_update_episode_spider():
    logger.info("Starting spider in a new process...")
    
    spider_process = Process(target=run_spider)
    spider_process.start()
    spider_process.join()  # Wait for the spider to complete
    
    return "Spider run complete"