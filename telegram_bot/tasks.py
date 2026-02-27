import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from habits.models import Habit
from telegram_bot.bot import send_message

logger = logging.getLogger(__name__)


@shared_task
def send_habit_reminders():
    """
    Отправка напоминаний о привычках пользователям в Telegram.

    Задача выполняется ежедневно и отправляет напоминания о привычках,
    которые нужно выполнить сегодня.
    """
    logger.info("Запуск задачи отправки напоминаний о привычках")

    # Получаем текущее время
    now = timezone.now()
    current_time = now.time()

    # Получаем все привычки, которые нужно выполнить сегодня
    habits_to_remind = Habit.objects.filter(
        is_public=False,  # Только личные привычки
        user__telegram_chat_id__isnull=False,  # Только у пользователей с привязанным Telegram
    ).select_related("user")

    sent_count = 0
    failed_count = 0

    for habit in habits_to_remind:
        # Проверяем, нужно ли напоминать о привычке сегодня
        should_remind = False

        # Если привычка никогда не выполнялась, напоминаем
        if habit.last_completed is None:
            should_remind = True
        else:
            # Проверяем периодичность
            days_since_last = (now.date() - habit.last_completed).days
            if days_since_last >= habit.periodicity:
                should_remind = True

        # Проверяем время (напоминаем за 15 минут до времени привычки)
        if should_remind:
            habit_time = habit.time
            reminder_time_start = (timezone.datetime.combine(now.date(), habit_time) - timedelta(minutes=15)).time()
            reminder_time_end = habit_time

            # Проверяем, попадает ли текущее время в интервал напоминания
            if reminder_time_start <= current_time <= reminder_time_end:
                # Отправляем напоминание
                message = (
                    f"⏰ <b>Напоминание о привычке!</b>\n\n"
                    f"📝 <b>{habit.action}</b>\n"
                    f"📍 Место: {habit.place}\n"
                    f"⏰ Время: {habit_time.strftime('%H:%M')}\n"
                )

                if habit.reward:
                    message += f"\n🎁 После выполнения: {habit.reward}"
                elif habit.related_habit:
                    message += f"\n🔗 После выполнения: {habit.related_habit.action}"

                success = send_message(habit.user.telegram_chat_id, message)

                if success:
                    sent_count += 1
                    logger.info(f"Напоминание отправлено пользователю {habit.user.id}")
                else:
                    failed_count += 1
                    logger.error(f"Не удалось отправить напоминание пользователю {habit.user.id}")

    logger.info(f"Задача завершена: отправлено {sent_count}, не удалось {failed_count}")
    return {"sent": sent_count, "failed": failed_count}


@shared_task
def check_inactive_habits():
    """
    Проверка неактивных привычек.
    Отправляет уведомление, если привычка не выполнялась более 7 дней.
    """
    logger.info("Запуск задачи проверки неактивных привычек")

    # Получаем привычки, которые не выполнялись более 7 дней
    seven_days_ago = timezone.now().date() - timedelta(days=7)

    inactive_habits = Habit.objects.filter(
        last_completed__lt=seven_days_ago, user__telegram_chat_id__isnull=False
    ).select_related("user")

    for habit in inactive_habits:
        message = (
            f"⚠️ <b>Внимание!</b>\n\n"
            f'Ты не выполнял привычку <b>"{habit.action}"</b> уже более 7 дней.\n'
            f"Не забывай о своих целях! 💪"
        )
        send_message(habit.user.telegram_chat_id, message)

    logger.info(f"Проверено {inactive_habits.count()} неактивных привычек")
    return {"checked": inactive_habits.count()}
