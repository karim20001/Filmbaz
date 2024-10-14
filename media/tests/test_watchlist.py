import pytest
import datetime
from rest_framework import status
from django.urls import reverse
from model_bakery import baker
from django.contrib.auth import get_user_model
from django.utils import timezone

from media.models import Show, Episode, UserMovie, UserShow, UserEpisode

User = get_user_model()

@pytest.mark.django_db
class TestShowWatchList:
    def test_if_user_is_anonymous_returns_401(self, api_client):
        response = api_client.get(reverse('user-shows-watchlist'))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_user_watchlist_next_episode(self, api_client, authenticate, create_user, create_show, create_episodes):
        user = create_user(username="johndoe", password="password123")
        authenticate(user=user)

        show = create_episodes[0].show
        episodes = create_episodes

        watched_history = []
        for episode in episodes[:4]:
            user_episode = baker.make(UserEpisode, user=user, episode=episode)
            watched_history.insert(0, user_episode)

        episode = Episode.objects.filter(show=show, season=1, episode_number=4).first()
        four_years_ago = datetime.datetime.now() - datetime.timedelta(days=365*4)
        user_episode = baker.make(UserEpisode, user=user, episode=episodes[10], watch_date=four_years_ago)
        watched_history.append(user_episode)

        response = api_client.get(reverse('user-shows-watchlist'))

        assert response.status_code == status.HTTP_200_OK

        watched_history_data = response.data['watched_history']

        assert len(watched_history_data) == len(watched_history)
        for i in range(len(watched_history)):
            assert watched_history_data[i]['episode_number'] == watched_history[i].episode.episode_number
            assert watched_history_data[i]['season'] == watched_history[i].episode.season
            assert watched_history_data[i]['show']['id'] == str(watched_history[i].episode.show.id)

        next_episdoes = response.data['watch_next']
        assert next_episdoes[0]['episode_number'] == episode.episode_number + 1

        # Test havent_watched_for_a_while
        last_time_episode = Episode.objects.filter(show=episodes[10].show, season=1, episode_number=2).first()

        watched_history_data = response.data['havent_watched_for_a_while']
        print(response.data['watch_next'])

        assert watched_history_data[0]['episode_number'] == last_time_episode.episode_number
        assert watched_history_data[0]['season'] == last_time_episode.season
        assert watched_history_data[0]['show']['id'] == str(last_time_episode.show.id)

    def test_upcoming_episodes(self, api_client, authenticate, create_user, create_episodes):
        user = create_user(username="johndoe", password="password123")
        authenticate(user=user)

        episodes = create_episodes
        for episode in episodes[:5]:
            baker.make(UserEpisode, user=user, episode=episode)

        response = api_client.get(reverse('user-shows-upcoming'))
        upcoming_episodes_data = response.data

        assert upcoming_episodes_data[0]['episode_number'] == episodes[5].episode_number
        assert upcoming_episodes_data[0]['season'] == episodes[5].season
        assert upcoming_episodes_data[0]['show']['id'] == str(episodes[5].show.id)

@pytest.mark.django_db
class TestMovieWatchList:

    def test_user_movie_watchlist(self, api_client, create_user, authenticate, create_movies):
        user = create_user(username="johndoe", password="password123")
        authenticate(user=user)
        for movie in create_movies:
            baker.make(UserMovie, user=user, movie=movie, watched=False)

        response = api_client.get(reverse('user-movies-watchlist'))
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 5
        for movie_data in response.data:
            assert 'name' in movie_data
            assert 'genres' in movie_data
            assert 'duration' in movie_data
            assert 'time_to_release' in movie_data
    
    def test_user_movie_upcoming(self, api_client, create_user, authenticate, create_movies):
        user = create_user(username="johndoe", password="password123")
        authenticate(user=user)
        for movie in create_movies:
            baker.make(UserMovie, user=user, movie=movie, watched=False)
        
        response = api_client.get(reverse('user-movies-upcoming'))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3
        for movie_data in response.data:
            assert 'name' in movie_data
            assert 'genres' in movie_data
            assert 'duration' in movie_data
            assert 'time_to_release' in movie_data