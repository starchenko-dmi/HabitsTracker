from datetime import time as time_type

import pytest


pytestmark = pytest.mark.django_db


class TestAsyncWrappersExtra:
    """Дополнительные тесты асинхронных обёрток"""

    @pytest.mark.asyncio
    async def test_get_user_by_chat_id_not_exists(self):
        """Проверка получения несуществующего пользователя"""
        from telegram_bot.bot import get_user_by_chat_id

        user = await get_user_by_chat_id(999999999)
        assert user is None

    @pytest.mark.asyncio
    async def test_user_exists_by_chat_id_false(self):
        """Проверка несуществующего chat_id"""
        from telegram_bot.bot import user_exists_by_chat_id

        exists = await user_exists_by_chat_id(999999999)
        assert exists is False

    @pytest.mark.asyncio
    async def test_bind_user_to_chat_not_found(self):
        """Проверка привязки несуществующего пользователя"""
        from telegram_bot.bot import bind_user_to_chat

        user = await bind_user_to_chat("nonexistent_user", 111222333)
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_habits_data_empty(self, db_user):
        """Проверка получения пустого списка привычек"""
        from telegram_bot.bot import get_user_habits_data

        habits = await get_user_habits_data(db_user.telegram_chat_id)
        assert len(habits) == 0

    @pytest.mark.asyncio
    async def test_create_habit_validation_reward_and_related(self, db_user):
        """Проверка валидации одновременного указания вознаграждения и связанной привычки"""
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
    async def test_create_habit_validation_duration_exceeded(self, db_user):
        """Проверка валидации превышения времени выполнения"""
        from telegram_bot.bot import create_habit

        with pytest.raises(ValueError, match="Время выполнения не должно превышать 120 секунд"):
            await create_habit(
                user_id=db_user.id, place="дома", time=time_type(8, 0), action="тест", duration=121, periodicity=1
            )

    @pytest.mark.asyncio
    async def test_create_habit_validation_periodicity_low(self, db_user):
        """Проверка валидации низкой периодичности"""
        from telegram_bot.bot import create_habit

        with pytest.raises(ValueError, match="Периодичность должна быть от 1 до 7 дней"):
            await create_habit(user_id=db_user.id, place="дома", time=time_type(8, 0), action="тест", periodicity=0)

    @pytest.mark.asyncio
    async def test_create_habit_validation_periodicity_high(self, db_user):
        """Проверка валидации высокой периодичности"""
        from telegram_bot.bot import create_habit

        with pytest.raises(ValueError, match="Периодичность должна быть от 1 до 7 дней"):
            await create_habit(user_id=db_user.id, place="дома", time=time_type(8, 0), action="тест", periodicity=8)

    @pytest.mark.asyncio
    async def test_create_habit_pleasant_with_reward(self, db_user):
        """Проверка валидации указания вознаграждения для приятной привычки"""
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
