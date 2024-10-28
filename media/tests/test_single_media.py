import pytest
from decimal import Decimal
from django.utils import timezone
from model_bakery import baker
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from media.models import UserEpisode, UserMovie, UserShow, Follow, Cast, Actor, Movie

User = get_user_model()

@pytest.mark.django_db
class TestSingleShow:

    @pytest.fixture
    def user_show(self, create_user, authenticate, create_show):
        user = create_user(username="johndoe", password="password123")
        authenticate(user)
        return baker.make(UserShow, user=user, show=create_show[0])

    @pytest.fixture
    def user(self):
        return baker.make(User, username='w', password='password123')
    
    @pytest.fixture
    def user2(self):
        return baker.make(User, username='g', password='password123')
    
    def test_view_single_show(self, api_client, create_user, authenticate, create_show):
        user = create_user(username="johndoe", password="password123")
        authenticate(user)
        show = create_show[0]
        url = reverse('series-detail', kwargs={'pk': show.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == show.name
        assert response.data['imdb_rate'] == Decimal(show.imdb_rate)
    
    def test_add_show_to_user_list(self, api_client, create_user, authenticate, create_show):
        user = create_user(username="johndoe", password="password123")
        authenticate(user)
        show = create_show[0]
        url = reverse('series-add', kwargs={'pk': show.id})
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert UserShow.objects.filter(user=user, show=show).exists()
        show.refresh_from_db()
        assert show.users_added_count == 1
    
    def test_remove_show_from_user_list(self, api_client, create_user, authenticate, create_show):
        user = create_user(username="johndoe", password="password123")
        authenticate(user)
        show = create_show[0]
        url = reverse('series-add', kwargs={'pk': show.id})
        response = api_client.post(url)
        url = reverse('series-detail', kwargs={'pk': show.id})
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not UserShow.objects.filter(user=user, show=show).exists()
        show.refresh_from_db()
        assert show.users_added_count == 0
    
    def test_partial_update_show_status_returns_400(self, api_client, create_show, user_show): 
        url = reverse('series-detail', kwargs={'pk': create_show[0].id})
        data = {'status': 'WATCHING', 'user_rate': 4}
        response = api_client.patch(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        user_show.refresh_from_db()
        assert user_show.status == None
        assert user_show.user_rate == None
    
    def test_partial_update_show_status_returns_202(self, api_client, create_show, user_show): 
        url = reverse('series-detail', kwargs={'pk': create_show[0].id})
        user_show.status = 'WATCHING'
        user_show.save()
        data = {'status': 'متوقف شده', 'user_rate': 4}
        response = api_client.patch(url, data)

        assert response.status_code == status.HTTP_202_ACCEPTED
        user_show.refresh_from_db()
        assert user_show.status == 'متوقف شده'
        assert user_show.user_rate == 4
    
    def test_watchers_show(self, api_client, create_user, authenticate, create_episodes, user, user2):
        auth_user = create_user(username="johndoe", password="password123")
        authenticate(auth_user)

        show = create_episodes[0].show

        for episode in create_episodes[:3]:
            baker.make(UserEpisode, user=user, episode=episode)
        for episode in create_episodes[:3]:
            baker.make(UserEpisode, user=user2, episode=episode)
        
        baker.make(Follow, user=auth_user, follow=user)
        baker.make(Follow, user=auth_user, follow=user2)

        url = reverse('series-watchers', kwargs={'pk': show.id})
        response = api_client.get(url)
        print(response.data)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
        assert response.data['results'][0]['user']['username'] == user2.username


@pytest.mark.django_db
class TestSingleMovie:

    @pytest.fixture
    def user_movie(self, create_user, authenticate, create_movies):
        user = create_user(username="johndoe", password="password123")
        authenticate(user)
        return baker.make(UserMovie, user=user, movie=create_movies[0])

    @pytest.fixture
    def user(self):
        return baker.make(User, username='w', password='password123')
    
    @pytest.fixture
    def user2(self):
        return baker.make(User, username='g', password='password123')
    
    def test_view_single_movie(self, api_client, create_user, authenticate, create_movies):
        user = create_user(username="johndoe", password="password123")
        authenticate(user)
        movie = create_movies[0]
        url = reverse('movie-detail', kwargs={'pk': movie.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == movie.name
        assert response.data['imdb_rate'] == Decimal(movie.imdb_rate)
    
    def test_add_movie_to_user_list(self, api_client, create_user, authenticate, create_movies):
        user = create_user(username="johndoe", password="password123")
        authenticate(user)
        movie = create_movies[0]
        url = reverse('movie-add', kwargs={'pk': movie.id})
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert UserMovie.objects.filter(user=user, movie=movie).exists()
        movie.refresh_from_db()
        assert movie.users_added_count == 1
    
    def test_remove_movie_from_user_list(self, api_client, create_user, authenticate, create_movies):
        user = create_user(username="johndoe", password="password123")
        authenticate(user)
        movie = create_movies[0]
        url = reverse('movie-add', kwargs={'pk': movie.id})
        response = api_client.post(url)
        url = reverse('movie-detail', kwargs={'pk': movie.id})
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not UserMovie.objects.filter(user=user, movie=movie).exists()
        movie.refresh_from_db()
        assert movie.users_added_count == 0
    
    def test_partial_update_movie_status_returns_400(self, api_client, create_movies, user_movie): 
        url = reverse('movie-detail', kwargs={'pk': create_movies[0].id})
        data = {'emoji': 're', 'user_rate': 4}
        response = api_client.patch(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        user_movie.refresh_from_db()
        assert user_movie.emoji == None
        assert user_movie.user_rate == None
        assert response.data["message"] == "You must watch the movie before updating its details."
    
    def test_partial_update_movie_not_released(self, api_client, create_user, authenticate, create_movies):
        user = create_user(username="johndoe", password="password123")
        authenticate(user)
        movie = create_movies[6]
        user_movie = baker.make(UserMovie, movie=movie, user=user)
        
        url = reverse('movie-detail', kwargs={'pk': create_movies[6].id})
        data = {'emoji': 're', 'user_rate': 4}
        response = api_client.patch(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        user_movie.refresh_from_db()
        assert user_movie.emoji == None
        assert user_movie.user_rate == None
        assert response.data["message"] == "movie not released"
    
    def test_partial_update_movie_add_and_watched(self, api_client, create_user, authenticate, create_movies):
        user = create_user(username="johndoe", password="password123")
        authenticate(user)

        url = reverse('movie-detail', kwargs={'pk': create_movies[0].id})
        data = {'watched': True}
        
        response = api_client.patch(url, data=data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["message"] == "movie add and watched"
    
    def test_partial_update_movie_not_watched(self, api_client, create_user, authenticate, create_movies):
        user = create_user(username="johndoe", password="password123")
        authenticate(user)

        url = reverse('movie-detail', kwargs={'pk': create_movies[0].id})
        data = {'user_rate': 3}

        response = api_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["message"] == "movie not watched yet"
    
    def test_partial_update_unwatch_movie(self, api_client, create_user, authenticate, create_movies):
        user = create_user(username="johndoe", password="password123")
        authenticate(user)

        baker.make(UserMovie, user=user, movie=create_movies[0], watched=True)

        url = reverse('movie-detail', kwargs={'pk': create_movies[0].pk})
        data = {'watched': False}

        response = api_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Watched status updated and user movie data reset!"

    def test_partial_update_watch_movie(self, api_client, create_user, authenticate, create_movies):
        user = create_user(username="johndoe", password="password123")
        authenticate(user)

        baker.make(UserMovie, user=user, movie=create_movies[0])
        url = reverse('movie-detail', kwargs={'pk': create_movies[0].pk})
        data = {'watched': True}

        response = api_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Watched status updated!"
    
    def test_partial_update_favorite_cast_not_related(self, api_client, create_user, authenticate, create_movies, create_actors):
        user = create_user(username="johndoe", password="password123")
        authenticate(user)

        baker.make(UserMovie, user=user, movie=create_movies[0], watched=True)
        cast = baker.make(Cast, actor=create_actors[0], object_id=create_movies[0].id, content_type=ContentType.objects.get_for_model(Movie))
        cast2 = baker.make(Cast, actor=create_actors[0], object_id=create_movies[3].id, content_type=ContentType.objects.get_for_model(Movie))

        url = reverse('movie-detail', kwargs={'pk': create_movies[0].pk})
        data = {'favorite_cast': cast2.id}
        response = api_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["message"] == "cast is not related"


    def test_partial_update_movie_status_returns_202(self, api_client, create_user, authenticate, create_movies, create_actors): 
        user = create_user(username="johndoe", password="password123")
        authenticate(user)

        user_movie = baker.make(UserMovie, user=user, movie=create_movies[0], watched=True)
        cast = baker.make(Cast, actor=create_actors[0], object_id=create_movies[0].id, content_type=ContentType.objects.get_for_model(Movie))
        cast2 = baker.make(Cast, actor=create_actors[0], object_id=create_movies[3].id, content_type=ContentType.objects.get_for_model(Movie))

        url = reverse('movie-detail', kwargs={'pk': create_movies[0].id})
        data = {'user_rate': 4, 'favorite_cast': cast.id}

        response = api_client.patch(url, data, format='json')
        print(response.data["message"])

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data["message"] == "update success"
        user_movie.refresh_from_db()
        assert user_movie.user_rate == 4
    
    def test_watchers_movie(self, api_client, create_user, authenticate, create_movies, user, user2):
        auth_user = create_user(username="johndoe", password="password123")
        authenticate(auth_user)

        movie = create_movies[0]

        for movie in create_movies[:3]:
            baker.make(UserMovie, user=user, movie=movie, watched=True, watched_date=timezone.datetime.now())
        for movie in create_movies[:3]:
            baker.make(UserMovie, user=user2, movie=movie, watched=True, watched_date=timezone.datetime.now())
        
        baker.make(Follow, user=auth_user, follow=user)
        baker.make(Follow, user=auth_user, follow=user2)

        url = reverse('movie-watchers', kwargs={'pk': movie.id})
        response = api_client.get(url)
        watchers = response.data['results']['watchers']

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
        assert watchers[0]['user']['username'] == user2.username


@pytest.mark.django_db
class TestSingleEpisode:
    @pytest.fixture
    def user_episode(self, create_user, authenticate, create_episodes):
        user = create_user(username="johndoe", password="password123")
        authenticate(user)
        return baker.make(UserEpisode, user=user, episode=create_episodes[0])

    @pytest.fixture
    def user(self, authenticate):
        user = baker.make(User, username='w', password='password123')
        authenticate(user)
        return user
    
    @pytest.fixture
    def user2(self):
        return baker.make(User, username='g', password='password123')
    
    def test_add_episode_to_watched_list(self, api_client, user, create_episodes):
        url = reverse('episodes-add', kwargs={'series_pk': create_episodes[1].show.id, 'pk': create_episodes[1].id})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_201_CREATED
        assert UserEpisode.objects.filter(user=user, episode=create_episodes[1]).exists()
        assert response.data['detail'] == 'Episode watched'

    def test_partial_update_favorite_cast(self, api_client, user_episode, create_actors):
        cast = baker.make(Cast, name='Cast Member', content_type_id=ContentType.objects.get(model='episode').id, object_id=user_episode.episode.id, actor=create_actors[0])
        data = {'favorite_cast': cast.id}
        url = reverse('episodes-detail', kwargs={'series_pk': user_episode.episode.show.id, 'pk': user_episode.episode.id})
        response = api_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        updated_user_episode = UserEpisode.objects.get(id=user_episode.id)
        assert updated_user_episode.favorite_cast.id == cast.id

    def test_destroy_user_episode(self, api_client, user_episode):
        url = reverse('episodes-detail', kwargs={'series_pk': user_episode.episode.show.id, 'pk': user_episode.episode.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not UserEpisode.objects.filter(id=user_episode.id).exists()
    
    def test_list_episodes_unauthenticated(self, api_client, create_show):
        url = reverse('episodes-list', kwargs={'series_pk': create_show[0].id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_add_episode_already_watched(self, api_client, user_episode):
        url = reverse('episodes-add', kwargs={'series_pk': user_episode.episode.show.id, 'pk': user_episode.episode.id})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['detail'] == 'episode already watched'

    def test_partial_update_no_permission(self, api_client, user, create_user, create_episodes):
        another_user = create_user(username='anotheruser', password='password123')
        another_user_episode = UserEpisode.objects.create(user=another_user, episode=create_episodes[1])
        url = reverse('episodes-detail', kwargs={'series_pk': create_episodes[1].show.id, 'pk': another_user_episode.episode.id})
        data = {'user_rate': 5}
        response = api_client.patch(url, data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_user_rate(self, api_client, user, user_episode):
        data = {'user_rate': 4}
        url = reverse('episodes-detail', kwargs={'series_pk': user_episode.episode.show.id, 'pk': user_episode.episode.id})
        response = api_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        user_episode.refresh_from_db()
        assert user_episode.user_rate == 4

    def test_update_user_rate_not_watched(self, api_client, user, create_episodes):
        episode_not_watched = create_episodes[1]
        url = reverse('episodes-detail', kwargs={'series_pk': episode_not_watched.show.id, 'pk': episode_not_watched.id})
        data = {'user_rate': 3}
        response = api_client.patch(url, data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        # assert response.data['detail'] == 'You must watch the episode before updating its details.'

    def test_favorite_cast_not_related(self, api_client, user_episode, create_episodes):
        unrelated_cast = baker.make(Cast, name='Unrelated Cast', content_type_id=ContentType.objects.get(model='episode').id, object_id=create_episodes[1].id)
        data = {'favorite_cast': unrelated_cast.id}
        url = reverse('episodes-detail', kwargs={'series_pk': user_episode.episode.show.id, 'pk': user_episode.episode.id})
        response = api_client.patch(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['detail'] == 'cast is not related'

    def test_update_user_rate_and_favorite_cast(self, api_client, user_episode):
        cast = baker.make(Cast, name='Related Cast', content_type_id=ContentType.objects.get(model='episode').id, object_id=user_episode.episode.id)
        data = {'user_rate': 5, 'favorite_cast': cast.id}
        url = reverse('episodes-detail', kwargs={'series_pk': user_episode.episode.show.id, 'pk': user_episode.episode.id})
        response = api_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        user_episode.refresh_from_db()
        assert user_episode.user_rate == 5
        assert user_episode.favorite_cast.id == cast.id
        assert response.data['detail'] == 'update success'

    def test_invalid_episode_id(self, api_client, user, create_episodes):
        url = reverse('episodes-detail', kwargs={'series_pk': create_episodes[1].show.id, 'pk': 'invalid_id'})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

