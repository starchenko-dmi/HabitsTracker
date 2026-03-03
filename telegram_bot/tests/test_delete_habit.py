from datetime import time as time_type
import pytest


pytestmark = pytest.mark.django_db


class TestDeleteHabitFlow:
    """Тесты процесса удаления привычки"""

    @pytest.mark.asyncio
    async def test_delete_habit_start_unregistered(self, update_mock, context_mock):
        """Попытка удаления привычки без регистрации"""
        from telegram_bot.bot import ConversationHandler, delete_habit_start

        update_mock.effective_chat.id = 999999999

        result = await delete_habit_start(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "зарегистрируйтесь" in text
        assert "/start" in text
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_delete_habit_start_no_habits(self, update_mock, context_mock, db_user):
        """Попытка удаления при отсутствии привычек"""
        from telegram_bot.bot import ConversationHandler, delete_habit_start

        update_mock.effective_chat.id = db_user.telegram_chat_id

        result = await delete_habit_start(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "нет привычек" in text or "создайте привычку" in text
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_delete_habit_start_with_habits(self, update_mock, context_mock, db_user):
        """Начало удаления с существующими привычками"""
        from asgiref.sync import sync_to_async

        from telegram_bot.bot import SELECT_HABIT_TO_DELETE, delete_habit_start

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

        result = await delete_habit_start(update_mock, context_mock)

        assert "habits_list" in context_mock.user_data
        assert len(context_mock.user_data["habits_list"]) > 0
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "выберите" in text
        assert result == SELECT_HABIT_TO_DELETE  # SELECT_HABIT_TO_DELETE = 12

    @pytest.mark.asyncio
    async def test_confirm_delete_no(self, update_mock, context_mock, db_user):
        """Отмена удаления привычки"""
        from telegram_bot.bot import ConversationHandler, confirm_delete

        # Предварительно заполняем данные для удаления
        context_mock.user_data["habit_to_delete"] = {"id": 1, "action": "тестовая привычка"}
        update_mock.message.text = "Отмена"

        result = await confirm_delete(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "отменено" in text
        assert result == ConversationHandler.END
