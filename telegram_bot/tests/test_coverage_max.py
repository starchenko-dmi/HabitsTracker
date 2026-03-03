from datetime import time as time_type
from unittest.mock import AsyncMock, MagicMock

import pytest
from asgiref.sync import sync_to_async

pytestmark = pytest.mark.django_db


class TestCoverageMax:
    """Максимальное покрытие критических участков кода"""

    @pytest.fixture(autouse=True)
    def setup_fixtures(self, db_user, update_mock, context_mock):
        """Настройка фикстур"""
        self.db_user = db_user
        self.update_mock = update_mock
        self.context_mock = context_mock
        # Гарантируем корректные моки для асинхронных вызовов
        self.update_mock.message = AsyncMock()
        self.update_mock.message.reply_text = AsyncMock(return_value=None)
        self.update_mock.message.reply_html = AsyncMock(return_value=None)
        self.update_mock.effective_user = MagicMock()
        self.update_mock.effective_user.id = db_user.telegram_chat_id
        self.update_mock.effective_user.first_name = "TestUser"

    # ========== ВАЛИДАЦИЯ В СОЗДАНИИ ПРИВЫЧКИ (строки 144-174) ==========

    @pytest.mark.asyncio
    async def test_create_habit_validation_reward_and_related(self, db_user):
        """Покрытие строк 145-148: валидация одновременного указания вознаграждения и связанной привычки"""
        from telegram_bot.bot import create_habit

        with pytest.raises(ValueError, match="Нельзя указать одновременно вознаграждение и связанную привычку"):
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

    @pytest.mark.asyncio
    async def test_create_habit_validation_related_not_pleasant(self, db_user):
        """Покрытие строк 149-151: валидация связанной привычки должна быть приятной"""
        from telegram_bot.bot import create_habit

        with pytest.raises(ValueError, match="Связанная привычка должна быть приятной"):
            await create_habit(
                user_id=db_user.id,
                place="дома",
                time=time_type(8, 0),
                action="тест",
                is_pleasant=False,
                related_habit_id=999999,  # Несуществующая привычка
                duration=60,
                periodicity=1,
            )

    @pytest.mark.asyncio
    async def test_create_habit_validation_pleasant_with_reward(self, db_user):
        """Покрытие строк 152-153: валидация вознаграждения для приятной привычки"""
        from telegram_bot.bot import create_habit

        with pytest.raises(ValueError, match="У приятной привычки не может быть вознаграждения"):
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

    @pytest.mark.asyncio
    async def test_create_habit_validation_duration_exceeded(self, db_user):
        """Покрытие строк 155-156: валидация превышения времени выполнения"""
        from telegram_bot.bot import create_habit

        with pytest.raises(ValueError, match="Время выполнения не должно превышать 120 секунд"):
            await create_habit(
                user_id=db_user.id, place="дома", time=time_type(8, 0), action="тест", duration=121, periodicity=1
            )

    @pytest.mark.asyncio
    async def test_create_habit_validation_periodicity_low(self, db_user):
        """Покрытие строк 158-159: валидация низкой периодичности"""
        from telegram_bot.bot import create_habit

        with pytest.raises(ValueError, match="Периодичность должна быть от 1 до 7 дней"):
            await create_habit(user_id=db_user.id, place="дома", time=time_type(8, 0), action="тест", periodicity=0)

    @pytest.mark.asyncio
    async def test_create_habit_validation_periodicity_high(self, db_user):
        """Покрытие строк 158-159: валидация высокой периодичности"""
        from telegram_bot.bot import create_habit

        with pytest.raises(ValueError, match="Периодичность должна быть от 1 до 7 дней"):
            await create_habit(user_id=db_user.id, place="дома", time=time_type(8, 0), action="тест", periodicity=8)

    # ========== РЕГИСТРАЦИЯ (строки 265-375) ==========

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
    async def test_register_username_invalid_short(self, update_mock, context_mock):
        """Покрытие строк 285-290: короткое имя пользователя"""
        from telegram_bot.bot import USERNAME, register_username

        update_mock.message.text = "ab"
        context_mock.user_data = {}

        result = await register_username(update_mock, context_mock)

        assert result == USERNAME
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "3 символ" in text or "минимум" in text

    @pytest.mark.asyncio
    async def test_register_username_invalid_chars(self, update_mock, context_mock):
        """Покрытие строк 291-296: недопустимые спецсимволы"""
        from telegram_bot.bot import USERNAME, register_username

        update_mock.message.text = "user@name#"
        context_mock.user_data = {}

        result = await register_username(update_mock, context_mock)

        assert result == USERNAME
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "только буквы" in text or "цифры" in text

    @pytest.mark.asyncio
    async def test_register_email_invalid_format(self, update_mock, context_mock):
        """Покрытие строк 314-319: неверный формат email"""
        from telegram_bot.bot import EMAIL, register_email

        update_mock.message.text = "invalid-email"
        context_mock.user_data = {"username": "testuser"}

        result = await register_email(update_mock, context_mock)

        assert result == EMAIL
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "неверный формат" in text or "example" in text

    @pytest.mark.asyncio
    async def test_register_password_invalid_short(self, update_mock, context_mock):
        """Покрытие строк 337-342: короткий пароль"""
        from telegram_bot.bot import PASSWORD, register_password

        update_mock.message.text = "pass123"
        context_mock.user_data = {"username": "testuser", "email": "test@example.com"}

        result = await register_password(update_mock, context_mock)

        assert result == PASSWORD
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "8 символов" in text

    @pytest.mark.asyncio
    async def test_register_password_invalid_only_digits(self, update_mock, context_mock):
        """Покрытие строк 343-348: пароль из одних цифр"""
        from telegram_bot.bot import PASSWORD, register_password

        update_mock.message.text = "12345678"
        context_mock.user_data = {"username": "testuser", "email": "test@example.com"}

        result = await register_password(update_mock, context_mock)

        assert result == PASSWORD
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "буквы и цифры" in text

    @pytest.mark.asyncio
    async def test_register_password_invalid_only_letters(self, update_mock, context_mock):
        """Покрытие строк 343-348: пароль из одних букв"""
        from telegram_bot.bot import PASSWORD, register_password

        update_mock.message.text = "password"
        context_mock.user_data = {"username": "testuser", "email": "test@example.com"}

        result = await register_password(update_mock, context_mock)

        assert result == PASSWORD
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "буквы и цифры" in text

    # ========== ПРИВЯЗКА АККАУНТА (строки 394-412) ==========

    @pytest.mark.asyncio
    async def test_bind_account_already_bound(self, db_user, update_mock, context_mock):
        """Покрытие строк 396-404: попытка привязки уже привязанного аккаунта"""
        from telegram_bot.bot import ConversationHandler, bind_account

        update_mock.effective_chat.id = db_user.telegram_chat_id

        result = await bind_account(update_mock, context_mock)

        assert result == ConversationHandler.END
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "уже привязан" in text

    @pytest.mark.asyncio
    async def test_bind_username_not_found(self, update_mock, context_mock):
        """Покрытие строк 409-412: пользователь не найден"""
        from telegram_bot.bot import USERNAME, bind_username

        update_mock.effective_chat.id = 111222333
        update_mock.message.text = "nonexistent_user"

        result = await bind_username(update_mock, context_mock)

        assert result == USERNAME
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "не найден" in text

    # ========== СОЗДАНИЕ ПРИВЫЧКИ (строки 440-751) ==========

    @pytest.mark.asyncio
    async def test_create_habit_start_unregistered(self, update_mock, context_mock):
        """Покрытие строк 449-460: начало создания для незарегистрированного пользователя"""
        from telegram_bot.bot import ConversationHandler, create_habit_start

        update_mock.effective_chat.id = 999999999

        result = await create_habit_start(update_mock, context_mock)

        assert result == ConversationHandler.END
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "зарегистрируйтесь" in text or "start" in text

    @pytest.mark.asyncio
    async def test_habit_place_invalid_short(self, db_user, update_mock, context_mock):
        """Покрытие строк 471-476: короткое место выполнения"""
        from telegram_bot.bot import PLACE, create_habit_start, habit_place

        update_mock.effective_chat.id = db_user.telegram_chat_id
        await create_habit_start(update_mock, context_mock)

        update_mock.message.text = "a"
        result = await habit_place(update_mock, context_mock)

        assert result == PLACE
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "2 символ" in text or "минимум" in text

    @pytest.mark.asyncio
    async def test_habit_time_invalid_format(self, db_user, update_mock, context_mock):
        """Покрытие строк 489-503: неверный формат времени"""
        from telegram_bot.bot import TIME, create_habit_start, habit_place, habit_time

        update_mock.effective_chat.id = db_user.telegram_chat_id
        await create_habit_start(update_mock, context_mock)
        update_mock.message.text = "дома"
        await habit_place(update_mock, context_mock)

        update_mock.message.text = "25:00"
        result = await habit_time(update_mock, context_mock)

        assert result == TIME
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "неверный формат" in text

    @pytest.mark.asyncio
    async def test_habit_action_invalid_short(self, db_user, update_mock, context_mock):
        """Покрытие строк 517-522: короткое действие"""
        from telegram_bot.bot import ACTION, create_habit_start, habit_action, habit_place, habit_time

        update_mock.effective_chat.id = db_user.telegram_chat_id
        await create_habit_start(update_mock, context_mock)
        update_mock.message.text = "дома"
        await habit_place(update_mock, context_mock)
        update_mock.message.text = "08:00"
        await habit_time(update_mock, context_mock)

        update_mock.message.text = "пить"
        result = await habit_action(update_mock, context_mock)

        assert result == ACTION
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "5 символ" in text or "подробнее" in text

    @pytest.mark.asyncio
    async def test_habit_is_pleasant_invalid_choice(self, db_user, update_mock, context_mock):
        """Покрытие строк 535-540: неверный выбор типа привычки"""
        from telegram_bot.bot import (
            IS_PLEASANT,
            create_habit_start,
            habit_action,
            habit_is_pleasant,
            habit_place,
            habit_time,
        )

        update_mock.effective_chat.id = db_user.telegram_chat_id
        await create_habit_start(update_mock, context_mock)
        update_mock.message.text = "дома"
        await habit_place(update_mock, context_mock)
        update_mock.message.text = "08:00"
        await habit_time(update_mock, context_mock)
        update_mock.message.text = "выпить стакан воды"
        await habit_action(update_mock, context_mock)

        update_mock.message.text = "Может быть"
        result = await habit_is_pleasant(update_mock, context_mock)

        assert result == IS_PLEASANT
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "выберите" in text or "да" in text or "нет" in text

    @pytest.mark.asyncio
    async def test_habit_duration_invalid_low(self, db_user, update_mock, context_mock):
        """Покрытие строк 643-648: низкая длительность"""
        from telegram_bot.bot import (
            DURATION,
            create_habit_start,
            habit_action,
            habit_duration,
            habit_is_pleasant,
            habit_place,
            habit_time,
        )

        update_mock.effective_chat.id = db_user.telegram_chat_id
        await create_habit_start(update_mock, context_mock)
        update_mock.message.text = "дома"
        await habit_place(update_mock, context_mock)
        update_mock.message.text = "08:00"
        await habit_time(update_mock, context_mock)
        update_mock.message.text = "выпить стакан воды"
        await habit_action(update_mock, context_mock)
        update_mock.message.text = "Да"
        await habit_is_pleasant(update_mock, context_mock)

        update_mock.message.text = "0"
        result = await habit_duration(update_mock, context_mock)

        assert result == DURATION
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "1 до 120" in text

    @pytest.mark.asyncio
    async def test_habit_duration_invalid_high(self, db_user, update_mock, context_mock):
        """Покрытие строк 643-648: высокая длительность"""
        from telegram_bot.bot import (
            DURATION,
            create_habit_start,
            habit_action,
            habit_duration,
            habit_is_pleasant,
            habit_place,
            habit_time,
        )

        update_mock.effective_chat.id = db_user.telegram_chat_id
        await create_habit_start(update_mock, context_mock)
        update_mock.message.text = "дома"
        await habit_place(update_mock, context_mock)
        update_mock.message.text = "08:00"
        await habit_time(update_mock, context_mock)
        update_mock.message.text = "выпить стакан воды"
        await habit_action(update_mock, context_mock)
        update_mock.message.text = "Да"
        await habit_is_pleasant(update_mock, context_mock)

        update_mock.message.text = "121"
        result = await habit_duration(update_mock, context_mock)

        assert result == DURATION
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "1 до 120" in text

    @pytest.mark.asyncio
    async def test_habit_periodicity_invalid_low(self, db_user, update_mock, context_mock):
        """Покрытие строк 665-670: низкая периодичность"""
        from telegram_bot.bot import (
            PERIODICITY,
            create_habit_start,
            habit_action,
            habit_duration,
            habit_is_pleasant,
            habit_periodicity,
            habit_place,
            habit_time,
        )

        update_mock.effective_chat.id = db_user.telegram_chat_id
        await create_habit_start(update_mock, context_mock)
        update_mock.message.text = "дома"
        await habit_place(update_mock, context_mock)
        update_mock.message.text = "08:00"
        await habit_time(update_mock, context_mock)
        update_mock.message.text = "выпить стакан воды"
        await habit_action(update_mock, context_mock)
        update_mock.message.text = "Да"
        await habit_is_pleasant(update_mock, context_mock)
        update_mock.message.text = "60"
        await habit_duration(update_mock, context_mock)

        update_mock.message.text = "0"
        result = await habit_periodicity(update_mock, context_mock)

        assert result == PERIODICITY
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "1 до 7" in text

    @pytest.mark.asyncio
    async def test_habit_periodicity_invalid_high(self, db_user, update_mock, context_mock):
        """Покрытие строк 665-670: высокая периодичность"""
        from telegram_bot.bot import (
            PERIODICITY,
            create_habit_start,
            habit_action,
            habit_duration,
            habit_is_pleasant,
            habit_periodicity,
            habit_place,
            habit_time,
        )

        update_mock.effective_chat.id = db_user.telegram_chat_id
        await create_habit_start(update_mock, context_mock)
        update_mock.message.text = "дома"
        await habit_place(update_mock, context_mock)
        update_mock.message.text = "08:00"
        await habit_time(update_mock, context_mock)
        update_mock.message.text = "выпить стакан воды"
        await habit_action(update_mock, context_mock)
        update_mock.message.text = "Да"
        await habit_is_pleasant(update_mock, context_mock)
        update_mock.message.text = "60"
        await habit_duration(update_mock, context_mock)

        update_mock.message.text = "8"
        result = await habit_periodicity(update_mock, context_mock)

        assert result == PERIODICITY
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "1 до 7" in text

    @pytest.mark.asyncio
    async def test_habit_is_public_invalid_choice(self, db_user, update_mock, context_mock):
        """Покрытие строк 713-718: неверный выбор публичности"""
        from telegram_bot.bot import (
            IS_PUBLIC,
            create_habit_start,
            habit_action,
            habit_duration,
            habit_is_pleasant,
            habit_is_public,
            habit_periodicity,
            habit_place,
            habit_time,
        )

        update_mock.effective_chat.id = db_user.telegram_chat_id
        await create_habit_start(update_mock, context_mock)
        update_mock.message.text = "дома"
        await habit_place(update_mock, context_mock)
        update_mock.message.text = "08:00"
        await habit_time(update_mock, context_mock)
        update_mock.message.text = "выпить стакан воды"
        await habit_action(update_mock, context_mock)
        update_mock.message.text = "Да"
        await habit_is_pleasant(update_mock, context_mock)
        update_mock.message.text = "60"
        await habit_duration(update_mock, context_mock)
        update_mock.message.text = "1"
        await habit_periodicity(update_mock, context_mock)

        update_mock.message.text = "Возможно"
        result = await habit_is_public(update_mock, context_mock)

        assert result == IS_PUBLIC
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "выберите" in text or "да" in text or "нет" in text

    # ========== ПРОСМОТР ПРИВЫЧЕК (строки 756-795) ==========

    @pytest.mark.asyncio
    async def test_show_habits_empty(self, db_user, update_mock, context_mock):
        """Покрытие строк 763-768: отсутствие привычек"""
        from telegram_bot.bot import show_habits

        update_mock.effective_chat.id = db_user.telegram_chat_id

        await show_habits(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "нет активных привычек" in text or "создайте первую" in text

    # ========== УДАЛЕНИЕ ПРИВЫЧКИ (строки 800-905) ==========

    @pytest.mark.asyncio
    async def test_delete_habit_start_unregistered(self, update_mock, context_mock):
        """Покрытие строк 807-815: начало удаления для незарегистрированного пользователя"""
        from telegram_bot.bot import ConversationHandler, delete_habit_start

        update_mock.effective_chat.id = 999999999

        result = await delete_habit_start(update_mock, context_mock)

        assert result == ConversationHandler.END
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "зарегистрируйтесь" in text or "start" in text

    @pytest.mark.asyncio
    async def test_delete_habit_start_empty(self, db_user, update_mock, context_mock):
        """Покрытие строк 816-824: отсутствие привычек для удаления"""
        from telegram_bot.bot import ConversationHandler, delete_habit_start

        update_mock.effective_chat.id = db_user.telegram_chat_id

        result = await delete_habit_start(update_mock, context_mock)

        assert result == ConversationHandler.END
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "нет привычек" in text or "создайте привычку" in text

    @pytest.mark.asyncio
    async def test_select_habit_to_delete_invalid_number(self, db_user, update_mock, context_mock):
        """Покрытие строк 846-854: неверный номер привычки"""
        from telegram_bot.bot import SELECT_HABIT_TO_DELETE, delete_habit_start, select_habit_to_delete

        update_mock.effective_chat.id = db_user.telegram_chat_id

        # Создаём привычку
        @sync_to_async
        def create_habit():
            from habits.models import Habit

            return Habit.objects.create(
                user=db_user,
                place="дома",
                time=time_type(8, 0),
                action="выпить чай",
                is_pleasant=False,
                duration=60,
                periodicity=1,
            )

        await create_habit()

        await delete_habit_start(update_mock, context_mock)

        # Неверный номер (больше количества привычек)
        update_mock.message.text = "999"
        result = await select_habit_to_delete(update_mock, context_mock)

        assert result == SELECT_HABIT_TO_DELETE
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "неверный ввод" in text or "число от 1" in text

    @pytest.mark.asyncio
    async def test_confirm_delete_cancel(self, update_mock, context_mock):
        """Покрытие строк 875-880: отмена удаления"""
        from telegram_bot.bot import ConversationHandler, confirm_delete

        context_mock.user_data["habit_to_delete"] = {"id": 1, "action": "тест"}
        update_mock.message.text = "Отмена"

        result = await confirm_delete(update_mock, context_mock)

        assert result == ConversationHandler.END
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "отменено" in text

    # ========== СТАТИСТИКА (строки 910-935) ==========

    @pytest.mark.asyncio
    async def test_show_statistics_empty(self, db_user, update_mock, context_mock):
        """Покрытие строк 923-928: пустая статистика"""
        from telegram_bot.bot import show_statistics

        update_mock.effective_chat.id = db_user.telegram_chat_id

        await show_statistics(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "нет статистики" in text or "создайте первую" in text
