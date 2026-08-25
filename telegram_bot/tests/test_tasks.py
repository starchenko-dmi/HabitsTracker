from datetime import time as time_type
from datetime import timedelta
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from django.utils import timezone

pytestmark = pytest.mark.django_db


class TestTasks:
    """Тесты асинхронных задач отправки напоминаний"""

    @pytest.mark.asyncio
    async def test_send_habit_reminders_no_habits(self):
        """Проверка задачи без привычек для напоминания"""
        from telegram_bot.tasks import send_habit_reminders

        with patch("telegram_bot.tasks.send_message") as mock_send:
            result = await sync_to_async(send_habit_reminders)()

            assert result["sent"] == 0
            assert result["failed"] == 0
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_habit_reminders_with_habits(self, db_user):
        """Проверка отправки напоминаний для привычек в правильное время"""
        from habits.models import Habit
        from telegram_bot.tasks import send_habit_reminders

        # Создаём привычку с временем выполнения через 10 минут от текущего времени
        now = timezone.now()
        habit_time = (now + timedelta(minutes=10)).time()

        @sync_to_async
        def create_habit():
            return Habit.objects.create(
                user=db_user,
                place="дома",
                time=habit_time,
                action="выпить стакан воды",
                is_pleasant=False,
                reward="посмотреть видео",
                duration=60,
                periodicity=1,
                last_completed=None,  # Никогда не выполнялась
            )

        await create_habit()

        with patch("telegram_bot.tasks.send_message", return_value=True) as mock_send:
            result = await sync_to_async(send_habit_reminders)()

            assert result["sent"] == 1
            assert result["failed"] == 0
            assert mock_send.called
            # Проверяем, что сообщение содержит ключевые элементы
            call_args = mock_send.call_args
            assert db_user.telegram_chat_id == call_args[0][0]
            assert "выпить стакан воды" in call_args[0][1].lower()
            assert "напоминание" in call_args[0][1].lower()

    @pytest.mark.asyncio
    async def test_send_habit_reminders_outside_time_window(self, db_user):
        """Проверка, что напоминания НЕ отправляются вне временного окна"""
        from habits.models import Habit
        from telegram_bot.tasks import send_habit_reminders

        # Создаём привычку с временем выполнения через 1 час (вне окна напоминания)
        now = timezone.now()
        habit_time = (now + timedelta(hours=1)).time()

        @sync_to_async
        def create_habit():
            return Habit.objects.create(
                user=db_user,
                place="офис",
                time=habit_time,
                action="сделать перерыв",
                is_pleasant=False,
                reward="выпить кофе",
                duration=120,
                periodicity=1,
                last_completed=None,
            )

        await create_habit()

        with patch("telegram_bot.tasks.send_message", return_value=True) as mock_send:
            result = await sync_to_async(send_habit_reminders)()

            # Напоминание не должно быть отправлено (время вне окна ±15 минут)
            assert result["sent"] == 0
            assert result["failed"] == 0
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_inactive_habits(self, db_user):
        """Проверка отправки уведомлений о неактивных привычках"""
        from habits.models import Habit
        from telegram_bot.tasks import check_inactive_habits

        # Создаём привычку, которая не выполнялась более 7 дней
        seven_days_ago = timezone.now().date() - timedelta(days=8)

        @sync_to_async
        def create_inactive_habit():
            return Habit.objects.create(
                user=db_user,
                place="спортзал",
                time=time_type(19, 0),
                action="сделать 10 отжиманий",
                is_pleasant=False,
                reward="посмотреть серию",
                duration=120,
                periodicity=1,
                last_completed=seven_days_ago,
            )

        await create_inactive_habit()

        with patch("telegram_bot.tasks.send_message", return_value=True) as mock_send:
            result = await sync_to_async(check_inactive_habits)()

            assert result["checked"] == 1
            assert mock_send.called
            call_args = mock_send.call_args
            assert "не выполнял" in call_args[0][1].lower()
            assert "7 дней" in call_args[0][1].lower()

    @pytest.mark.asyncio
    async def test_send_habit_reminders_inactive_user(self):
        """Проверка, что напоминания не отправляются пользователям без telegram_chat_id"""
        from asgiref.sync import sync_to_async
        from django.contrib.auth import get_user_model

        from habits.models import Habit
        from telegram_bot.tasks import send_habit_reminders

        User = get_user_model()

        # Создаём пользователя без привязки к Telegram
        @sync_to_async
        def create_user_without_telegram():
            return User.objects.create_user(
                username="no_telegram_user", email="no_telegram@example.com", password="TestPass123!"
            )

        user = await create_user_without_telegram()

        # Создаём привычку для этого пользователя
        @sync_to_async
        def create_habit():
            now = timezone.now()
            habit_time = (now + timedelta(minutes=5)).time()
            return Habit.objects.create(
                user=user,
                place="дома",
                time=habit_time,
                action="тестовая привычка",
                is_pleasant=False,
                duration=60,
                periodicity=1,
                last_completed=None,
            )

        await create_habit()

        with patch("telegram_bot.tasks.send_message") as mock_send:
            result = await sync_to_async(send_habit_reminders)()

            # Напоминание не должно быть отправлено (нет telegram_chat_id)
            assert result["sent"] == 0
            assert result["failed"] == 0
            mock_send.assert_not_called()
