import scrapy
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.remote_connection import LOGGER as selenium_logger
from webdriver_manager.chrome import ChromeDriverManager
from scrapy.selector import Selector
from asgiref.sync import sync_to_async
from scrapy.utils.defer import deferred_from_coro
import asyncio
from media.models import Episode

selenium_logger.setLevel(logging.ERROR)

class UpdateEpisodeSpider(scrapy.Spider):
    name = 'update_episode'
    allowed_domains = ['imdb.com']

    # Override global ITEM_PIPELINES with spider-specific pipelines
    custom_settings = {
        'ITEM_PIPELINES': {
            'imdb_scraper.imdb_scraper.pipelines.UpdateEpisodePipeline': 350,
        },
    }

    def __init__(self, *args, **kwargs):
        super(UpdateEpisodeSpider, self).__init__(*args, **kwargs)

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36")

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Fetch URLs before starting the crawl."""
        spider = super(UpdateEpisodeSpider, cls).from_crawler(crawler, *args, **kwargs)
        spider._fetch_urls()  # Fetch URLs before crawl starts
        return spider

    def _fetch_urls(self):
        """Synchronously fetch URLs from the database."""
        loop = asyncio.get_event_loop()
        # Fetch URLs from the database asynchronously but wait for them synchronously
        self.shows_url = loop.run_until_complete(self._get_shows())

    async def _get_shows(self):
        """Asynchronously fetch IMDb URLs from the database."""
        return await sync_to_async(list)(Episode.objects.all().values_list('imdb_url', flat=True)[:3])

    def start_requests(self):
        """Synchronously start requests based on the pre-fetched URLs."""
    #     headers = {
    #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
    # }
        for url in self.shows_url:
            full_url = url + 'episodes/'
            yield scrapy.Request(url=full_url, callback=self.parse_episode)
    
    async def parse_episode(self, response):
        try:
            self.driver.get(response.url)            
            page_source = self.driver.page_source
            scrapy_selector = Selector(text=page_source)

            imdb_rate = scrapy_selector.css('span.imUuxf::text').get()
            parent_released_date = scrapy_selector.css("a.ipc-metadata-list-item__label:contains('Release date')").xpath('parent::*')
            release_date = parent_released_date.css('a.ipc-metadata-list-item__list-content-item.ipc-metadata-list-item__list-content-item--link::text').get().split(' (')[0]

            yield ({
                'source': response.url[:-9],
                'imdb_rate': imdb_rate,
                'release_date': release_date,
            })

        except Exception as e:
            self.logger.error(f'Error in parse_episode: {str(e)}')

        finally:
            print("Finished processing episode page.")
    
    def close(self, reason):
        if self.driver:
            self.driver.quit()
