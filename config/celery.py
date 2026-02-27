# config/celery.py (обновлённая версия)
import os
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

# Устанавливаем модуль настроек Django по умолчанию для программы 'celery'
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Создаём экземпляр Celery приложения
app = Celery("habits_tracker")

# Используем строку, чтобы воркеру не нужно было сериализовать
# объект конфигурации для дочерних процессов
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автоматически загружаем задачи из всех зарегистрированных приложений Django
app.autodiscover_tasks()

# Настройка периодических задач (Celery Beat)
app.conf.beat_schedule = {
    # Ежедневная отправка напоминаний о привычках
    "send-habit-reminders-daily": {
        "task": "telegram_bot.tasks.send_habit_reminders",
        "schedule": crontab(hour=7, minute=0),  # Каждый день в 07:00
        "options": {"queue": "reminders"},
    },
    # Проверка неактивных привычек раз в день
    "check-inactive-habits-daily": {
        "task": "telegram_bot.tasks.check_inactive_habits",
        "schedule": crontab(hour=9, minute=0),  # Каждый день в 09:00
        "options": {"queue": "reminders"},
    },
    # Дополнительная проверка напоминаний каждые 15 минут в течение дня
    "send-habit-reminders-every-15-minutes": {
        "task": "telegram_bot.tasks.send_habit_reminders",
        "schedule": timedelta(minutes=15),  # Каждые 15 минут
        "options": {"queue": "reminders"},
    },
    # Тестовая задача каждые 5 минут (для отладки)
    "test-periodic-task": {
        "task": "habits.tasks.test_periodic_task",
        "schedule": timedelta(minutes=5),
        "options": {"queue": "default"},
    },
    # Обновление дат следующих напоминаний каждую полночь
    "update-next-reminder-dates": {
        "task": "habits.tasks.update_next_reminder_dates",
        "schedule": crontab(hour=0, minute=0),  # Каждую полночь
        "options": {"queue": "default"},
    },
}

# Настройка часового пояса
app.conf.timezone = "Europe/Moscow"


@app.task(bind=True)
def debug_task(self):
    """Отладочная задача для тестирования Celery"""
    print(f"Запрос: {self.request!r}")
