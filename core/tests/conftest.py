import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

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
