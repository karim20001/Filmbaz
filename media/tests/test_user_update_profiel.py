import pytest
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserProfileUpdate:
    def test_update_profile_with_valid_data(self, authenticate, api_client, create_user):
        user = create_user(username="johndoe", password="password123")
        authenticate(user=user)
        
        data = {
            "first_name": "John",
            "last_name": "UpdatedDoe",
            "username": user.username,
            "password": "password123",  # Old password
            "password1": "newpassword123",  # New password
            "password2": "newpassword123"
        }

        url = reverse('profile-update-profile')

        response = api_client.patch(url, data)

        assert response.status_code == status.HTTP_202_ACCEPTED

    def test_update_profile_with_invalid_old_password_returns_400(self, authenticate, api_client, create_user):
        # Create and authenticate the user
        user = create_user(username="johndoe", password="password123")
        authenticate(user=user)

        data = {
            "first_name": "John",
            "last_name": "UpdatedDoe",
            "username": user.username,
            "password": "wrongpassword",  # Incorrect old password
            "password1": "newpassword123",
            "password2": "newpassword123"
        }

        url = reverse('profile-update-profile')
        response = api_client.patch(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        assert 'old password not correct' in str(response.data)
