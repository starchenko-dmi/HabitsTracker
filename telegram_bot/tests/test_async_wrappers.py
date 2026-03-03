from datetime import time as time_type
import pytest


pytestmark = pytest.mark.django_db  # ГЛОБАЛЬНЫЙ МАРКЕР ДЛЯ ВСЕХ ТЕСТОВ В МОДУЛЕ


class TestAsyncWrappers:
    """Тесты асинхронных обёрток для работы с БД"""

    @pytest.mark.asyncio
    async def test_get_user_by_chat_id_exists(self, db_user):
        """Проверка получения пользователя по chat_id"""
        from telegram_bot.bot import get_user_by_chat_id

        # Проверяем, что у пользователя установлен telegram_chat_id
        assert db_user.telegram_chat_id == 123456789

        user = await get_user_by_chat_id(db_user.telegram_chat_id)

        assert user is not None
        assert user.username == db_user.username
        assert user.telegram_chat_id == db_user.telegram_chat_id

    @pytest.mark.asyncio
    async def test_get_user_by_chat_id_not_exists(self):
        from telegram_bot.bot import get_user_by_chat_id

        user = await get_user_by_chat_id(999999999)
        assert user is None

    @pytest.mark.asyncio
    async def test_user_exists_by_chat_id(self, db_user):
        from telegram_bot.bot import user_exists_by_chat_id

        exists = await user_exists_by_chat_id(db_user.telegram_chat_id)
        assert exists is True

    @pytest.mark.asyncio
    async def test_user_exists_by_username(self, db_user):
        from telegram_bot.bot import user_exists_by_username

        exists = await user_exists_by_username(db_user.username)
        assert exists is True

    @pytest.mark.asyncio
    async def test_user_exists_by_email(self, db_user):
        from telegram_bot.bot import user_exists_by_email

        exists = await user_exists_by_email(db_user.email)
        assert exists is True

    @pytest.mark.asyncio
    async def test_create_user(self, update_mock, context_mock):
        from telegram_bot.bot import create_user

        user = await create_user(
            username="newuser", email="new@example.com", password="NewPass123!", chat_id=987654321
        )
        assert user is not None
        assert user.username == "newuser"
        assert user.telegram_chat_id == 987654321

    @pytest.mark.asyncio
    async def test_bind_user_to_chat(self):
        """Проверка привязки пользователя к chat_id"""
        from asgiref.sync import sync_to_async
        from django.contrib.auth import get_user_model

        from telegram_bot.bot import bind_user_to_chat

        User = get_user_model()

        # Создаём пользователя БЕЗ привязки к Telegram (асинхронно!)
        @sync_to_async
        def create_unbound_user():
            return User.objects.create_user(
                username="unbound_user", email="unbound@example.com", password="TestPass123!"
            )

        unbound_user = await create_unbound_user()

        # Привязываем пользователя к новому chat_id
        user = await bind_user_to_chat(unbound_user.username, 111222333)

        assert user is not None
        assert user.telegram_chat_id == 111222333
        assert user.username == unbound_user.username

    @pytest.mark.asyncio
    async def test_get_user_habits_data_empty(self, db_user):
        from telegram_bot.bot import get_user_habits_data

        habits = await get_user_habits_data(db_user.telegram_chat_id)
        assert len(habits) == 0

    @pytest.mark.asyncio
    async def test_get_user_habits_data_with_habits(self, db_user):
        from datetime import time as time_type

        from asgiref.sync import sync_to_async
        from telegram_bot.bot import get_user_habits_data

        # Создаём приятную привычку
        @sync_to_async
        def create_pleasant_habit():
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

        # Создаём полезную привычку
        @sync_to_async
        def create_useful_habit():
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

        # Создаём привычки
        await create_pleasant_habit()
        await create_useful_habit()

        # Получаем данные привычек
        habits = await get_user_habits_data(db_user.telegram_chat_id)

        assert len(habits) == 2
        assert any(h["is_pleasant"] for h in habits)
        assert any(not h["is_pleasant"] for h in habits)

    @pytest.mark.asyncio
    async def test_create_habit_pleasant(self, db_user):
        from telegram_bot.bot import create_habit

        habit = await create_habit(
            user_id=db_user.id,
            place="дома",
            time=time_type(7, 30),
            action="медитировать 5 минут",
            is_pleasant=True,
            duration=60,
            periodicity=1,
        )
        assert habit is not None
        assert habit.is_pleasant is True
        assert habit.action == "медитировать 5 минут"

    @pytest.mark.asyncio
    async def test_create_habit_useful_with_reward(self, db_user):
        from telegram_bot.bot import create_habit

        habit = await create_habit(
            user_id=db_user.id,
            place="офис",
            time=time_type(12, 0),
            action="сделать перерыв",
            is_pleasant=False,
            reward="выпить кофе",
            duration=120,
            periodicity=1,
        )
        assert habit is not None
        assert habit.reward == "выпить кофе"
        assert habit.related_habit is None

    @pytest.mark.asyncio
    async def test_create_habit_useful_with_related(self, db_user):
        from datetime import time as time_type

        from asgiref.sync import sync_to_async
        from telegram_bot.bot import create_habit

        # Создаём приятную привычку (предварительное условие для теста)
        @sync_to_async
        def create_pleasant_habit():
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

        pleasant_habit = await create_pleasant_habit()

        # Создаём полезную привычку со связанной приятной привычкой
        habit = await create_habit(
            user_id=db_user.id,
            place="дома",
            time=time_type(20, 0),
            action="прочитать 10 страниц",
            is_pleasant=False,
            related_habit_id=pleasant_habit.id,
            duration=120,
            periodicity=1,
        )

        assert habit is not None
        assert habit.related_habit_id == pleasant_habit.id
        assert habit.is_pleasant is False

    @pytest.mark.asyncio
    async def test_create_habit_validation_duration(self, db_user):
        from telegram_bot.bot import create_habit

        with pytest.raises(ValueError, match="Время выполнения не должно превышать 120 секунд"):
            await create_habit(
                user_id=db_user.id,
                place="дома",
                time=time_type(8, 0),
                action="долгое действие",
                duration=121,
                periodicity=1,
            )

    @pytest.mark.asyncio
    async def test_create_habit_validation_periodicity(self, db_user):
        from telegram_bot.bot import create_habit

        with pytest.raises(ValueError, match="Периодичность должна быть от 1 до 7 дней"):
            await create_habit(
                user_id=db_user.id, place="дома", time=time_type(8, 0), action="редкое действие", periodicity=8
            )

    @pytest.mark.asyncio
    async def test_delete_habit(self, db_user):
        """Проверка удаления привычки"""
        from datetime import time as time_type

        from telegram_bot.bot import create_habit, delete_habit

        # Создаём привычку
        habit = await create_habit(
            user_id=db_user.id,
            place="дома",
            time=time_type(8, 0),
            action="выпить чай",
            is_pleasant=True,
            duration=60,
            periodicity=1,
        )

        # Удаляем привычку
        success = await delete_habit(habit.id, db_user.id)

        assert success is True

    @pytest.mark.asyncio
    async def test_delete_habit_wrong_user(self, db_user):
        """Проверка удаления привычки чужим пользователем"""
        from datetime import time as time_type

        from asgiref.sync import sync_to_async
        from django.contrib.auth import get_user_model

        from telegram_bot.bot import create_habit, delete_habit

        User = get_user_model()

        # Создаём привычку для первого пользователя (владельца)
        # ВНИМАНИЕ: create_habit уже асинхронная, вызываем напрямую!
        habit = await create_habit(
            user_id=db_user.id,
            place="спортзал",
            time=time_type(19, 0),
            action="сделать 10 отжиманий",
            is_pleasant=False,
            reward="посмотреть серию",
            duration=120,
            periodicity=1,
        )

        # Создаём второго пользователя (не владельца привычки)
        @sync_to_async
        def create_other_user():
            return User.objects.create_user(username="other_user", email="other@example.com", password="OtherPass123!")

        other_user = await create_other_user()

        # Пытаемся удалить привычку другим пользователем
        success = await delete_habit(habit.id, other_user.id)

        assert success is False

    @pytest.mark.asyncio
    async def test_get_habit_statistics(self, db_user):
        """Проверка получения статистики привычек"""
        from datetime import time as time_type

        from asgiref.sync import sync_to_async

        from telegram_bot.bot import get_habit_statistics

        # Создаём приятную привычку
        @sync_to_async
        def create_pleasant_habit():
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

        # Создаём полезную привычку
        @sync_to_async
        def create_useful_habit():
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

        # Создаём привычки
        await create_pleasant_habit()
        await create_useful_habit()

        # Получаем статистику
        stats = await get_habit_statistics(db_user.telegram_chat_id)

        assert stats is not None
        assert stats["total_habits"] == 2
        assert stats["pleasant_habits"] == 1
        assert stats["useful_habits"] == 1

    @pytest.mark.asyncio
    async def test_get_pleasant_habits(self, db_user):
        """Проверка получения приятных привычек"""
        from datetime import time as time_type

        from asgiref.sync import sync_to_async
        from telegram_bot.bot import get_user_habits_data

        # Создаём смесь приятных и полезных привычек
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

        pleasant = [h for h in habits if h["is_pleasant"]]
        useful = [h for h in habits if not h["is_pleasant"]]

        assert len(pleasant) == 1
        assert len(useful) == 1
