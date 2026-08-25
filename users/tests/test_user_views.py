import pytest
from rest_framework.test import APIClient

from users.models import User


@pytest.mark.django_db
class TestUserViewSet:
    """Тесты для представления пользователей"""

    def test_user_can_see_own_profile(self):
        """Пользователь видит свой профиль"""
        client = APIClient()
        user = User.objects.create_user(email="test@example.com", username="testuser", password="password123")
        client.force_authenticate(user=user)

        response = client.get(f"/api/users/{user.id}/")
        assert response.status_code == 200
        assert response.data["email"] == "test@example.com"

    def test_user_cannot_see_other_profile(self):
        """Пользователь не видит чужой профиль"""
        client = APIClient()
        user1 = User.objects.create_user(email="user1@example.com", username="user1", password="password123")
        user2 = User.objects.create_user(email="user2@example.com", username="user2", password="password123")
        client.force_authenticate(user=user1)

        response = client.get(f"/api/users/{user2.id}/")
        assert response.status_code == 404  # или 403 в зависимости от настроек
