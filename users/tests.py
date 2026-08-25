import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Тесты для модели пользователя"""

    def test_create_user_with_email(self):
        """Тест создания пользователя с email"""
        user = User.objects.create_user(email="test@example.com", username="testuser", password="password123")
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.has_telegram() is False

    def test_create_user_with_telegram(self):
        """Тест создания пользователя с Telegram"""
        user = User.objects.create_user(
            email="telegram@example.com",
            username="telegram_user",
            password="password123",
            telegram_chat_id=123456789,
            telegram_username="test_bot",
        )
        assert user.has_telegram() is True
        assert user.telegram_chat_id == 123456789
        assert user.telegram_username == "test_bot"

    def test_user_string_representation(self):
        """Тест строкового представления пользователя"""
        user = User.objects.create_user(email="test@example.com", username="testuser", password="password123")
        assert str(user) == "test@example.com"

    def test_create_superuser(self):
        """Тест создания суперпользователя"""
        admin = User.objects.create_superuser(email="admin@example.com", username="admin", password="admin123")
        assert admin.is_staff is True
        assert admin.is_superuser is True
