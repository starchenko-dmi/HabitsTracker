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


def send_message(chat_id, text):
    """
    Отправка сообщения пользователю в Telegram

    Args:
        chat_id: ID чата пользователя
        text: Текст сообщения

    Returns:
        bool: True если сообщение отправлено успешно
    """
    bot = get_bot()
    if not bot:
        return False

    try:
        bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
        logger.info(f"Сообщение отправлено пользователю {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения пользователю {chat_id}: {e}")
        return False
