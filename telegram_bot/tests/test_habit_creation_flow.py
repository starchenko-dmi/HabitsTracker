from datetime import time as time_type
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.django_db


class TestHabitCreationFlow:
    """Тесты для этапов создания привычки: связанная привычка и вознаграждение"""

    @pytest.fixture(autouse=True)
    def setup_fixtures(self, db_user, update_mock, context_mock):
        """Настройка фикстур для всех тестов"""
        self.db_user = db_user
        self.update_mock = update_mock
        self.context_mock = context_mock

        # Гарантируем корректные моки для асинхронных вызовов
        self.update_mock.message = AsyncMock()
        self.update_mock.message.reply_text = AsyncMock(return_value=None)
        self.update_mock.message.text = "Тест"

        # Инициализируем контекст для создания привычки
        self.context_mock.user_data["habit"] = {
            "user_id": db_user.id,
            "place": "дома",
            "time": time_type(8, 0),
            "action": "выпить стакан воды",
            "is_pleasant": False,
        }

    # ========== ТЕСТЫ ДЛЯ habit_related_habit ==========

    @pytest.mark.asyncio
    async def test_habit_related_habit_skip(self, update_mock, context_mock):
        """Проверка выбора 'пропустить' при выборе связанной привычки"""
        from telegram_bot.bot import REWARD, habit_related_habit

        # Подготавливаем контекст
        context_mock.user_data["habit"]["pleasant_habits_list"] = [
            {"id": 1, "action": "выпить чай"},
            {"id": 2, "action": "посмотреть видео"},
        ]

        # Пользователь выбирает "пропустить"
        update_mock.message.text = "Пропустить"

        result = await habit_related_habit(update_mock, context_mock)

        # Проверяем результат
        assert result == REWARD
        assert context_mock.user_data["habit"]["related_habit_id"] is None
        assert update_mock.message.reply_text.called

        # Проверяем текст сообщения
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "шаг 6" in text
        assert "вознаграждение" in text

    @pytest.mark.asyncio
    async def test_habit_related_habit_invalid_format(self, update_mock, context_mock):
        """Проверка обработки неверного формата ввода"""
        from telegram_bot.bot import RELATED_HABIT, habit_related_habit

        # Подготавливаем контекст
        pleasant_habits = [{"id": 1, "action": "выпить чай"}]
        context_mock.user_data["habit"]["pleasant_habits_list"] = pleasant_habits

        # Пользователь вводит текст вместо номера
        update_mock.message.text = "неправильный ввод"

        result = await habit_related_habit(update_mock, context_mock)

        # Проверяем результат
        assert result == RELATED_HABIT
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "неверный выбор" in text

    # ========== ТЕСТЫ ДЛЯ habit_reward ==========

    @pytest.mark.asyncio
    async def test_habit_reward_too_short(self, update_mock, context_mock):
        """Проверка обработки слишком короткого вознаграждения"""
        from telegram_bot.bot import REWARD, habit_reward

        # Пользователь вводит вознаграждение короче 3 символов
        update_mock.message.text = "ок"

        result = await habit_reward(update_mock, context_mock)

        # Проверяем результат
        assert result == REWARD
        assert update_mock.message.reply_text.called

        # Проверяем текст сообщения об ошибке
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "вознаграждение должно быть не менее 3 символов" in text or "3 символ" in text

    @pytest.mark.asyncio
    async def test_habit_reward_empty(self, update_mock, context_mock):
        """Проверка обработки пустого вознаграждения"""
        from telegram_bot.bot import REWARD, habit_reward

        # Пользователь вводит пустую строку
        update_mock.message.text = "  "

        result = await habit_reward(update_mock, context_mock)

        # Проверяем результат
        assert result == REWARD
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "вознаграждение должно быть не менее 3 символов" in text

    @pytest.mark.asyncio
    async def test_habit_reward_exact_min_length(self, update_mock, context_mock):
        """Проверка вознаграждения ровно 3 символа (минимальная длина)"""
        from telegram_bot.bot import DURATION, habit_reward

        # Пользователь вводит вознаграждение ровно 3 символа
        update_mock.message.text = "ок!"

        result = await habit_reward(update_mock, context_mock)

        # Проверяем результат
        assert result == DURATION
        assert context_mock.user_data["habit"]["reward"] == "ок!"
        assert update_mock.message.reply_text.called

    @pytest.mark.asyncio
    async def test_habit_reward_with_special_chars(self, update_mock, context_mock):
        """Проверка вознаграждения со спецсимволами"""
        from telegram_bot.bot import DURATION, habit_reward

        # Пользователь вводит вознаграждение со спецсимволами
        update_mock.message.text = "☕️ выпить кофе"

        result = await habit_reward(update_mock, context_mock)

        # Проверяем результат
        assert result == DURATION
        assert context_mock.user_data["habit"]["reward"] == "☕️ выпить кофе"
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "☕️" in text or "выпить кофе" in text
