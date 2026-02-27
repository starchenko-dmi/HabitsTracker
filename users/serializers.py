from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer
from rest_framework import serializers

from .models import User


class UserCreateSerializer(BaseUserCreateSerializer):
    """Сериализатор для создания пользователя"""

    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ("id", "email", "username", "password", "first_name", "last_name")
        extra_kwargs = {"password": {"write_only": True}}


class UserSerializer(BaseUserSerializer):
    """Сериализатор для отображения пользователя"""

    has_telegram = serializers.BooleanField(read_only=True)

    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "telegram_chat_id",
            "telegram_username",
            "has_telegram",
            "date_joined",
            "last_login",
        )
        read_only_fields = ("id", "date_joined", "last_login", "has_telegram")
