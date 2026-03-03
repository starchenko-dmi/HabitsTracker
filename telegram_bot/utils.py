import logging

import requests
from django.conf import settings
from telegram import Bot, BotCommand

logger = logging.getLogger(__name__)


def get_bot():
    """Получение экземпляра бота"""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не настроен в настройках")
        return None
    return Bot(token=settings.TELEGRAM_BOT_TOKEN)


logger = logging.getLogger(__name__)


def send_message(chat_id, text):
    """
    Отправка сообщения пользователю в Telegram через прямой HTTP-запрос.
    Не зависит от основного цикла бота — работает из задач Celery.

    Args:
        chat_id: ID чата пользователя
        text: Текст сообщения

    Returns:
        bool: True если сообщение отправлено успешно
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не настроен в настройках")
        return False

    if not chat_id:
        logger.warning("Попытка отправить сообщение без chat_id")
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_notification": False,  # Отправляем с уведомлением
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()

        if response.status_code == 200 and result.get("ok"):
            logger.info(f"✅ Сообщение успешно отправлено в чат {chat_id}")
            return True
        else:
            error_msg = result.get("description", "Неизвестная ошибка")
            logger.error(f"❌ Ошибка отправки сообщения в чат {chat_id}: {error_msg} (код {response.status_code})")
            return False

    except requests.exceptions.Timeout:
        logger.error(f"❌ Таймаут при отправке сообщения в чат {chat_id}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Ошибка сети при отправке сообщения в чат {chat_id}: {e}")
        return False
    except Exception as e:
        logger.exception(f"🔥 Неожиданная ошибка при отправке сообщения в чат {chat_id}: {e}")
        return False


def set_commands():
    """
    Установка команд бота в меню Telegram.
    Вызывается один раз после настройки бота.
    """
    bot = get_bot()
    if not bot:
        return False

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
