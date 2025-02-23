import scrapy
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.remote_connection import LOGGER as selenium_logger
from webdriver_manager.chrome import ChromeDriverManager
from scrapy.selector import Selector


# selenium_logger.setLevel(logging.ERROR)


class ActorSpider(scrapy.Spider):
    name = 'actor_spider'
    allowed_domains = ['imdb.com']

    # Override global ITEM_PIPELINES with spider-specific pipelines
    custom_settings = {
        'ITEM_PIPELINES': {
            'imdb_scraper.pipelines.ActorPipeline': 300,
        }
    }

    def __init__(self, *args, **kwargs):
        super(ActorSpider, self).__init__(*args, **kwargs)
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36")

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    def start_requests(self):
        start_url = 'https://www.imdb.com/search/name/?gender=male,female'
        yield scrapy.Request(url=start_url, callback=self.parse_page_with_selenium)

    def parse_page_with_selenium(self, response):
        self.driver.get(response.url)

        try:
            # Ensure page is fully loaded
            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button.ipc-see-more__button"))
            )
            while True:
                more_button = self.driver.find_element(By.CSS_SELECTOR, "button.ipc-see-more__button")
                if more_button:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", more_button)
                    self.driver.execute_script("arguments[0].click();", more_button)
                    WebDriverWait(self.driver, 30).until(
                        lambda d: d.find_element(By.CSS_SELECTOR, "button.ipc-see-more__button").get_attribute("aria-disabled") == "false"
                    )
                    selenium_response = Selector(text=self.driver.page_source)
                    actors = selenium_response.css('a.ipc-title-link-wrapper::attr(href)').getall()
                    
                    for actor in actors:
                        bio_link = 'https://www.imdb.com' + actor.split('?')[0] + 'bio/?ref_=nm_ov_bio_sm'
                        yield scrapy.Request(url=bio_link, callback=self.parse_actor)

                    # Remove processed elements from the page to reduce memory usage
                    self.driver.execute_script("""
                                               var items = document.querySelectorAll(
                                               'li.ipc-metadata-list-summary-item'
                                               ).forEach(e => {e.parentNode.removeChild(e); e = null});
                                               if ('caches' in window) {
                                                    caches.keys().then(function(names) {
                                                        for (let name of names) caches.delete(name);
                                                    });
                                                }""")

                else:
                    break

        except Exception as e:
            self.logger.error(f'Error occurred: {str(e)}')
        finally:
            print("Successfully crawled actors!")
            self.driver.quit()


    async def parse_actor(self, response):
        # Extract actor details
        name = response.css('h2.sc-5f0a904b-9::text').get()
        bio = ''.join(response.css('div.ipc-html-content-inner-div::text').getall()).strip().replace('"', '')
        birth_info_div = response.css('div.ipc-html-content-inner-div')
        birth_date = birth_info_div.css('a::text').getall()[0] + ', ' + birth_info_div.css('a::text').getall()[1]
        birth_city = birth_info_div.css('a::text').getall()[2]
        profile_photo_url = response.css('img.ipc-image::attr(src)').get()

        yield {
            'name': name,
            'bio': bio,
            'birth_date': birth_date,
            'birth_city': birth_city,
            'profile_photo': profile_photo_url,
        }