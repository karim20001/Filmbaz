import scrapy
from datetime import datetime
from asgiref.sync import sync_to_async
from scrapy_djangoitem import DjangoItem
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from scrapy.selector import Selector
from media.models import Actor


class ActorItem(DjangoItem):
    django_model = Actor


class ActorSpider(scrapy.Spider):
    name = 'actor_spider'
    allowed_domains = ['imdb.com']

    def __init__(self, *args, **kwargs):
        super(ActorSpider, self).__init__(*args, **kwargs)
        # chrome_options = Options()
        # chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))  # Specify the path to chromedriver

    def start_requests(self):
        start_url = 'https://www.imdb.com/search/name/?gender=male,female'
        # Return an iterable of a single Scrapy Request object that calls parse_page
        yield scrapy.Request(url=start_url, callback=self.parse_page_with_selenium)

    def parse_page_with_selenium(self, response):
        # Use Selenium to load the page content
        self.driver.get(response.url)

        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button.ipc-btn.ipc-btn--single-padding.ipc-btn--center-align-content.ipc-btn--default-height.ipc-btn--core-base.ipc-btn--theme-base.ipc-btn--on-accent2.ipc-btn--rounded.ipc-text-button.ipc-see-more__button"))
            )

            # Parse the page with Scrapy's Selector
            selenium_response = Selector(text=self.driver.page_source)
            actors = selenium_response.css('a.ipc-title-link-wrapper::attr(href)').getall()[:2]
            print(actors)

            for actor in actors:
                bio_link = 'https://www.imdb.com' + actor.split('?')[0] + 'bio/?ref_=nm_ov_bio_sm'
                print(bio_link)
                # Yield a request for each actor's bio page
                yield scrapy.Request(url=bio_link, callback=self.parse_actor)

        
            # more_button = self.driver.find_element(By.CSS_SELECTOR, "button.ipc-btn.ipc-btn--single-padding.ipc-btn--center-align-content.ipc-btn--default-height.ipc-btn--core-base.ipc-btn--theme-base.ipc-btn--on-accent2.ipc-btn--rounded.ipc-text-button.ipc-see-more__button")
            # if more_button:
            #     more_button.click()
            #     WebDriverWait(self.driver, 10).until(
            #         EC.presence_of_element_located((By.CSS_SELECTOR, ".lister-item"))
            #     )
            #     # Parse the newly loaded content
            #     self.parse_page()

        except Exception as e:
            self.logger.error(f'Error occurred: {str(e)}')
        finally:
            self.driver.quit()
    def parse_actor(self, response):
        # Extract actor details
        name = response.css('h2.sc-5f0a904b-9::text').get()
        bio = ' '.join(response.css('div.ipc-html-content-inner-div::text').getall()).strip()
        birth_info_div = response.css('div.ipc-html-content-inner-div')
        birth_date = birth_info_div.css('a::text').getall()[0] + birth_info_div.css('a::text').getall()[1]
        birth_date = datetime.strptime(birth_date, '%B %d, %Y').date()
        birth_city = birth_info_div.css('a::text').getall()[2]
        profile_photo_url = response.css('img.ipc-image::attr(src)').get()
        print(f'\n\n {name}\n {bio} \n {birth_date} \n {birth_city}')

        # Save actor data to Django model
        actor_item = ActorItem()
        actor_item['name'] = name
        actor_item['bio'] = bio
        actor_item['birth_date'] = birth_date
        actor_item['birth_city'] = birth_city

        # If profile photo exists, download it
        if profile_photo_url:
            actor_item['profile_photo'] = profile_photo_url  # Implement downloading and saving images

        # Save to Django database
        sync_to_async(actor_item.save)()
        print('success')

        yield actor_item