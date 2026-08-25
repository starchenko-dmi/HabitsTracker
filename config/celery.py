import os
from pathlib import Path

from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

# Загружаем переменные из .env файла (ДО любых других операций)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Устанавливаем модуль настроек Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Создаём экземпляр Celery приложения
app = Celery("habits_tracker")

# Загружаем конфигурацию из settings.py
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автоматически загружаем задачи из приложений Django
app.autodiscover_tasks()

# Настройка периодических задач (Celery Beat)
app.conf.beat_schedule = {
    # 🔔 ЕЖЕМИНУТНАЯ проверка напоминаний (без указания очереди — используется очередь по умолчанию "celery")
    "send-habit-reminders-every-minute": {
        "task": "habits.tasks.send_habit_reminders",
        "schedule": crontab(minute="*"),  # Каждую минуту
    },
    # 🧪 Тестовая задача (каждые 5 минут)
    "test-periodic-task": {
        "task": "habits.tasks.test_periodic_task",
        "schedule": crontab(minute="*/5"),
    },
}

# Настройка часового пояса (должен совпадать с TIME_ZONE в settings.py)
app.conf.timezone = os.environ.get("TIME_ZONE", "Asia/Novosibirsk")


@app.task(bind=True)
def debug_task(self):
    """Отладочная задача для тестирования Celery"""
    print(f"Запрос: {self.request!r}")
