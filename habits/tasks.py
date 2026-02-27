import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def test_periodic_task():
    """
    Тестовая периодическая задача для проверки работы Celery Beat.
    """
    current_time = timezone.now()
    logger.info(f"✅ Тестовая периодическая задача выполнена в {current_time}")
    print(f"✅ Тестовая задача выполнена в {current_time}")
    return {"status": "success", "timestamp": str(current_time)}


@shared_task
def update_next_reminder_dates():
    """
    Обновление дат следующих напоминаний для всех привычек.
    Выполняется ежедневно в полночь.
    """
    from django.utils import timezone

    from habits.models import Habit

    logger.info("Обновление дат следующих напоминаний...")

    habits = Habit.objects.all()
    updated_count = 0

    for habit in habits:
        if habit.last_completed:
            # Рассчитываем следующую дату напоминания
            next_date = habit.last_completed + timezone.timedelta(days=habit.periodicity)
            habit.next_reminder = timezone.datetime.combine(next_date, habit.time).replace(
                tzinfo=timezone.get_current_timezone()
            )
            habit.save()
            updated_count += 1

    logger.info(f"Обновлено {updated_count} привычек")
    return {"updated": updated_count}
