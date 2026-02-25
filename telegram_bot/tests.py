# telegram_bot/tests.py
import pytest
from unittest.mock import Mock, patch
from telegram_bot.bot import send_message
from telegram_bot.tasks import send_habit_reminders


@pytest.mark.django_db
class TestTelegramBot:
    """Тесты для интеграции с Telegram"""

    @patch('telegram_bot.bot.Bot')
    def test_send_message_success(self, mock_bot_class):
        """Тест успешной отправки сообщения"""
        # Создаем мок объекта бота
        mock_bot_instance = Mock()
        mock_bot_class.return_value = mock_bot_instance

        # Вызываем функцию
        result = send_message(123456789, "Тестовое сообщение")

        # Проверяем, что метод send_message был вызван
        mock_bot_instance.send_message.assert_called_once_with(
            chat_id=123456789,
            text="Тестовое сообщение",
            parse_mode='HTML'
        )
        assert result is True

    @patch('telegram_bot.bot.Bot')
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

    @patch('telegram_bot.bot.send_message')
    def test_send_habit_reminders_task(self, mock_send_message):
        """Тест задачи отправки напоминаний"""
        # Создаем тестовые данные
        from users.models import User
        from habits.models import Habit
        from datetime import time

        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='password123',
            telegram_chat_id=123456789
        )

        Habit.objects.create(
            user=user,
            place='Дом',
            time=time(8, 0),
            action='Пробежка',
            duration=60,
            periodicity=1
        )

        # Вызываем задачу
        result = send_habit_reminders()

        # Проверяем результат
        assert 'sent' in result
        assert 'failed' in result