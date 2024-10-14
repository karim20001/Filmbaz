import pytest
import datetime
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from model_bakery import baker
from django.utils import timezone
from media.models import Show, UserShow, Episode, UserEpisode

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def create_user():
    def do_create_user(**kwargs):
        return User.objects.create_user(**kwargs)
    return do_create_user

@pytest.fixture
def authenticate(api_client):
    def do_authenticate(user=None):
        if not user:
            user = User.objects.create_user(username='user', password='password')
        api_client.force_authenticate(user=user)
        return api_client
    return do_authenticate

@pytest.fixture
def create_show():
    return baker.make(Show, _quantity=5)

@pytest.fixture
def create_episodes(create_show):
    """Create episodes for each show."""
    shows = create_show
    episodes = []
    
    for show in shows:
        # Create 5 released episodes for Season 1
        for episode_num in range(1, 6):
            episode = baker.make(Episode, 
                                 show=show, 
                                 season=1, 
                                 episode_number=episode_num, 
                                 is_released=True)
            episodes.append(episode)

        # Create 5 unreleased episodes for Season 2
        for episode_num in range(1, 6):
            episode = baker.make(Episode, 
                                 show=show, 
                                 season=2, 
                                 episode_number=episode_num,
                                 release_date='2025-02-07',
                                 is_released=False)
            episodes.append(episode)

    return episodes

@pytest.fixture
def genres():
    return baker.make('media.Genre', _quantity=3)

@pytest.fixture
def create_movies(genres):
    movies = baker.make('media.Movie', _quantity=5, is_released=True, release_date=datetime.date(2020, 5, 1), genres=genres)
    upcoming_date = timezone.now().date() + datetime.timedelta(days=10)
    upcoming_movies = baker.make('media.Movie', _quantity=3, is_released=False, release_date=upcoming_date, genres=genres)
    return movies + upcoming_movies