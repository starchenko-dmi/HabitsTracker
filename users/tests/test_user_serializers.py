import pytest

from users.serializers import UserCreateSerializer


@pytest.mark.django_db
class TestUserSerializers:
    """Тесты для сериализаторов пользователей"""

    def test_create_user_serializer(self):
        """Тест создания пользователя через сериализатор"""
        data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "strongpassword123",
            "first_name": "Test",
            "last_name": "User",
        }
        serializer = UserCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        user = serializer.save()
        assert user.email == "test@example.com"
        assert user.check_password("strongpassword123")
