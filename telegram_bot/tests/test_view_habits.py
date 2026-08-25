from datetime import time as time_type

import pytest
from asgiref.sync import sync_to_async

pytestmark = pytest.mark.django_db


class TestViewHabits:
    """Тесты просмотра привычек"""

    @pytest.mark.asyncio
    async def test_show_habits_unregistered(self, update_mock, context_mock):
        """Проверка для незарегистрированного пользователя"""
        from telegram_bot.bot import show_habits

        update_mock.effective_chat.id = 999999999

        await show_habits(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "зарегистрируйтесь" in text
        assert "/start" in text

    @pytest.mark.asyncio
    async def test_show_habits_no_habits(self, update_mock, context_mock, db_user):
        """Проверка для зарегистрированного пользователя БЕЗ привычек"""
        from telegram_bot.bot import show_habits

        # КРИТИЧЕСКИ ВАЖНО: совпадение chat_id
        update_mock.effective_chat.id = db_user.telegram_chat_id

        await show_habits(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        # Учитываем реальное сообщение бота
        assert "нет активных привычек" in text or "нет привычек" in text
        assert "зарегистрируйтесь" not in text

    @pytest.mark.asyncio
    async def test_show_habits_with_habits(self, update_mock, context_mock, db_user):
        """Проверка списка привычек"""
        from telegram_bot.bot import show_habits

        # Создаём привычку
        @sync_to_async
        def create_habit():
            from habits.models import Habit

            return Habit.objects.create(
                user=db_user,
                place="спортзал",
                time=time_type(19, 0),
                action="сделать 10 отжиманий",
                is_pleasant=False,
                reward="посмотреть серию",
                duration=120,
                periodicity=1,
                is_public=True,
            )

        await create_habit()

        await show_habits(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "ваши привычки" in text
        assert "отжимани" in text
