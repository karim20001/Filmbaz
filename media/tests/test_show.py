import pytest
from decimal import Decimal
from django.utils import timezone
from model_bakery import baker
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from media.models import UserEpisode, UserShow, Follow

User = get_user_model()

@pytest.mark.django_db
class TestSingleShow:
    @pytest.fixture
    def user_show(self, create_user, authenticate, create_show):
        user = create_user(username="johndoe", password="password123")
        authenticate(user)
        return baker.make(UserShow, user=user, show=create_show[0])

    @pytest.fixture
    def follow(self, user, user2):
        return baker.make(Follow, user=user, follow=user2)

    @pytest.fixture
    def user(self):
        return baker.make(User)
    
    @pytest.fixture
    def user2(self):
        return baker.make(User)
    
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