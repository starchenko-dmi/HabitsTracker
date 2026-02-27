from unittest.mock import Mock, patch

import pytest

from telegram_bot.bot import send_message
from telegram_bot.tasks import send_habit_reminders
from telegram_bot.utils import get_bot, set_commands


@pytest.mark.django_db
class TestTelegramBot:
    """Тесты для интеграции с Telegram"""

    @patch("telegram_bot.bot.Bot")
    def test_send_message_success(self, mock_bot_class):
        """Тест успешной отправки сообщения"""
        # Создаем мок объекта бота
        mock_bot_instance = Mock()
        mock_bot_class.return_value = mock_bot_instance

        # Вызываем функцию
        result = send_message(123456789, "Тестовое сообщение")

        # Проверяем, что метод send_message был вызван
        mock_bot_instance.send_message.assert_called_once_with(
            chat_id=123456789, text="Тестовое сообщение", parse_mode="HTML"
        )
        assert result is True

    @patch("telegram_bot.bot.Bot")
    def test_send_message_failure(self, mock_bot_class):
        """Тест обработки ошибки при отправке сообщения"""
        # Создаем мок объекта бота, который выбрасывает исключение
        mock_bot_instance = Mock()
        mock_bot_instance.send_message.side_effect = Exception("Ошибка отправки")
        mock_bot_class.return_value = mock_bot_instance

        # Вызываем функцию
        result = send_message(123456789, "Тестовое сообщение")

        # Проверяем, что функция вернула False
        assert result is False

    @patch("telegram_bot.bot.send_message")
    def test_send_habit_reminders_task(self, mock_send_message):
        """Тест задачи отправки напоминаний"""
        # Создаем тестовые данные
        from datetime import time

        from habits.models import Habit
        from users.models import User

        user = User.objects.create_user(
            email="test@example.com", username="testuser", password="password123", telegram_chat_id=123456789
        )

        Habit.objects.create(user=user, place="Дом", time=time(8, 0), action="Пробежка", duration=60, periodicity=1)

        # Вызываем задачу
        result = send_habit_reminders()

        # Проверяем результат
        assert "sent" in result
        assert "failed" in result


@pytest.mark.django_db
@patch("telegram_bot.utils.Bot")
def test_get_bot_success(mock_bot_class):
    """Тест получения экземпляра бота при наличии токена"""
    from django.conf import settings

    with patch.object(settings, "TELEGRAM_BOT_TOKEN", "test_token_123"):
        bot = get_bot()
        assert bot is not None
        mock_bot_class.assert_called_once_with(token="test_token_123")


@pytest.mark.django_db
@patch("telegram_bot.utils.Bot")
def test_get_bot_no_token(mock_bot_class):
    """Тест получения бота при отсутствии токена"""
    from django.conf import settings

    with patch.object(settings, "TELEGRAM_BOT_TOKEN", ""):
        bot = get_bot()
        assert bot is None
        mock_bot_class.assert_not_called()


@pytest.mark.django_db
@patch("telegram_bot.utils.get_bot")
def test_set_commands_success(mock_get_bot):
    """Тест установки команд бота"""
    # Создаём мок бота
    mock_bot = Mock()
    mock_bot.set_my_commands.return_value = True
    mock_get_bot.return_value = mock_bot

    result = set_commands()

    assert result is True
    mock_bot.set_my_commands.assert_called_once()
    # Проверяем, что команды переданы корректно
    call_args = mock_bot.set_my_commands.call_args
    assert len(call_args[0][0]) == 4  # 4 команды


@pytest.mark.django_db
@patch("telegram_bot.utils.get_bot")
def test_set_commands_no_bot(mock_get_bot):
    """Тест установки команд при отсутствии бота"""
    mock_get_bot.return_value = None

    result = set_commands()

    assert result is False
