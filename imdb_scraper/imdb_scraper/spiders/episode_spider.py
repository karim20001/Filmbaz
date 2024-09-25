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
from media.models import Show

# selenium_logger.setLevel(logging.ERROR)

class EpisodeSpider(scrapy.Spider):
    name = 'episode_spider'
    allowed_domains = ['imdb.com']

    def __init__(self, *args, **kwargs):
        super(EpisodeSpider, self).__init__(*args, **kwargs)

        chrome_options = Options()
        # chrome_options.add_argument("--headless")
        # chrome_options.add_argument("--disable-gpu")
        # chrome_options.add_argument("--window-size=1920,1080")
        # chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36")

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Fetch URLs before starting the crawl."""
        spider = super(EpisodeSpider, cls).from_crawler(crawler, *args, **kwargs)
        spider._fetch_urls()  # Fetch URLs before crawl starts
        return spider

    def _fetch_urls(self):
        """Synchronously fetch URLs from the database."""
        loop = asyncio.get_event_loop()
        # Fetch URLs from the database asynchronously but wait for them synchronously
        self.shows_url = loop.run_until_complete(self._get_shows())

    async def _get_shows(self):
        """Asynchronously fetch IMDb URLs from the database."""
        return await sync_to_async(list)(Show.objects.all().values_list('imdb_url', flat=True)[:3])

    def start_requests(self):
        """Synchronously start requests based on the pre-fetched URLs."""
        for url in self.shows_url:
            full_url = url + 'episodes/'
            yield scrapy.Request(url=full_url, callback=self.parse_page_with_selenium)

    async def parse_page_with_selenium(self, response):
        """Process the page and its seasons using Selenium."""
        self.driver.get(response.url)

        episodes = []
        all_seasons_processed = False

        while not all_seasons_processed:
            page_source = self.driver.page_source
            scrapy_selector = Selector(text=page_source)
            
            # Extract episode URLs from the current page
            episodes_url = scrapy_selector.css('a.ipc-title-link-wrapper::attr(href)').getall()

            for item in episodes_url:
                if 'title' in item:  # Ensure it's an episode URL
                    episodes.append(item)

            try:
                next_season_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button#next-season-btn"))
                )
                
                if next_season_button:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", next_season_button)
                    self.driver.execute_script("arguments[0].click();", next_season_button)

                    # Wait for the new season content to load
                    WebDriverWait(self.driver, 10).until(
                        EC.staleness_of(self.driver.find_element(By.CSS_SELECTOR, "a.ipc-title-link-wrapper"))
                    )
                else:
                    all_seasons_processed = True

            except Exception:
                all_seasons_processed = True

        # Now that all seasons and episodes have been collected, yield each episode
        for episode_url in episodes:
            full_episode_url = 'https://www.imdb.com' + episode_url
            # self.driver.get(full_episode_url)
            yield deferred_from_coro(self.parse_episode_with_selenium(full_episode_url, response.url))

    async def parse_episode_with_selenium(self, episode_url, show_url):
        """Parse individual episode page using Selenium."""
        try:
            self.driver.get(episode_url)
            # Scroll down to storyline to load data
            storyline_section = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Storyline')]")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", storyline_section)
            # Wait data load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Genres')]"))
           )
            page_source = self.driver.page_source
            scrapy_selector = Selector(text=page_source)

            name = scrapy_selector.css('span.hero__primary-text::text').get()
            description = self.driver.find_element(By.CSS_SELECTOR, 'div.ipc-overflowText--children').text     
            season_episode = scrapy_selector.css('div.fYpskP::text').getall()
            imdb_rate = scrapy_selector.css('span.iQZtLP::text').get()
            duration = scrapy_selector.css('div.ipc-metadata-list-item__content-container::text').getall()
            parent_released_date = scrapy_selector.css("a.ipc-metadata-list-item__label:contains('Release date')").xpath('parent::*')
            release_date = parent_released_date.css('a.ipc-metadata-list-item__list-content-item.ipc-metadata-list-item__list-content-item--link::text').get().split(' (')[0]
            cover_photo = scrapy_selector.css('img.ipc-image::attr(src)').get()

            return ({
                'episode_url': episode_url,
                'show_url': show_url,
                'name': name,
                'description': description,
                'season_episode': season_episode,
                'imdb_rate': imdb_rate,
                'duration': duration,
                'release_date': release_date,
                'cover_photo': cover_photo
            })

        except Exception as e:
            self.logger.error(f'Error in parse_episode: {str(e)}')

        finally:
            print("Finished processing episode page.")
    
    def close(self, reason):
        if self.driver:
            self.driver.quit()