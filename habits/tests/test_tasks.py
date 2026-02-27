from unittest.mock import patch

import pytest

from habits.tasks import test_periodic_task as task_function
from telegram_bot.tasks import check_inactive_habits, send_habit_reminders


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
