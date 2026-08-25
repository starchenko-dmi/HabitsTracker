from datetime import time as time_type
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asgiref.sync import sync_to_async

pytestmark = pytest.mark.django_db


class TestCoverageFinalExtra:
    """Дополнительные тесты для достижения 85%+ покрытия"""

    @pytest.fixture(autouse=True)
    def setup_fixtures(self, db_user, update_mock, context_mock):
        """Настройка фикстур"""
        self.db_user = db_user
        self.update_mock = update_mock
        self.context_mock = context_mock
        # Гарантируем корректные моки
        self.update_mock.message = AsyncMock()
        self.update_mock.message.reply_text = AsyncMock(return_value=None)
        self.update_mock.message.reply_html = AsyncMock(return_value=None)
        self.update_mock.effective_user = MagicMock()
        self.update_mock.effective_user.id = db_user.telegram_chat_id
        self.update_mock.effective_user.first_name = "TestUser"

    # ========== ВАЛИДАЦИЯ В СОЗДАНИИ ПРИВЫЧКИ ==========

    @pytest.mark.asyncio
    async def test_create_habit_validation_all_scenarios(self, db_user):
        """Покрытие всех сценариев валидации в create_habit"""
        from telegram_bot.bot import create_habit

        # Тест 1: Одновременно вознаграждение и связанная привычка
        with pytest.raises(ValueError, match="Нельзя указать одновременно"):
            await create_habit(
                user_id=db_user.id,
                place="дома",
                time=time_type(8, 0),
                action="тест",
                is_pleasant=False,
                related_habit_id=1,
                reward="тест",
                duration=60,
                periodicity=1,
            )

        # Тест 2: Связанная привычка не является приятной
        with pytest.raises(ValueError, match="Связанная привычка должна быть приятной"):
            await create_habit(
                user_id=db_user.id,
                place="дома",
                time=time_type(8, 0),
                action="тест",
                is_pleasant=False,
                related_habit_id=999999,
                duration=60,
                periodicity=1,
            )

        # Тест 3: У приятной привычки есть вознаграждение
        with pytest.raises(ValueError, match="У приятной привычки не может быть"):
            await create_habit(
                user_id=db_user.id,
                place="дома",
                time=time_type(8, 0),
                action="тест",
                is_pleasant=True,
                reward="тест",
                duration=60,
                periodicity=1,
            )

        # Тест 4: Время выполнения > 120 секунд
        with pytest.raises(ValueError, match="Время выполнения не должно превышать 120 секунд"):
            await create_habit(
                user_id=db_user.id, place="дома", time=time_type(8, 0), action="тест", duration=121, periodicity=1
            )

        # Тест 5: Периодичность < 1
        with pytest.raises(ValueError, match="Периодичность должна быть от 1 до 7 дней"):
            await create_habit(user_id=db_user.id, place="дома", time=time_type(8, 0), action="тест", periodicity=0)

        # Тест 6: Периодичность > 7
        with pytest.raises(ValueError, match="Периодичность должна быть от 1 до 7 дней"):
            await create_habit(user_id=db_user.id, place="дома", time=time_type(8, 0), action="тест", periodicity=8)

    # ========== ОБРАБОТКА ОШИБОК В РЕГИСТРАЦИИ ==========

    @pytest.mark.asyncio
    async def test_register_password_integrity_error(self, update_mock, context_mock, db_user):
        """Покрытие ошибки целостности при регистрации (пользователь уже существует)"""
        from telegram_bot.bot import register_password

        # Настраиваем контекст с данными существующего пользователя
        context_mock.user_data = {
            "username": db_user.username,
            "email": "new@example.com",
        }
        update_mock.effective_chat.id = 999888777
        update_mock.message.text = "NewPass123!"

        await register_password(update_mock, context_mock)

        # Проверяем, что отправлено сообщение об ошибке
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "ошибка" in text or "существует" in text

    @pytest.mark.asyncio
    async def test_register_password_general_exception(self, update_mock, context_mock):
        """Покрытие общей ошибки при регистрации"""
        from telegram_bot.bot import register_password

        context_mock.user_data = {
            "username": "newuser",
            "email": "new@example.com",
        }
        update_mock.effective_chat.id = 999888777
        update_mock.message.text = "NewPass123!"

        # Мокаем создание пользователя с исключением
        with patch("telegram_bot.bot.create_user", side_effect=Exception("General error")):
            await register_password(update_mock, context_mock)

            assert update_mock.message.reply_text.called
            text = update_mock.message.reply_text.call_args[0][0].lower()
            assert "ошибка" in text

    # ========== УДАЛЕНИЕ ПРИВЫЧКИ С ПОДТВЕРЖДЕНИЕМ ==========

    @pytest.mark.asyncio
    async def test_delete_habit_full_flow_with_confirmation(self, db_user, update_mock, context_mock):
        """Покрытие полного цикла удаления привычки с подтверждением"""
        from habits.models import Habit
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

        # Шаг 3: Подтверждение (Да)
        update_mock.message.text = "Да"
        with patch("telegram_bot.bot.delete_habit", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True
            result = await confirm_delete(update_mock, context_mock)
            assert result == ConversationHandler.END

            # Проверяем сообщение об успешном удалении
            assert update_mock.message.reply_text.called
            text = update_mock.message.reply_text.call_args[0][0].lower()
            assert "удалена" in text

    # ========== ФОРМИРОВАНИЕ СООБЩЕНИЙ С HTML ==========

    @pytest.mark.asyncio
    async def test_start_registered_user_html_formatting(self, db_user, update_mock, context_mock):
        """Покрытие форматирования HTML в /start для зарегистрированного пользователя"""
        from telegram_bot.bot import start

        update_mock.effective_chat.id = db_user.telegram_chat_id

        await start(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        call_kwargs = update_mock.message.reply_text.call_args[1]
        assert call_kwargs.get("parse_mode") == "HTML"

        # Проверяем наличие HTML-тегов
        message = update_mock.message.reply_text.call_args[0][0]
        assert "<b>" in message or "🤖" in message
        assert "/create" in message
        assert "/habits" in message

    @pytest.mark.asyncio
    async def test_show_habits_html_formatting(self, db_user, update_mock, context_mock):
        """Покрытие форматирования HTML в списке привычек"""
        from habits.models import Habit
        from telegram_bot.bot import show_habits

        # Создаём привычку
        @sync_to_async
        def create_habit():
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
        call_kwargs = update_mock.message.reply_text.call_args[1]
        assert call_kwargs.get("parse_mode") == "HTML"

        # Проверяем наличие HTML-тегов
        message = update_mock.message.reply_text.call_args[0][0]
        assert "<b>" in message or "📋" in message
        assert "08:00" in message

    @pytest.mark.asyncio
    async def test_show_statistics_html_formatting(self, db_user, update_mock, context_mock):
        """Покрытие форматирования HTML в статистике"""
        from habits.models import Habit
        from telegram_bot.bot import show_statistics

        # Создаём привычку
        @sync_to_async
        def create_habit():
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

        await show_statistics(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        call_kwargs = update_mock.message.reply_text.call_args[1]
        assert call_kwargs.get("parse_mode") == "HTML"

        # Проверяем наличие HTML-тегов
        message = update_mock.message.reply_text.call_args[0][0]
        assert "<b>" in message or "📊" in message
        assert "1" in message  # Количество привычек
