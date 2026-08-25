import logging
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings

# Настройка логгера для тестов
logging.basicConfig(level=logging.CRITICAL)


class TestUtils:
    """Тесты вспомогательных функций"""

    @pytest.fixture(autouse=True)
    def setup_settings(self):
        """Гарантируем наличие токена в настройках для тестов"""
        # Сохраняем оригинальное значение
        original_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        settings.TELEGRAM_BOT_TOKEN = "test_token_12345"
        yield
        # Восстанавливаем оригинальное значение
        if original_token is not None:
            settings.TELEGRAM_BOT_TOKEN = original_token
        else:
            # Если токена не было, удаляем атрибут безопасно
            if hasattr(settings, "TELEGRAM_BOT_TOKEN"):
                delattr(settings, "TELEGRAM_BOT_TOKEN")

    def test_send_message_success(self):
        """Проверка успешной отправки сообщения"""
        from telegram_bot.utils import send_message

        chat_id = 123456789
        text = "Тестовое сообщение"

        # Мокаем успешный ответ от Telegram API
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": {}}

        with patch("telegram_bot.utils.requests.post", return_value=mock_response) as mock_post:
            result = send_message(chat_id, text)

            assert result is True
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args[1]
            assert call_kwargs["json"]["chat_id"] == chat_id
            assert call_kwargs["json"]["text"] == text
            assert call_kwargs["json"]["parse_mode"] == "HTML"

    def test_send_message_invalid_chat_id(self):
        """Проверка отправки сообщения без chat_id"""
        from telegram_bot.utils import send_message

        result = send_message(None, "Тест")
        assert result is False

    def test_send_message_no_token(self):
        """Проверка отправки сообщения без токена"""
        from telegram_bot.utils import send_message

        # Временно устанавливаем токен в None (безопасно)
        original_token = settings.TELEGRAM_BOT_TOKEN
        settings.TELEGRAM_BOT_TOKEN = None

        try:
            result = send_message(123456789, "Тест")
            assert result is False
        finally:
            settings.TELEGRAM_BOT_TOKEN = original_token

    def test_send_message_api_error(self):
        """Проверка обработки ошибки API Telegram"""
        from telegram_bot.utils import send_message

        chat_id = 123456789
        text = "Тестовое сообщение"

        # Мокаем ошибочный ответ от Telegram API
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"ok": False, "description": "Bad Request"}

        with patch("telegram_bot.utils.requests.post", return_value=mock_response):
            result = send_message(chat_id, text)
            assert result is False

    def test_send_message_timeout(self):
        """Проверка обработки таймаута"""
        from telegram_bot.utils import send_message

        with patch("telegram_bot.utils.requests.post", side_effect=TimeoutError):
            result = send_message(123456789, "Тест")
            assert result is False

    def test_send_message_network_error(self):
        """Проверка обработки сетевой ошибки"""
        from telegram_bot.utils import send_message

        with patch("telegram_bot.utils.requests.post", side_effect=ConnectionError("Network error")):
            result = send_message(123456789, "Тест")
            assert result is False

    def test_get_bot_success(self):
        """Проверка получения экземпляра бота"""
        from telegram_bot.utils import get_bot

        bot = get_bot()

        assert bot is not None
        assert bot.token == settings.TELEGRAM_BOT_TOKEN

    def test_get_bot_no_token(self):
        """Проверка получения бота без токена"""
        from telegram_bot.utils import get_bot

        # Временно устанавливаем токен в None (безопасно)
        original_token = settings.TELEGRAM_BOT_TOKEN
        settings.TELEGRAM_BOT_TOKEN = None

        try:
            bot = get_bot()
            assert bot is None
        finally:
            settings.TELEGRAM_BOT_TOKEN = original_token

    @patch("telegram_bot.utils.get_bot")
    def test_set_commands_success(self, mock_get_bot):
        """Проверка успешной установки команд"""
        from telegram import BotCommand

        from telegram_bot.utils import set_commands

        mock_bot = MagicMock()
        mock_get_bot.return_value = mock_bot

        result = set_commands()

        assert result is True
        mock_bot.set_my_commands.assert_called_once()
        # Проверяем, что переданы правильные команды
        commands = mock_bot.set_my_commands.call_args[0][0]
        assert len(commands) == 4
        assert isinstance(commands[0], BotCommand)
        assert commands[0].command == "start"
        assert commands[1].command == "help"
        assert commands[2].command == "habits"
        assert commands[3].command == "stats"

    @patch("telegram_bot.utils.get_bot")
    def test_set_commands_failure(self, mock_get_bot):
        """Проверка обработки ошибки при установке команд"""
        from telegram_bot.utils import set_commands

        mock_bot = MagicMock()
        mock_bot.set_my_commands.side_effect = Exception("API error")
        mock_get_bot.return_value = mock_bot

        result = set_commands()

        assert result is False

    def test_send_message_url_formatting(self):
        """Проверка корректного форматирования URL без лишних пробелов"""

        from telegram_bot.utils import send_message

        chat_id = 123456789
        text = "Тест"

        url_called = None

        def mock_post(url, **kwargs):
            nonlocal url_called
            url_called = url
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"ok": True}
            return mock_response

        with patch("telegram_bot.utils.requests.post", side_effect=mock_post):
            send_message(chat_id, text)

        # Проверяем, что в URL нет лишних пробелов между 'bot' и токеном
        assert url_called is not None
        # URL должен быть в формате: https://api.telegram.org/bot<token>/sendMessage
        assert "bot  " not in url_called  # Нет двойного пробела
        assert "bot/" not in url_called  # Нет слеша после bot
        # Проверяем наличие токена в правильном месте
        assert f"bot{settings.TELEGRAM_BOT_TOKEN}" in url_called
