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


selenium_logger.setLevel(logging.ERROR)


class MovieSpider(scrapy.Spider):
    name = 'movie_spider'
    allowed_domains = ['imdb.com']

    # Override global ITEM_PIPELINES with spider-specific pipelines
    custom_settings = {
        'ITEM_PIPELINES': {
            'imdb_scraper.pipelines.MoviePipeline': 200,
        }
    }

    def __init__(self, *args, **kwargs):
        super(MovieSpider, self).__init__(*args, **kwargs)

        chrome_options = Options()
        # chrome_options.add_argument("--headless")
        # chrome_options.add_argument("--disable-gpu")
        # chrome_options.add_argument("--window-size=1920,1080")
        # chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36")

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    def start_requests(self):
        start_url = "https://www.imdb.com/search/title/?title_type=feature,tv_movie"
        # Return an iterable of a single Scrapy Request object that calls parse_page
        yield scrapy.Request(url=start_url, callback=self.parse_page_with_selenium)
    
    def parse_page_with_selenium(self, response):
        # Use Selenium to load the page content
        self.driver.get(response.url)

        try:
            # Ensure page is fully loaded
            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

            # Wait until the "See More" button is present
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button.ipc-see-more__button"))
            )
            while True:
                # Use Selenium to click the "See More" button without refreshing the page
                more_button = self.driver.find_element(By.CSS_SELECTOR, "button.ipc-see-more__button")

                if more_button:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", more_button)
                    self.driver.execute_script("arguments[0].click();", more_button)
                    WebDriverWait(self.driver, 30).until(
                        lambda d: d.find_element(By.CSS_SELECTOR, "button.ipc-see-more__button").get_attribute("aria-disabled") == "false"
                    )
                    selenium_response = Selector(text=self.driver.page_source)
                    movies = selenium_response.css('a.ipc-title-link-wrapper::attr(href)').getall()
                    
                    for movie in movies:
                        movie_link = 'https://www.imdb.com' + movie.split('?')[0]
                        yield scrapy.Request(url=movie_link, callback=self.parse_movie)

                    self.driver.execute_script("""
                                               var items = document.querySelectorAll(
                                               'li.ipc-metadata-list-summary-item'
                                               ).forEach(e => {e.parentNode.removeChild(e); e = null});
                                               if ('caches' in window) {
                                                    caches.keys().then(function(names) {
                                                        for (let name of names) caches.delete(name);
                                                    });
                                                }""")
                    break

                else:
                    break

        except Exception as e:
            self.logger.error(f'Error occurred: {str(e)}')
        finally:
            print("successfully movies crawled!")
    

    async def parse_movie(self, response):
        try:
            self.driver.get(response.url)
            # Scroll down to storyline to load data
            storyline_section = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Storyline')]")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", storyline_section)
            # Wait data load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Genres')]"))
           )

            name = response.css("span.hero__primary-text::text").get()
            duration = response.css("div.ipc-metadata-list-item__content-container::text").getall()
            imdb_rate = response.css('span.sc-eb51e184-1.ljxVSS::text').get()
            description = response.css('div.ipc-html-content-inner-div::text').get()
            parent_released_date = response.css("a.ipc-metadata-list-item__label:contains('Release date')").xpath('parent::*')
            release_date = parent_released_date.css('a.ipc-metadata-list-item__list-content-item.ipc-metadata-list-item__list-content-item--link::text').get().split(' (')[0]
            is_released = response.css('div.sc-5766672e-1.kDBNLe:contains("Genres")').get()
            span_element = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Genres')]")
            parent_genres = span_element.find_element(By.XPATH, '..')
            genre_elements = parent_genres.find_elements(By.CSS_SELECTOR, 'a.ipc-metadata-list-item__list-content-item--link')
            genres = [element.text for element in genre_elements]
            cover_photo = response.css('img.ipc-image::attr(src)').get()
            print(f'name: {name}  duration:{duration} rate:{imdb_rate}  description:{description}  release_date:{release_date}  is_released:{is_released} genres:{genres}  cover_photo:{cover_photo}')

            yield {
                'name': name,
                'duration': duration,
                'imdb_rate': imdb_rate,
                'description': description,
                'release_date': release_date,
                'is_released': is_released,
                'genres': genres,
                'cover_photo': cover_photo
            }

        except Exception as e:
            self.logger.error(f'Error in parse_movie: {str(e)}')

        finally:
            print("Finished processing movie page.")
    
    def close(self, reason):
        if self.driver:
            self.driver.quit()
