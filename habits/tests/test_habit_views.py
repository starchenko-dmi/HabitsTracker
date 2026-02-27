from datetime import time

import pytest
from rest_framework.test import APIClient

from habits.models import Habit
from users.models import User


@pytest.fixture
def user():
    return User.objects.create_user(email="test@example.com", username="testuser", password="password123")


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestHabitViewSet:
    """Тесты для представления привычек"""

    def test_list_habits(self, api_client, user):
        """Тест списка привычек пользователя"""
        Habit.objects.create(user=user, place="Дом", time=time(8, 0), action="Пробежка", duration=60, periodicity=1)
        response = api_client.get("/api/habits/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_create_habit(self, api_client, user):
        """Тест создания привычки"""
        data = {
            "place": "Парк",
            "time": "08:00",
            "action": "Прогулка",
            "duration": 120,
            "periodicity": 1,
            "reward": "Кофе",
        }
        response = api_client.post("/api/habits/", data, format="json")
        assert response.status_code == 201
        assert Habit.objects.count() == 1

    def test_public_habits(self, api_client, user):
        """Тест списка публичных привычек"""
        Habit.objects.create(
            user=user, place="Дом", time=time(8, 0), action="Пробежка", duration=60, periodicity=1, is_public=True
        )
        response = api_client.get("/api/habits/public/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
