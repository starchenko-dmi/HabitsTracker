from datetime import time as time_type
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.django_db


class TestCreateHabitFlow:
    """Тесты полного цикла создания привычки"""

    @pytest.mark.asyncio
    async def test_create_habit_start_unregistered(self, update_mock, context_mock):
        """Попытка создания привычки без регистрации"""
        from telegram_bot.bot import ConversationHandler, create_habit_start

        update_mock.effective_chat.id = 999999999

        result = await create_habit_start(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "зарегистрируйтесь" in text
        assert "/start" in text
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_create_habit_start_registered(self, update_mock, context_mock, db_user):
        """Начало создания привычки для зарегистрированного пользователя"""
        from telegram_bot.bot import PLACE, create_habit_start

        update_mock.effective_chat.id = db_user.telegram_chat_id

        result = await create_habit_start(update_mock, context_mock)

        # Проверяем, что в контексте появилось состояние привычки
        assert "habit" in context_mock.user_data
        assert context_mock.user_data["habit"]["user_id"] == db_user.id
        assert update_mock.message.reply_text.called

        # Анализируем текст сообщения
        text = update_mock.message.reply_text.call_args[0][0].lower()

        # Проверяем ключевые элементы сообщения (без жёсткой привязки к опечаткам)
        assert "1" in text  # Номер шага (цифра надёжнее слова "шаг" из-за возможных опечаток)
        assert "где" in text  # Суть вопроса о месте выполнения
        assert "привычк" in text  # Корень слова "привычка" для подтверждения контекста

        assert result == PLACE  # PLACE = 3

    @pytest.mark.asyncio
    async def test_habit_place_valid(self, update_mock, context_mock, db_user):
        """Валидное место выполнения"""
        from telegram_bot.bot import TIME, habit_place

        # Инициализируем состояние ВРУЧНУЮ (т.к. предыдущий шаг не вызывался)
        context_mock.user_data["habit"] = {"user_id": db_user.id}
        update_mock.message.text = "дома"

        result = await habit_place(update_mock, context_mock)

        assert context_mock.user_data["habit"]["place"] == "дома"
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "шаг 2" in text
        assert "время" in text or "чч:мм" in text
        assert result == TIME  # TIME = 4

    @pytest.mark.asyncio
    async def test_habit_time_valid(self, update_mock, context_mock, db_user):
        """Валидное время выполнения"""
        from telegram_bot.bot import ACTION, habit_time

        context_mock.user_data["habit"] = {"user_id": db_user.id, "place": "дома"}
        update_mock.message.text = "08:30"

        result = await habit_time(update_mock, context_mock)

        assert isinstance(context_mock.user_data["habit"]["time"], time_type)
        assert context_mock.user_data["habit"]["time"] == time_type(8, 30)
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "шаг 3" in text
        assert "действие" in text
        assert result == ACTION  # ACTION = 5

    @pytest.mark.asyncio
    async def test_habit_action_valid(self, update_mock, context_mock, db_user):
        """Валидное действие"""
        from telegram_bot.bot import IS_PLEASANT, habit_action

        context_mock.user_data["habit"] = {"user_id": db_user.id, "place": "дома", "time": time_type(8, 30)}
        update_mock.message.text = "выпить стакан воды"

        result = await habit_action(update_mock, context_mock)

        assert context_mock.user_data["habit"]["action"] == "выпить стакан воды"
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "шаг 4" in text
        assert "приятная" in text
        assert result == IS_PLEASANT  # IS_PLEASANT = 6

    @pytest.mark.asyncio
    async def test_habit_is_pleasant_yes(self, update_mock, context_mock, db_user):
        """Выбор приятной привычки"""
        from telegram_bot.bot import DURATION, habit_is_pleasant

        context_mock.user_data["habit"] = {
            "user_id": db_user.id,
            "place": "дома",
            "time": time_type(8, 30),
            "action": "медитировать",
        }
        update_mock.message.text = "Да"

        result = await habit_is_pleasant(update_mock, context_mock)

        assert context_mock.user_data["habit"]["is_pleasant"] is True
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "шаг 5" in text
        assert "время" in text or "секунд" in text
        assert result == DURATION  # DURATION = 9

    @pytest.mark.asyncio
    async def test_habit_duration_valid(self, update_mock, context_mock, db_user):
        """Валидная длительность"""
        from telegram_bot.bot import PERIODICITY, habit_duration

        context_mock.user_data["habit"] = {
            "user_id": db_user.id,
            "place": "дома",
            "time": time_type(8, 30),
            "action": "медитировать",
            "is_pleasant": True,
        }
        update_mock.message.text = "60"

        result = await habit_duration(update_mock, context_mock)

        assert context_mock.user_data["habit"]["duration"] == 60
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "шаг 8" in text
        assert "периодичность" in text
        assert result == PERIODICITY  # PERIODICITY = 10

    @pytest.mark.asyncio
    async def test_habit_periodicity_valid(self, update_mock, context_mock, db_user):
        """Валидная периодичность"""
        from telegram_bot.bot import IS_PUBLIC, habit_periodicity

        context_mock.user_data["habit"] = {
            "user_id": db_user.id,
            "place": "дома",
            "time": time_type(8, 30),
            "action": "медитировать",
            "is_pleasant": True,
            "duration": 60,
        }
        update_mock.message.text = "1"

        result = await habit_periodicity(update_mock, context_mock)

        assert context_mock.user_data["habit"]["periodicity"] == 1
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "публичной" in text or "публичная" in text
        assert result == IS_PUBLIC  # IS_PUBLIC = 11

    @pytest.mark.asyncio
    async def test_habit_is_public_yes(self, update_mock, context_mock, db_user):
        """Выбор публичной привычки"""
        from unittest.mock import AsyncMock

        from telegram_bot.bot import ConversationHandler, habit_is_public

        # Мокаем создание привычки
        with patch("telegram_bot.bot.create_habit", new_callable=AsyncMock) as mock_create:
            mock_habit = AsyncMock()
            mock_habit.place = "дома"
            mock_habit.time = time_type(8, 30)
            mock_habit.action = "медитировать"
            mock_habit.is_pleasant = True
            mock_habit.duration = 60
            mock_habit.periodicity = 1
            mock_habit.is_public = True
            mock_create.return_value = mock_habit

            context_mock.user_data["habit"] = {
                "user_id": db_user.id,
                "place": "дома",
                "time": time_type(8, 30),
                "action": "медитировать",
                "is_pleasant": True,
                "duration": 60,
                "periodicity": 1,
            }
            update_mock.message.text = "Да"

            result = await habit_is_public(update_mock, context_mock)

            assert update_mock.message.reply_text.called
            text = update_mock.message.reply_text.call_args[0][0].lower()
            assert "создана" in text or "успешно" in text
            assert result == ConversationHandler.END
