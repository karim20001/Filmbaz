import random
from faker import Faker
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from core.models import CustomUser
from media.models import Genre, Show, Episode, Movie, Actor, Cast, UserShow, UserEpisode, UserMovie, Follow, Comment
from django.contrib.auth import get_user_model

# User = get_user_model()
# fake = Faker()

def generate_valid_decimal(min_value, max_value, decimal_places):
    value = round(random.uniform(min_value, max_value), decimal_places)
    return Decimal(value).quantize(Decimal(10) ** -decimal_places, rounding=ROUND_HALF_UP)

class Command(BaseCommand):
    help = 'Generate fake data for the media app'

    def handle(self, *args, **kwargs):
        faker = Faker()
        User = get_user_model()

        # Create fake users
        users = [User.objects.create_user(
            username=faker.user_name(),
            password='password',
            email=faker.email()
        ) for _ in range(20)]

        # Create genres
        genres = [Genre.objects.create(name=faker.word()) for _ in range(20)]

        # Create shows
        shows = [Show.objects.create(
            id=uuid4(),
            name=faker.word(),
            season_count=random.randint(1, 10),
            imdb_rate=generate_valid_decimal(1, 5, 1),
            users_rate=generate_valid_decimal(1, 5, 1),
            release_year=random.randint(1980, 2023),
            duration=random.randint(20, 120),
            release_time=faker.time(),
            release_day=faker.day_of_week(),
            users_added_count=random.randint(0, 100),
            cover_photo=None
        ) for _ in range(20)]

        # Assign genres to shows
        for show in shows:
            show.genres.set(random.sample(genres, random.randint(1, 3)))

        # Create episodes
        episodes = [Episode.objects.create(
            id=uuid4(),
            show=random.choice(shows),
            season=random.randint(1, 10),
            imdb_rate=generate_valid_decimal(1, 5, 1),
            users_rate=generate_valid_decimal(1, 5, 1),
            episode_number=random.randint(1, 24),
            release_date=faker.date_between(start_date='-5y', end_date='today'),
            name=faker.word(),
            description=faker.text(),
            cover_photo=None
        ) for _ in range(20)]

        # Create movies
        movies = [Movie.objects.create(
            id=uuid4(),
            name=faker.word(),
            duration=random.randint(20, 180),
            imdb_rate=generate_valid_decimal(1, 5, 1),
            users_rate=generate_valid_decimal(1, 5, 1),
            description=faker.text(),
            release_date=faker.date_between(start_date='-5y', end_date='today'),
            cover_photo=None
        ) for _ in range(20)]

        # Assign genres to movies
        for movie in movies:
            movie.genres.set(random.sample(genres, random.randint(1, 3)))

        # Create actors
        actors = [Actor.objects.create(
            name=faker.name(),
            birth_date=faker.date_of_birth(minimum_age=20, maximum_age=80),
            birth_city=faker.city(),
            profile_photo=None
        ) for _ in range(20)]

        # Create casts
        all_content_objects = shows + episodes + movies
        content_types = [ContentType.objects.get_for_model(model) for model in [Show, Episode, Movie]]
        for _ in range(20):
            content_object = random.choice(all_content_objects)
            content_type = ContentType.objects.get_for_model(type(content_object))
            Cast.objects.create(
                content_type=content_type,
                object_id=content_object.id,
                content_object=content_object,
                actor=random.choice(actors),
                name=faker.word(),
                likes=random.randint(0, 100),
                photo=None
            )

        # Create user shows
        for _ in range(20):
            UserShow.objects.create(
                user=random.choice(users),
                show=random.choice(shows),
                status=random.choice([UserShow.WATCHING, UserShow.STOPPED, UserShow.WATCH_LATER]),
                is_favorite=random.choice([True, False]),
                user_rate=generate_valid_decimal(1, 5, 0)
            )

        # Create user episodes
        all_casts = Cast.objects.all()
        for _ in range(20):
            UserEpisode.objects.create(
                user=random.choice(users),
                episode=random.choice(episodes),
                user_rate=generate_valid_decimal(1, 5, 0),
                emoji=random.choice(['😀', '😢', '😡', '😍']),
                favorite_cast=random.choice(all_casts)
            )

        # Create user movies
        for _ in range(20):
            UserMovie.objects.create(
                user=random.choice(users),
                movie=random.choice(movies),
                watched=random.choice([True, False]),
                user_rate=generate_valid_decimal(1, 5, 0),
                emoji=random.choice(['😀', '😢', '😡', '😍']),
                is_favorite=random.choice([True, False]),
                favorite_cast=random.choice(all_casts)
            )

        # Create follows
        for _ in range(20):
            follower = random.choice(users)
            followee = random.choice([user for user in users if user != follower])
            Follow.objects.create(
                user=follower,
                follow=followee
            )

        # Create comments
        for _ in range(20):
            content_object = random.choice(all_content_objects)
            content_type = ContentType.objects.get_for_model(type(content_object))
            Comment.objects.create(
                user=random.choice(users),
                content_type=content_type,
                object_id=content_object.id,
                content_object=content_object,
                detail=faker.text(),
                likes=random.randint(0, 100),
                is_active=random.choice([True, False]),
                is_spoiler=random.choice([True, False]),
                parent=None
            )

        self.stdout.write(self.style.SUCCESS('Successfully generated fake data'))