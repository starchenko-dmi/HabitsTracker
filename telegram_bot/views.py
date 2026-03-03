import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes

from telegram_bot.utils import get_bot

logger = logging.getLogger(__name__)

# Инициализация приложения бота
application = None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    message = (
        f"Привет, {user.first_name}! 👋\n\n"
        f"Я бот для трекера привычек 📱\n"
        f"Я буду напоминать тебе о твоих полезных привычках!\n\n"
        f"Твой ID чата: <code>{user.id}</code>\n"
        f"Сообщи этот ID администратору, чтобы привязать твой аккаунт."
    )
    await update.message.reply_html(message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    message = (
        "📖 <b>Инструкция по использованию</b>\n\n"
        "/start - Начать работу с ботом и получить свой ID чата\n"
        "/help - Показать эту справку\n"
        "/habits - Показать список твоих привычек\n"
        "/stats - Показать статистику выполнения привычек"
    )
    await update.message.reply_html(message)


async def habits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /habits"""
    from habits.models import Habit
    from users.models import User

    user = update.effective_user

    try:
        # Находим пользователя по telegram_chat_id
        db_user = User.objects.get(telegram_chat_id=user.id)
        habits = Habit.objects.user_habits(db_user).filter(is_pleasant=False)

        if habits.exists():
            message = "📋 <b>Твои привычки:</b>\n\n"
            for habit in habits:
                message += (
                    f"• {habit.action}\n"
                    f"  📍 Место: {habit.place}\n"
                    f"  ⏰ Время: {habit.time.strftime('%H:%M')}\n"
                    f"  🔄 Периодичность: каждые {habit.periodicity} дн.\n"
                    f"  ⏱️ Длительность: {habit.duration} сек.\n"
                )
                if habit.reward:
                    message += f"  🎁 Вознаграждение: {habit.reward}\n"
                if habit.related_habit:
                    message += f"  🔗 Связанная привычка: {habit.related_habit.action}\n"
                message += "\n"
        else:
            message = "У тебя пока нет привычек. Добавь их через веб-приложение!"

    except User.DoesNotExist:
        message = "⚠️ Твой аккаунт не привязан к боту.\n" f"Сообщи администратору свой ID чата: <code>{user.id}</code>"

    await update.message.reply_html(message)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /stats"""
    from habits.models import Habit
    from users.models import User

    user = update.effective_user

    try:
        db_user = User.objects.get(telegram_chat_id=user.id)
        total_habits = Habit.objects.user_habits(db_user).count()
        pleasant_habits = Habit.objects.user_habits(db_user).pleasant().count()
        useful_habits = Habit.objects.user_habits(db_user).useful().count()

        message = (
            "📊 <b>Статистика твоих привычек:</b>\n\n"
            f"Всего привычек: {total_habits}\n"
            f"Полезных привычек: {useful_habits}\n"
            f"Приятных привычек: {pleasant_habits}\n"
        )

        await update.message.reply_html(message)

    except User.DoesNotExist:
        message = "⚠️ Твой аккаунт не привязан к боту.\n" f"Сообщи администратору свой ID чата: <code>{user.id}</code>"
        await update.message.reply_html(message)


@csrf_exempt
@require_http_methods(["POST"])
def telegram_webhook(request):
    """
    Вебхук для получения обновлений от Telegram.
    Telegram будет отправлять сюда все сообщения и команды от пользователей.
    """
    global application

    if not application:
        # Инициализация приложения бота при первом запросе
        application = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()

        # Регистрация обработчиков команд
        from telegram.ext import CommandHandler

        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("habits", habits_command))
        application.add_handler(CommandHandler("stats", stats_command))

        # Инициализация приложения
        application.initialize()
        application.updater.initialize()

    try:
        # Получаем данные из запроса
        json_data = json.loads(request.body.decode("utf-8"))
        logger.info(f"Получено обновление от Telegram: {json_data}")

        # Создаем объект Update и обрабатываем его
        update = Update.de_json(json_data, application.bot)
        application.update_queue.put_nowait(update)

        return JsonResponse({"status": "ok"})

    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@require_http_methods(["GET"])
def set_webhook(request):
    """
    Установка вебхука в Telegram.
    Нужно вызвать один раз после развертывания на сервере.
    """
    bot = get_bot()
    if not bot:
        return JsonResponse({"status": "error", "message": "Bot token not configured"})

    try:
        # URL вебхука (должен быть публичным)
        webhook_url = f"{request.scheme}://{request.get_host()}/api/telegram/webhook/"

        bot.set_webhook(url=webhook_url)
        logger.info(f"Вебхук установлен: {webhook_url}")

        return JsonResponse({"status": "ok", "webhook_url": webhook_url, "bot_name": settings.TELEGRAM_BOT_NAME})

    except Exception as e:
        logger.error(f"Ошибка установки вебхука: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@require_http_methods(["GET"])
def delete_webhook(request):
    """
    Удаление вебхука из Telegram.
    """
    bot = get_bot()
    if not bot:
        return JsonResponse({"status": "error", "message": "Bot token not configured"})

    try:
        bot.delete_webhook()
        logger.info("Вебхук удален")

        return JsonResponse({"status": "ok", "message": "Webhook deleted"})

    except Exception as e:
        logger.error(f"Ошибка удаления вебхука: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
