from datetime import time as time_type
from unittest.mock import AsyncMock, patch

import pytest
from asgiref.sync import sync_to_async

pytestmark = pytest.mark.django_db


class TestCoverageBoost:
    """Тесты для повышения покрытия до 80%+"""

    @pytest.mark.asyncio
    async def test_get_user_habits_data_with_habits(self, db_user, update_mock, context_mock):
        """Покрытие строк 101-131: получение данных привычек с реальными привычками"""
        from telegram_bot.bot import get_user_habits_data

        # Создаём привычки
        @sync_to_async
        def create_habits():
            from habits.models import Habit

            Habit.objects.create(
                user=db_user,
                place="дома",
                time=time_type(8, 0),
                action="выпить чай",
                is_pleasant=True,
                duration=60,
                periodicity=1,
            )
            Habit.objects.create(
                user=db_user,
                place="спортзал",
                time=time_type(19, 0),
                action="сделать 10 отжиманий",
                is_pleasant=False,
                reward="посмотреть серию",
                duration=120,
                periodicity=1,
            )

        await create_habits()

        habits = await get_user_habits_data(db_user.telegram_chat_id)

        assert len(habits) == 2
        assert any(h["is_pleasant"] for h in habits)
        assert any(not h["is_pleasant"] for h in habits)

    @pytest.mark.asyncio
    async def test_register_start_already_registered(self, db_user, update_mock, context_mock):
        """Покрытие строк 265-275: попытка регистрации уже зарегистрированного пользователя"""
        from telegram_bot.bot import ConversationHandler, register_start

        update_mock.effective_chat.id = db_user.telegram_chat_id

        result = await register_start(update_mock, context_mock)

        assert result == ConversationHandler.END
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "уже зарегистрированы" in text

    @pytest.mark.asyncio
    async def test_bind_account_already_bound(self, db_user, update_mock, context_mock):
        """Покрытие строк 394-404: попытка привязки уже привязанного аккаунта"""
        from telegram_bot.bot import ConversationHandler, bind_account

        update_mock.effective_chat.id = db_user.telegram_chat_id

        result = await bind_account(update_mock, context_mock)

        assert result == ConversationHandler.END
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "уже привязан" in text

    @pytest.mark.asyncio
    async def test_create_habit_full_cycle(self, db_user, update_mock, context_mock):
        """Покрытие строк 440-751: полный цикл создания привычки"""
        from telegram_bot.bot import (
            ACTION,
            DURATION,
            IS_PLEASANT,
            IS_PUBLIC,
            PERIODICITY,
            PLACE,
            TIME,
            ConversationHandler,
            create_habit_start,
            habit_action,
            habit_duration,
            habit_is_pleasant,
            habit_is_public,
            habit_periodicity,
            habit_place,
            habit_time,
        )

        # Шаг 1: Начало создания
        update_mock.effective_chat.id = db_user.telegram_chat_id
        result = await create_habit_start(update_mock, context_mock)
        assert result == PLACE
        assert "habit" in context_mock.user_data

        # Шаг 2: Место
        update_mock.message.text = "дома"
        result = await habit_place(update_mock, context_mock)
        assert result == TIME
        assert context_mock.user_data["habit"]["place"] == "дома"

        # Шаг 3: Время
        update_mock.message.text = "08:00"
        result = await habit_time(update_mock, context_mock)
        assert result == ACTION
        assert context_mock.user_data["habit"]["time"] == time_type(8, 0)

        # Шаг 4: Действие
        update_mock.message.text = "выпить стакан воды"
        result = await habit_action(update_mock, context_mock)
        assert result == IS_PLEASANT

        # Шаг 5: Тип привычки (приятная)
        update_mock.message.text = "Да"
        result = await habit_is_pleasant(update_mock, context_mock)
        assert result == DURATION
        assert context_mock.user_data["habit"]["is_pleasant"] is True

        # Шаг 6: Длительность
        update_mock.message.text = "60"
        result = await habit_duration(update_mock, context_mock)
        assert result == PERIODICITY

        # Шаг 7: Периодичность
        update_mock.message.text = "1"
        result = await habit_periodicity(update_mock, context_mock)
        assert result == IS_PUBLIC

        # Шаг 8: Публичность
        update_mock.message.text = "Нет"
        with patch("telegram_bot.bot.create_habit", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = AsyncMock(
                place="дома",
                time=time_type(8, 0),
                action="выпить стакан воды",
                is_pleasant=True,
                duration=60,
                periodicity=1,
                is_public=False,
            )
            result = await habit_is_public(update_mock, context_mock)
            assert result == ConversationHandler.END
            assert update_mock.message.reply_text.called

    @pytest.mark.asyncio
    async def test_show_habits_with_data(self, db_user, update_mock, context_mock):
        """Покрытие строк 756-795: просмотр привычек с реальными данными"""
        from asgiref.sync import sync_to_async

        from telegram_bot.bot import show_habits

        # Создаём привычку
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

        update_mock.effective_chat.id = db_user.telegram_chat_id

        await show_habits(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "ваши привычки" in text
        assert "выпить чай" in text
        assert "08:00" in text

    @pytest.mark.asyncio
    async def test_delete_habit_full_flow(self, db_user, update_mock, context_mock):
        """Покрытие строк 800-905: полный цикл удаления привычки"""
        from asgiref.sync import sync_to_async

        from telegram_bot.bot import (
            CONFIRM_DELETE,
            SELECT_HABIT_TO_DELETE,
            ConversationHandler,
            confirm_delete,
            delete_habit_start,
            select_habit_to_delete,
        )

        # Создаём привычку
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

        update_mock.effective_chat.id = db_user.telegram_chat_id

        # Шаг 1: Начало удаления
        result = await delete_habit_start(update_mock, context_mock)
        assert result == SELECT_HABIT_TO_DELETE
        assert "habits_list" in context_mock.user_data

        # Шаг 2: Выбор привычки
        update_mock.message.text = "1"
        result = await select_habit_to_delete(update_mock, context_mock)
        assert result == CONFIRM_DELETE
        assert "habit_to_delete" in context_mock.user_data

        # Шаг 3: Подтверждение
        update_mock.message.text = "Да"
        with patch("telegram_bot.bot.delete_habit", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True
            result = await confirm_delete(update_mock, context_mock)
            assert result == ConversationHandler.END
            assert update_mock.message.reply_text.called
            text = update_mock.message.reply_text.call_args[0][0].lower()
            assert "удалена" in text

    @pytest.mark.asyncio
    async def test_show_statistics_with_data(self, db_user, update_mock, context_mock):
        """Покрытие строк 910-935: статистика с реальными данными"""
        from asgiref.sync import sync_to_async

        from telegram_bot.bot import show_statistics

        # Создаём привычки
        @sync_to_async
        def create_habits():
            from habits.models import Habit

            Habit.objects.create(
                user=db_user,
                place="дома",
                time=time_type(8, 0),
                action="выпить чай",
                is_pleasant=True,
                duration=60,
                periodicity=1,
            )
            Habit.objects.create(
                user=db_user,
                place="спортзал",
                time=time_type(19, 0),
                action="сделать 10 отжиманий",
                is_pleasant=False,
                reward="посмотреть серию",
                duration=120,
                periodicity=1,
            )

        await create_habits()

        update_mock.effective_chat.id = db_user.telegram_chat_id

        await show_statistics(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "статистика" in text
        assert "2" in text  # Всего привычек
        assert "1" in text  # Приятных и полезных
