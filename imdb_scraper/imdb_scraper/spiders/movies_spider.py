import scrapy
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from scrapy.selector import Selector


class MovieSpider(scrapy.Spider):
    name = 'movie_spider'
    allowed_domains = ['imdb.com']

    def __init__(self, *args, **kwargs):
        super(MovieSpider, self).__init__(*args, **kwargs)
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    
    def start_requests(self):
        start_url = "https://www.imdb.com/search/title/?title_type=feature,tv_movie"
        # Return an iterable of a single Scrapy Request object that calls parse_page
        yield scrapy.Request(url=start_url, callback=self.parse_page_with_selenium)
    
    def parse_page_with_selenium(self, response):
        # Use Selenium to load the page content
        self.driver.get(response.url)

        try:
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
                    # Wait until the content after the button click is loaded
                    time.sleep(1)
                    # Parse the content after clicking the "See More" button
                    selenium_response = Selector(text=self.driver.page_source)
                    movies = selenium_response.css('a.ipc-title-link-wrapper::attr(href)').getall()
                    self.parse_page(movies)
                    break

                else:
                    break

        except Exception as e:
            self.logger.error(f'Error occurred: {str(e)}')
        finally:
            print("successfully actors crawled!")
            self.driver.quit()
    
    def parse_page(self, movies):
        print(movies)
        for movie in movies:
            movie_link = 'https://www.imdb.com' + movie.split('?')[0]
            # Yield a request for each actor's bio page
            yield scrapy.Request(url=movie_link, callback=self.parse_actor)

    async def parse_movie(self, response):
        