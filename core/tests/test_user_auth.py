import pytest
from rest_framework import status
from django.urls import reverse
from model_bakery import baker
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestUserSignup:
    def test_signup_with_valid_data_returns_201(self, api_client):
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "johndoe@example.com",
            "username": "johndoe",
            "password1": "strongpassword123",
            "password2": "strongpassword123"
        }

        response = api_client.post(reverse('sign-up'), data)

        assert response.status_code == status.HTTP_201_CREATED

    def test_signup_with_mismatched_passwords_returns_400(self, api_client):
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "johndoe@example.com",
            "username": "johndoe",
            "password1": "password123",
            "password2": "password321"
        }

        response = api_client.post(reverse('sign-up'), data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Passwords do not match' in str(response.data)

@pytest.mark.django_db
class TestUserLogin:
    def test_login_with_valid_credentials_returns_token(self, create_user, api_client):
        user = create_user(username="johndoe", password="password123")

        data = {
            "username": "johndoe",
            "password": "password123"
        }

        response = api_client.post(reverse('token_obtain_pair'), data)

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_login_with_invalid_credentials_returns_400(self, api_client):
        data = {
            "username": "invaliduser",
            "password": "wrongpassword"
        }

        response = api_client.post(reverse('token_obtain_pair'), data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'No active account found with the given credentials' in str(response.data)
