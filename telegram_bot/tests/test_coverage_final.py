from datetime import time as time_type
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from telegram import ReplyKeyboardRemove

pytestmark = pytest.mark.django_db


class TestCoverageFinal:
    """Финальные тесты для достижения 85%+ покрытия"""

    @pytest.mark.asyncio
    async def test_bind_user_to_chat_success(self, db_user):
        """Покрытие строк 95-97: успешная привязка пользователя к chat_id"""
        from telegram_bot.bot import bind_user_to_chat

        # Создаём пользователя БЕЗ привязки
        @sync_to_async
        def create_unbound_user():
            from django.contrib.auth import get_user_model

            User = get_user_model()
            return User.objects.create_user(
                username="unbound_test_user", email="unbound@example.com", password="TestPass123!"
            )

        unbound_user = await create_unbound_user()

        # Привязываем к новому chat_id
        new_chat_id = 999888777
        bound_user = await bind_user_to_chat(unbound_user.username, new_chat_id)

        assert bound_user is not None
        assert bound_user.telegram_chat_id == new_chat_id
        assert bound_user.username == unbound_user.username

    @pytest.mark.asyncio
    async def test_get_user_habits_data_full(self, db_user):
        """Покрытие строк 111-131: формирование данных привычек с связанными объектами"""
        from habits.models import Habit
        from telegram_bot.bot import get_user_habits_data

        # Создаём приятную привычку
        @sync_to_async
        def create_pleasant_habit():
            return Habit.objects.create(
                user=db_user,
                place="дома",
                time=time_type(8, 0),
                action="выпить чай",
                is_pleasant=True,
                duration=60,
                periodicity=1,
            )

        pleasant = await create_pleasant_habit()

        # Создаём полезную привычку со связанной приятной
        @sync_to_async
        def create_useful_habit():
            return Habit.objects.create(
                user=db_user,
                place="спортзал",
                time=time_type(19, 0),
                action="сделать 10 отжиманий",
                is_pleasant=False,
                related_habit=pleasant,
                duration=120,
                periodicity=1,
                is_public=True,
            )

        await create_useful_habit()

        # Получаем данные
        habits_data = await get_user_habits_data(db_user.telegram_chat_id)

        assert len(habits_data) == 2

        # Проверяем структуру данных приятной привычки
        pleasant_data = [h for h in habits_data if h["is_pleasant"]][0]
        assert pleasant_data["id"] == pleasant.id
        assert pleasant_data["action"] == "выпить чай"
        assert pleasant_data["related_habit"] is None

        # Проверяем структуру данных полезной привычки
        useful_data = [h for h in habits_data if not h["is_pleasant"]][0]
        assert useful_data["related_habit"] is not None
        assert useful_data["related_habit"]["id"] == pleasant.id
        assert useful_data["related_habit"]["action"] == "выпить чай"
        assert useful_data["is_public"] is True

    @pytest.mark.asyncio
    async def test_create_habit_validation_full(self, db_user):
        """Покрытие строк 144-174: полная валидация бизнес-правил при создании привычки"""
        from telegram_bot.bot import create_habit

        # 1. Валидация: нельзя указать одновременно вознаграждение и связанную привычку
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

        # 2. Валидация: связанная привычка должна быть приятной
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

        # 3. Валидация: у приятной привычки не может быть вознаграждения
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

        # 4. Валидация: время выполнения не должно превышать 120 секунд
        with pytest.raises(ValueError, match="Время выполнения не должно превышать 120 секунд"):
            await create_habit(
                user_id=db_user.id, place="дома", time=time_type(8, 0), action="тест", duration=121, periodicity=1
            )

        # 5. Валидация: периодичность должна быть от 1 до 7 дней
        with pytest.raises(ValueError, match="Периодичность должна быть от 1 до 7 дней"):
            await create_habit(user_id=db_user.id, place="дома", time=time_type(8, 0), action="тест", periodicity=8)

    @pytest.mark.asyncio
    async def test_start_registered_user_full(self, db_user, update_mock, context_mock):
        """Покрытие строк 210-237: полный ответ /start для зарегистрированного пользователя"""
        from telegram_bot.bot import start

        update_mock.effective_chat.id = db_user.telegram_chat_id

        await start(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        call_kwargs = update_mock.message.reply_text.call_args[1]

        # Проверяем структуру ответа
        assert call_kwargs.get("parse_mode") == "HTML"
        assert "reply_markup" in call_kwargs

        # Проверяем содержание сообщения
        message = update_mock.message.reply_text.call_args[0][0]
        assert db_user.username in message
        assert "👋 Привет" in message or "👋" in message
        assert "/create" in message
        assert "/habits" in message
        assert "/delete" in message
        assert "/stats" in message

    @pytest.mark.asyncio
    async def test_register_start_already_registered(self, db_user, update_mock, context_mock):
        """Покрытие строк 271-275: попытка регистрации уже зарегистрированного пользователя"""
        from telegram_bot.bot import ConversationHandler, register_start

        update_mock.effective_chat.id = db_user.telegram_chat_id

        result = await register_start(update_mock, context_mock)

        assert result == ConversationHandler.END
        assert update_mock.message.reply_text.called

        # Проверяем сообщение об ошибке
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "уже зарегистрированы" in text or "уже зарегистр" in text

        # Проверяем, что клавиатура удалена
        call_kwargs = update_mock.message.reply_text.call_args[1]
        assert "reply_markup" in call_kwargs
        assert isinstance(call_kwargs["reply_markup"], ReplyKeyboardRemove)

    @pytest.mark.asyncio
    async def test_register_username_validation(self, update_mock, context_mock):
        """Покрытие строк 285, 296, 299-302, 309-315: полная валидация имени пользователя"""
        from telegram_bot.bot import register_username

        # Тест 1: короткое имя (< 3 символов)
        update_mock.message.text = "ab"
        context_mock.user_data = {}

        result = await register_username(update_mock, context_mock)
        assert result == 0  # USERNAME статус
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "3 символ" in text or "минимум" in text

        # Тест 2: недопустимые спецсимволы
        update_mock.message.text = "user@name#"
        context_mock.user_data = {}

        result = await register_username(update_mock, context_mock)
        assert result == 0  # USERNAME статус
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "только буквы" in text or "цифры" in text or "@" in text

        # Тест 3: имя уже занято (мокаем проверку)
        update_mock.message.text = "testuser_bot"
        context_mock.user_data = {}

        with patch("telegram_bot.bot.user_exists_by_username", return_value=True):
            result = await register_username(update_mock, context_mock)
            assert result == 0  # USERNAME статус
            text = update_mock.message.reply_text.call_args[0][0].lower()
            assert "занят" in text or "уже существует" in text

    @pytest.mark.asyncio
    async def test_bind_account_already_bound(self, db_user, update_mock, context_mock):
        """Покрытие строк 396-412: попытка привязки уже привязанного аккаунта"""
        from telegram_bot.bot import ConversationHandler, bind_account

        update_mock.effective_chat.id = db_user.telegram_chat_id

        result = await bind_account(update_mock, context_mock)

        assert result == ConversationHandler.END
        assert update_mock.message.reply_text.called

        # Проверяем сообщение об ошибке
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "уже привязан" in text

        # Проверяем, что клавиатура удалена
        call_kwargs = update_mock.message.reply_text.call_args[1]
        assert "reply_markup" in call_kwargs
        assert isinstance(call_kwargs["reply_markup"], ReplyKeyboardRemove)

    @pytest.mark.asyncio
    async def test_create_habit_start_unregistered(self, update_mock, context_mock):
        """Покрытие строк 449-460: начало создания привычки для незарегистрированного пользователя"""
        from telegram_bot.bot import ConversationHandler, create_habit_start

        # Chat ID без привязанного пользователя
        update_mock.effective_chat.id = 999999999

        result = await create_habit_start(update_mock, context_mock)

        assert result == ConversationHandler.END
        assert update_mock.message.reply_text.called

        # Проверяем сообщение о необходимости регистрации
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "зарегистрируйтесь" in text or "start" in text

    @pytest.mark.asyncio
    async def test_habit_place_validation(self, db_user, update_mock, context_mock):
        """Покрытие строк 471, 474-479: валидация места выполнения привычки"""
        from telegram_bot.bot import PLACE, TIME, create_habit_start, habit_place

        # Начинаем создание привычки
        update_mock.effective_chat.id = db_user.telegram_chat_id
        await create_habit_start(update_mock, context_mock)

        # Тест 1: короткое место (< 2 символов) → должен вернуться статус PLACE
        update_mock.message.text = "a"

        result = await habit_place(update_mock, context_mock)
        assert result == PLACE
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "2 символ" in text or "минимум" in text

        # Тест 2: валидное место → должен вернуться статус TIME
        update_mock.message.text = "дома"

        result = await habit_place(update_mock, context_mock)
        assert result == TIME
        assert context_mock.user_data["habit"]["place"] == "дома"

        # ИСПРАВЛЕНО: Проверяем реальные ключевые слова из сообщения бота
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "во сколько" in text or "формат" in text or "чч:мм" in text

    @pytest.mark.asyncio
    async def test_habit_time_validation(self, db_user, update_mock, context_mock):
        """Покрытие строк 489, 499, 506: валидация времени выполнения привычки"""
        from telegram_bot.bot import ACTION, TIME, create_habit_start, habit_place, habit_time

        # Начинаем создание привычки
        update_mock.effective_chat.id = db_user.telegram_chat_id
        await create_habit_start(update_mock, context_mock)
        update_mock.message.text = "дома"
        await habit_place(update_mock, context_mock)

        # Тест 1: неверный формат (без двоеточия)
        update_mock.message.text = "0800"

        result = await habit_time(update_mock, context_mock)
        assert result == TIME
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "неверный формат" in text or "пример" in text

        # Тест 2: неверные значения (25 часов)
        update_mock.message.text = "25:00"

        result = await habit_time(update_mock, context_mock)
        assert result == TIME
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "неверный формат" in text

        # Тест 3: валидное время
        update_mock.message.text = "08:30"

        result = await habit_time(update_mock, context_mock)
        assert result == ACTION
        assert context_mock.user_data["habit"]["time"] == time_type(8, 30)
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "действие" in text or "опишите" in text

    @pytest.mark.asyncio
    async def test_habit_action_validation(self, db_user, update_mock, context_mock):
        """Покрытие строк 517, 527: валидация действия привычки"""
        from telegram_bot.bot import (
            ACTION,
            IS_PLEASANT,
            create_habit_start,
            habit_action,
            habit_place,
            habit_time,
        )

        # Начинаем создание привычки
        update_mock.effective_chat.id = db_user.telegram_chat_id
        await create_habit_start(update_mock, context_mock)
        update_mock.message.text = "дома"
        await habit_place(update_mock, context_mock)
        update_mock.message.text = "08:00"
        await habit_time(update_mock, context_mock)

        # Тест 1: короткое действие (< 5 символов)
        update_mock.message.text = "пить"

        result = await habit_action(update_mock, context_mock)
        assert result == ACTION
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "5 символ" in text or "подробнее" in text

        # Тест 2: валидное действие
        update_mock.message.text = "выпить стакан воды"

        result = await habit_action(update_mock, context_mock)
        assert result == IS_PLEASANT
        assert context_mock.user_data["habit"]["action"] == "выпить стакан воды"
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "приятная" in text or "вознаграждение" in text

    @pytest.mark.asyncio
    async def test_show_habits_with_data(self, db_user, update_mock, context_mock):
        """Покрытие строк 763-795: вывод списка привычек с данными"""
        from habits.models import Habit
        from telegram_bot.bot import show_habits

        # Создаём привычки
        @sync_to_async
        def create_habits():
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

        await show_habits(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        call_kwargs = update_mock.message.reply_text.call_args[1]
        assert call_kwargs.get("parse_mode") == "HTML"

        # Проверяем содержание сообщения
        message = update_mock.message.reply_text.call_args[0][0]
        assert "ваши привычки" in message.lower() or "📋" in message
        assert "выпить чай" in message
        assert "08:00" in message
        assert "спортзал" in message
        assert "отжиманий" in message
        assert "19:00" in message
        assert "приятная" in message.lower() or "✨" in message

    @pytest.mark.asyncio
    async def test_show_statistics_with_data(self, db_user, update_mock, context_mock):
        """Покрытие строк 917-935: вывод статистики с данными"""
        from habits.models import Habit
        from telegram_bot.bot import show_statistics

        # Создаём привычки
        @sync_to_async
        def create_habits():
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
        call_kwargs = update_mock.message.reply_text.call_args[1]
        assert call_kwargs.get("parse_mode") == "HTML"

        # Проверяем содержание сообщения
        message = update_mock.message.reply_text.call_args[0][0].lower()
        assert "статистика" in message
        assert "2" in message  # Всего привычек
        assert "1" in message  # Приятных и полезных
        assert "полезных" in message or "useful" in message
        assert "приятных" in message or "pleasant" in message
