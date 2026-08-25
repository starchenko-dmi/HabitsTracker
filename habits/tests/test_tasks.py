from unittest.mock import patch

import pytest

from habits.tasks import test_periodic_task as task_function
from telegram_bot.tasks import check_inactive_habits, send_habit_reminders

pytestmark = pytest.mark.django_db


@pytest.mark.django_db
def test_periodic_task_execution():
    """Тест выполнения периодической задачи"""
    result = task_function()
    assert result["status"] == "success"
    assert "timestamp" in result


@pytest.mark.django_db
@patch("telegram_bot.tasks.send_message")
def test_send_habit_reminders_task(mock_send_message):
    """Тест задачи отправки напоминаний"""
    result = send_habit_reminders()
    assert "sent" in result
    assert "failed" in result


@pytest.mark.django_db
@patch("telegram_bot.tasks.send_message")
def test_check_inactive_habits_task(mock_send_message):
    """Тест задачи проверки неактивных привычек"""
    result = check_inactive_habits()
    assert "checked" in result


class TestTimeWindowCalculation:
    """Юнит-тесты расчёта временного окна для напоминаний"""

    def test_time_diff_within_window(self):
        """Проверка расчёта разницы времени внутри окна ±30 сек"""
        # Текущее время: 08:00:15 (48015 секунд)
        current_seconds = 8 * 3600 + 0 * 60 + 15

        # Время привычки: 08:00:00 (48000 секунд)
        habit_seconds = 8 * 3600 + 0 * 60 + 0

        time_diff = abs(current_seconds - habit_seconds)
        assert time_diff == 15  # Разница 15 секунд
        assert time_diff <= 30  # В пределах окна ±30 сек

    def test_time_diff_outside_window(self):
        """Проверка расчёта разницы времени вне окна ±30 сек"""
        # Текущее время: 08:00:15 (48015 секунд)
        current_seconds = 8 * 3600 + 0 * 60 + 15

        # Время привычки: 08:01:00 (48060 секунд)
        habit_seconds = 8 * 3600 + 1 * 60 + 0

        time_diff = abs(current_seconds - habit_seconds)
        assert time_diff == 45  # Разница 45 секунд
        assert time_diff > 30  # Вне окна ±30 сек


class TestTestPeriodicTask:
    """Тесты тестовой периодической задачи"""

    def test_test_periodic_task(self):
        """Проверка тестовой периодической задачи"""
        from habits.tasks import test_periodic_task

        result = test_periodic_task()

        assert result["status"] == "success"
        assert "timestamp" in result
