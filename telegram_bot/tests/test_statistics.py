from datetime import time as time_type

import pytest
from asgiref.sync import sync_to_async

pytestmark = pytest.mark.django_db


class TestStatistics:
    """Тесты статистики привычек"""

    @pytest.mark.asyncio
    async def test_show_statistics_unregistered(self, update_mock, context_mock):
        """Проверка сообщения для незарегистрированного пользователя"""
        from telegram_bot.bot import show_statistics

        # Устанавливаем НЕСУЩЕСТВУЮЩИЙ chat_id
        update_mock.effective_chat.id = 999999999

        await show_statistics(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "зарегистрируйтесь" in text
        assert "/start" in text

    @pytest.mark.asyncio
    async def test_show_statistics_no_habits(self, update_mock, context_mock, db_user):
        """Проверка сообщения для зарегистрированного пользователя БЕЗ привычек"""
        from telegram_bot.bot import show_statistics

        # КРИТИЧЕСКИ ВАЖНО: совпадение chat_id
        assert update_mock.effective_chat.id == db_user.telegram_chat_id

        await show_statistics(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        # Учитываем реальное сообщение бота
        assert "статистик" in text
        assert "0" in text or "нет" in text
        assert "зарегистрируйтесь" not in text

    @pytest.mark.asyncio
    async def test_show_statistics_with_habits(self, update_mock, context_mock, db_user):
        """Проверка статистики с одной привычкой"""
        from telegram_bot.bot import show_statistics

        # Создаём привычку напрямую через sync_to_async
        @sync_to_async
        def create_habit():
            from habits.models import Habit

            return Habit.objects.create(
                user=db_user,
                place="дома",
                time=time_type(8, 0),
                action="выпить чай",
                is_pleasant=True,
                duration=60,
                periodicity=1,
            )

        await create_habit()

        await show_statistics(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "статистик" in text
        assert "1" in text  # Одна привычка
        assert "приятн" in text  # Упоминание типа привычки
