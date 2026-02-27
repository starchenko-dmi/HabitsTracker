import logging

from django.conf import settings
from telegram import Bot

logger = logging.getLogger(__name__)


def get_bot():
    """Получение экземпляра бота"""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не настроен в настройках")
        return None
    return Bot(token=settings.TELEGRAM_BOT_TOKEN)


def set_commands():
    """
    Установка команд бота в меню Telegram.
    Вызывается один раз после настройки бота.
    """
    bot = get_bot()
    if not bot:
        return False

    from telegram import BotCommand

    commands = [
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("help", "Показать справку"),
        BotCommand("habits", "Показать мои привычки"),
        BotCommand("stats", "Показать статистику"),
    ]

    try:
        bot.set_my_commands(commands)
        logger.info("Команды бота установлены")
        return True
    except Exception as e:
        logger.error(f"Ошибка установки команд бота: {e}")
        return False
