from unittest.mock import AsyncMock, MagicMock

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

TEST_CHAT_ID = 123456789


@pytest.fixture
def db_user(transactional_db):  # ← Используем transactional_db вместо db
    """Пользователь с привязанным Telegram chat_id"""
    user = User.objects.create_user(username="testuser_bot", email="bot_test@example.com", password="SecurePass123!")
    user.telegram_chat_id = TEST_CHAT_ID
    user.save()
    return user


@pytest.fixture
def update_mock():
    """Правильно настроенный мок для асинхронных вызовов"""
    update = MagicMock()
    update.effective_chat = MagicMock()
    update.effective_chat.id = TEST_CHAT_ID

    # AsyncMock для метода reply_text
    update.message = MagicMock()
    update.message.reply_text = AsyncMock(return_value=None)
    update.message.text = "Тест"

    return update


@pytest.fixture
def context_mock():
    """Контекст с реальным словарём"""
    context = MagicMock()
    context.user_data = {}  # Реальный словарь, не мок!
    context.bot = AsyncMock()
    return context


@pytest.fixture(autouse=True)
def close_db_connections():
    """Закрываем соединения с БД после каждого теста"""
    from django.db import connection

    yield
    if connection.connection:
        connection.close()
