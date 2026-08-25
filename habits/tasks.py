import logging
from celery import shared_task
from django.utils import timezone
from telegram_bot.utils import send_message
from .models import Habit

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def send_habit_reminders(self):
    """
    Ежеминутная задача: отправка напоминаний о ПОЛЕЗНЫХ привычках в назначенное время.

    Особенности:
    - Отправляются ТОЛЬКО для полезных привычек (is_pleasant=False)
    - Приятные привычки являются вознаграждением и НЕ получают напоминаний
    - Корректная работа с часовым поясом на Windows через pytz
    - Детальное логирование для диагностики
    """
    import pytz
    from django.utils import timezone

    try:
        # Получаем текущее время в UTC и преобразуем в локальный часовой пояс
        now_utc = timezone.now()
        moscow_tz = pytz.timezone("Asia/Novosibirsk")  # UTC+7
        now_local = now_utc.astimezone(moscow_tz)
        current_time = now_local.time()

        # Детальное логирование для диагностики
        logger.info(
            f"🔍 НАЧАЛО проверки напоминаний | "
            f"UTC: {now_utc.strftime('%H:%M:%S')} | "
            f"Локальное (Новосибирск): {now_local.strftime('%H:%M:%S')} | "
            f"Task ID: {self.request.id}"
        )

        # Получаем ТОЛЬКО полезные привычки с привязанным Telegram
        habits = (
            Habit.objects.filter(
                user__telegram_chat_id__isnull=False,
                is_pleasant=False,  # ← КРИТИЧЕСКИ ВАЖНО: только полезные привычки!
            )
            .select_related("user", "related_habit")
            .order_by("time")
        )

        # Фильтруем активные привычки (если поле существует)
        if hasattr(Habit, "is_active"):
            habits = habits.filter(is_active=True)

        total_habits = habits.count()
        logger.info(f"📊 Найдено полезных привычек с chat_id: {total_habits}")

        if total_habits == 0:
            logger.debug("📭 Нет полезных привычек для проверки напоминаний")
            return {"reminders_sent": 0, "timestamp": str(now_utc), "status": "no_habits"}

        # Подготовка к проверке времени
        current_seconds = current_time.hour * 3600 + current_time.minute * 60 + current_time.second
        reminders_sent = 0
        habits_checked = 0

        # Проверяем каждую привычку
        for habit in habits:
            habits_checked += 1

            # Пропускаем, если нет chat_id (на всякий случай)
            if not habit.user.telegram_chat_id:
                logger.warning(
                    f"⚠️ Привычка '{habit.action}' (ID: {habit.id}) пропущена: "
                    f"отсутствует telegram_chat_id у пользователя @{habit.user.username}"
                )
                continue

            # Рассчитываем время привычки в секундах
            habit_seconds = habit.time.hour * 3600 + habit.time.minute * 60 + habit.time.second

            # Проверяем совпадение времени с точностью ±30 секунд
            time_diff = abs(current_seconds - habit_seconds)
            if time_diff > 43200:  # Учёт перехода через полночь
                time_diff = 86400 - time_diff

            # Логируем для диагностики (каждую 5-ю привычку)
            if habits_checked % 5 == 0 or time_diff <= 60:
                logger.debug(
                    f"⏱ Проверка привычки '{habit.action}' | "
                    f"Время привычки: {habit.time.strftime('%H:%M:%S')} | "
                    f"Текущее время: {current_time.strftime('%H:%M:%S')} | "
                    f"Разница: {time_diff} сек"
                )

            # Отправляем напоминание, если время совпадает (±30 сек)
            if time_diff <= 30:
                try:
                    # Формируем сообщение
                    message = (
                        f"⏰ <b>Время выполнить привычку!</b>\n\n"
                        f"📍 <b>Место:</b> {habit.place}\n"
                        f"🎯 <b>Действие:</b> {habit.action}\n"
                        f"⏱ <b>Длительность:</b> {habit.duration} сек"
                    )

                    # Добавляем информацию о вознаграждении
                    if habit.related_habit:
                        message += f"\n\n✨ <b>После выполнения:</b> {habit.related_habit.action}"
                    elif habit.reward:
                        message += f"\n\n🎁 <b>Ваше вознаграждение:</b> {habit.reward}"

                    # Отправляем сообщение
                    success = send_message(habit.user.telegram_chat_id, message)

                    if success:
                        reminders_sent += 1
                        logger.info(
                            f"✅ Напоминание ОТПРАВЛЕНО | "
                            f"Пользователь: @{habit.user.username} (chat_id: {habit.user.telegram_chat_id}) | "
                            f"Привычка: '{habit.action}' | Время: {habit.time.strftime('%H:%M')}"
                        )
                    else:
                        logger.error(
                            f"❌ Ошибка ОТПРАВКИ напоминания | "
                            f"Пользователь: @{habit.user.username} (chat_id: {habit.user.telegram_chat_id}) | "
                            f"Привычка: '{habit.action}'"
                        )

                except Exception as e:
                    logger.exception(
                        f"🔥 Исключение при отправке напоминания для привычки '{habit.action}' "
                        f"(ID: {habit.id}, пользователь: @{habit.user.username}): {e}"
                    )
                    continue

        # Итоговый лог
        if reminders_sent > 0:
            logger.info(
                f"📤 УСПЕШНО отправлено {reminders_sent} напоминаний | "
                f"Проверено привычек: {habits_checked}/{total_habits} | "
                f"Время: {current_time.strftime('%H:%M:%S')} (Новосибирск)"
            )
        else:
            logger.debug(
                f"📭 Нет напоминаний для отправки | "
                f"Проверено привычек: {habits_checked}/{total_habits} | "
                f"Время: {current_time.strftime('%H:%M:%S')} (Новосибирск)"
            )

        return {
            "reminders_sent": reminders_sent,
            "habits_checked": habits_checked,
            "total_habits": total_habits,
            "timestamp_utc": str(now_utc),
            "timestamp_local": now_local.strftime("%Y-%m-%d %H:%M:%S %Z%z"),
            "timezone": str(moscow_tz),
            "status": "success",
        }

    except Exception as e:
        logger.exception(f"🔥 КРИТИЧЕСКАЯ ОШИБКА в задаче send_habit_reminders: {e}")
        return {"reminders_sent": 0, "error": str(e), "status": "failed"}


@shared_task
def test_periodic_task():
    """
    Тестовая периодическая задача для проверки работы Celery Beat.
    """
    current_time = timezone.now()
    logger.info(f"✅ Тестовая задача выполнена в {current_time.strftime('%H:%M:%S')}")
    return {"status": "success", "timestamp": str(current_time)}
