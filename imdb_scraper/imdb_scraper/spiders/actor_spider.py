import scrapy
from asgiref.sync import sync_to_async
from scrapy_djangoitem import DjangoItem
from media.models import Actor


class ActorItem(DjangoItem):
    django_model = Actor


class ActorSpider(scrapy.Spider):
    name = 'actor_spider'
    start_urls = ['https://www.imdb.com/search/name/?gender=male,female']

    def parse(self, response):
        actors = response.css('a.ipc-title-link-wrapper::attr(href)').getall()
        print(actors)
        
        # Loop through the list of actors on the page
        # for actor in actors:
        #     # actor_name = actor.css('.lister-item-header a::text').get()
        #     # actor_url = actor.css('.ipc-title__text h3::attr(href)').get()
        #     print(actor)

        #     # Go to the actor's details page
        #     yield response.follow(actor, self.parse_actor)

        # Follow the pagination to get the next page of actors
         # Check if there is a "50 more" button and follow it
        more_button = response.css('span.ipc-btn__text:contains("50 more")')
        if more_button:
            next_page = more_button.xpath('./ancestor::a/@href').get()
            if next_page:
                yield response.follow(next_page, self.parse)

    def parse_actor(self, response):
        # Extract actor details
        name = response.css('span.itemprop::text').get()
        bio = ' '.join(response.css('div.soda p::text').getall()).strip()
        birth_date = response.css('time::attr(datetime)').get()
        birth_city = response.css('div.birthplace a::text').get()
        profile_photo_url = response.css('.poster img::attr(src)').get()
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
        actor_item.save()

        yield actor_item