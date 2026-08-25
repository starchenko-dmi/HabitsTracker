import os
import sys
from pathlib import Path
import django

# Настройка Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import logging
from datetime import time as time_type

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

# Импорт модели привычки
from habits.models import Habit

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("telegram_bot.log", encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

User = get_user_model()

# Статусы для конечных автоматов
(
    USERNAME,
    EMAIL,
    PASSWORD,
    PLACE,
    TIME,
    ACTION,
    IS_PLEASANT,
    RELATED_HABIT,
    REWARD,
    DURATION,
    PERIODICITY,
    IS_PUBLIC,
    SELECT_HABIT_TO_DELETE,
    CONFIRM_DELETE,
) = range(14)


# ========== АСИНХРОННЫЕ ОБЁРТКИ ДЛЯ РАБОТЫ С БД ==========


@sync_to_async
def get_user_by_chat_id(chat_id):
    """Получить пользователя по telegram_chat_id"""
    return User.objects.filter(telegram_chat_id=chat_id).first()


@sync_to_async
def user_exists_by_chat_id(chat_id):
    """Проверить существование пользователя по chat_id"""
    return User.objects.filter(telegram_chat_id=chat_id).exists()


@sync_to_async
def user_exists_by_username(username):
    """Проверить существование пользователя по username"""
    return User.objects.filter(username=username).exists()


@sync_to_async
def user_exists_by_email(email):
    """Проверить существование пользователя по email"""
    return User.objects.filter(email=email).exists()


@sync_to_async
def create_user(username, email, password, chat_id):
    """Создать нового пользователя"""
    return User.objects.create_user(username=username, email=email, password=password, telegram_chat_id=chat_id)


@sync_to_async
def bind_user_to_chat(username, chat_id):
    """Привязать существующего пользователя к chat_id"""
    user = User.objects.filter(username=username).first()
    if user:
        user.telegram_chat_id = chat_id
        user.save()
        return user
    return None


@sync_to_async
def get_user_habits_data(chat_id):
    """
    Получить данные привычек пользователя в виде словарей для безопасного использования в асинхронном контексте
    """
    user = User.objects.filter(telegram_chat_id=chat_id).first()
    if not user:
        return []

    # Предзагружаем связанные объекты одним запросом
    habits = Habit.objects.filter(user=user).select_related("related_habit", "user").order_by("time")

    habits_data = []
    for habit in habits:
        habits_data.append(
            {
                "id": habit.id,
                "place": habit.place,
                "time": habit.time,
                "action": habit.action,
                "is_pleasant": habit.is_pleasant,
                "related_habit": (
                    {"id": habit.related_habit.id, "action": habit.related_habit.action}
                    if habit.related_habit
                    else None
                ),
                "reward": habit.reward,
                "duration": habit.duration,
                "periodicity": habit.periodicity,
                "is_public": habit.is_public,
            }
        )

    return habits_data


@sync_to_async
def create_habit(
    user_id,
    place,
    time,
    action,
    is_pleasant=False,
    related_habit_id=None,
    reward=None,
    duration=60,
    periodicity=1,
    is_public=False,
):
    """Создать новую привычку"""
    user = User.objects.get(id=user_id)

    # Валидация бизнес-правил
    if not is_pleasant:
        if reward and related_habit_id:
            raise ValueError("Нельзя указать одновременно вознаграждение и связанную привычку")
        if related_habit_id:
            related = Habit.objects.filter(id=related_habit_id, is_pleasant=True).first()
            if not related:
                raise ValueError("Связанная привычка должна быть приятной")
    else:
        if reward or related_habit_id:
            raise ValueError("У приятной привычки не может быть вознаграждения или связанной привычки")

    if duration > 120:
        raise ValueError("Время выполнения не должно превышать 120 секунд")

    if periodicity < 1 or periodicity > 7:
        raise ValueError("Периодичность должна быть от 1 до 7 дней")

    # Создаём привычку
    habit = Habit.objects.create(
        user=user,
        place=place,
        time=time,
        action=action,
        is_pleasant=is_pleasant,
        related_habit_id=related_habit_id,
        reward=reward,
        duration=duration,
        periodicity=periodicity,
        is_public=is_public,
    )
    return habit


@sync_to_async
def delete_habit(habit_id, user_id):
    """Удалить привычку (физическое удаление)"""
    result = Habit.objects.filter(id=habit_id, user_id=user_id).delete()
    return result[0] > 0


@sync_to_async
def get_habit_statistics(chat_id):
    """Получить статистику выполнения привычек"""
    user = User.objects.filter(telegram_chat_id=chat_id).first()
    if not user:
        return None

    habits = Habit.objects.filter(user=user)
    total = habits.count()
    pleasant = habits.filter(is_pleasant=True).count()

    return {
        "total_habits": total,
        "pleasant_habits": pleasant,
        "useful_habits": total - pleasant,
    }


# ========== ОБРАБОТЧИКИ КОМАНД ==========


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)

    if user:
        keyboard = [["Создать привычку", "Мои привычки"], ["Удалить привычку", "Статистика"], ["Помощь"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True, selective=True)

        message = (
            f"👋 Привет, {user.username}!\n\n"
            f"✨ Добро пожаловать в трекер привычек!\n\n"
            f"🤖 <b>Что можно делать:</b>\n"
            f"• Создавать новые привычки ✨\n"
            f"• Получать ежедневные напоминания ⏰\n"
            f"• Просматривать список привычек 📋\n"
            f"• Удалять ненужные привычки 🗑\n"
            f"• Следить за статистикой 📊\n\n"
            f"👇 Выберите действие ниже или используйте команды:\n"
            f"/create — Создать привычку ✨\n"
            f"/habits — Мои привычки 📋\n"
            f"/delete — Удалить привычку 🗑\n"
            f"/stats — Статистика 📊"
        )
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="HTML")
    else:
        keyboard = [["Регистрация", "Привязать аккаунт"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True, selective=True)

        message = (
            "👋 Добро пожаловать в трекер привычек!\n\n"
            "Я помогу вам формировать полезные привычки по методике «Атомных привычек» Джеймса Клира.\n\n"
            "👇 <b>Выберите действие:</b>\n"
            "• Нажмите кнопку <b>«Регистрация»</b> ниже\n"
            "• Или напишите в чат: <code>Регистрация</code>\n\n"
            "💡 <i>Если кнопок не видно — кликните по полю ввода сообщения</i>"
        )

        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="HTML")


async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса регистрации"""
    chat_id = update.effective_chat.id
    exists = await user_exists_by_chat_id(chat_id)

    if exists:
        await update.message.reply_text("❌ Вы уже зарегистрированы!", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    await update.message.reply_text(
        "📝 <b>Регистрация</b>\n\n"
        "Шаг 1 из 3: Введите имя пользователя\n"
        "Только буквы, цифры и @/./+/-/_\n"
        "Минимум 3 символа:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    return USERNAME


async def register_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода имени пользователя"""
    username = update.message.text.strip()

    if len(username) < 3:
        await update.message.reply_text("❌ Не менее 3 символов.\nПопробуйте снова:")
        return USERNAME

    if not username.replace("@", "").replace(".", "").replace("+", "").replace("-", "").replace("_", "").isalnum():
        await update.message.reply_text("❌ Только буквы, цифры и @/./+/-/_\nПопробуйте снова:")
        return USERNAME

    exists = await user_exists_by_username(username)
    if exists:
        await update.message.reply_text("❌ Такой логин уже занят.\nПопробуйте другой:")
        return USERNAME

    context.user_data["username"] = username
    await update.message.reply_text(f"✅ Логин: {username}\n\nШаг 2 из 3: Введите email:")
    return EMAIL


async def register_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода email"""
    email = update.message.text.strip()

    if "@" not in email or "." not in email.split("@")[-1]:
        await update.message.reply_text("❌ Неверный формат email.\nПример: user@example.com\nПопробуйте снова:")
        return EMAIL

    exists = await user_exists_by_email(email)
    if exists:
        await update.message.reply_text("❌ Email уже используется.\nПопробуйте другой:")
        return EMAIL

    context.user_data["email"] = email
    await update.message.reply_text(f"✅ Email: {email}\n\nШаг 3 из 3: Придумайте пароль (мин. 8 символов):")
    return PASSWORD


async def register_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода пароля"""
    password = update.message.text.strip()

    if len(password) < 8:
        await update.message.reply_text("❌ Пароль должен быть не менее 8 символов.\nПопробуйте снова:")
        return PASSWORD

    if password.isdigit() or password.isalpha():
        await update.message.reply_text("❌ Пароль должен содержать буквы и цифры.\nПопробуйте снова:")
        return PASSWORD

    context.user_data["password"] = password
    chat_id = update.effective_chat.id

    try:
        user = await create_user(context.user_data["username"], context.user_data["email"], password, chat_id)

        await update.message.reply_text(
            f"🎉 <b>Регистрация успешна!</b>\n\n"
            f"✅ Пользователь @{user.username} создан\n"
            f"📧 Email: {user.email}\n"
            f"🤖 Telegram привязан автоматически!\n\n"
            f"👉 Теперь создайте свою первую привычку:\n"
            f"• Нажмите кнопку «Создать привычку»\n"
            f"• Или напишите /create",
            parse_mode="HTML",
        )

        logger.info(f"Новый пользователь: {user.username}, chat_id: {chat_id}")

    except IntegrityError as e:
        logger.error(f"Ошибка целостности БД: {e}")
        await update.message.reply_text("❌ Пользователь с такими данными уже существует.")
    except Exception as e:
        logger.error(f"Ошибка создания пользователя: {e}")
        await update.message.reply_text("❌ Ошибка при создании аккаунта.\nПопробуйте снова.")

    return ConversationHandler.END


async def bind_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Привязка существующего аккаунта"""
    chat_id = update.effective_chat.id
    exists = await user_exists_by_chat_id(chat_id)

    if exists:
        await update.message.reply_text("❌ Аккаунт уже привязан!", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    await update.message.reply_text(
        "🔗 <b>Привязка аккаунта</b>\n\n" "Введите логин от вашего аккаунта в трекере привычек:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    return USERNAME


async def bind_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка логина для привязки"""
    username = update.message.text.strip()
    chat_id = update.effective_chat.id

    user = await bind_user_to_chat(username, chat_id)

    if not user:
        await update.message.reply_text(f"❌ Пользователь @{username} не найден.\nПроверьте логин:")
        return USERNAME

    await update.message.reply_text(
        f"✅ Аккаунт @{username} привязан к Telegram!\n\n" f"Теперь вы будете получать напоминания о привычках ⏰",
        parse_mode="HTML",
    )

    logger.info(f"Аккаунт @{username} привязан к chat_id {chat_id}")
    return ConversationHandler.END


# ========== СОЗДАНИЕ ПРИВЫЧКИ ==========


async def create_habit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания привычки"""
    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)

    if not user:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь!\nНапишите /start")
        return ConversationHandler.END

    context.user_data["habit"] = {"user_id": user.id}

    await update.message.reply_text(
        "✨ <b>Создание привычки</b>\n\n"
        "Шаг 1 из 8: Где вы будете выполнять привычку?\n"
        "Пример: «дома», «в спортзале», «на работе»",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    return PLACE


async def habit_place(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод места выполнения"""
    place = update.message.text.strip()

    if len(place) < 2:
        await update.message.reply_text("❌ Место должно быть не менее 2 символов.\nПопробуйте снова:")
        return PLACE

    context.user_data["habit"]["place"] = place
    await update.message.reply_text(
        f"✅ Место: {place}\n\n"
        "Шаг 2 из 8: Во сколько выполнять привычку?\n"
        "Формат: ЧЧ:ММ (например: 08:00 или 21:30)"
    )
    return TIME


async def habit_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод времени выполнения"""
    time_text = update.message.text.strip()

    try:
        parts = time_text.split(":")
        if len(parts) != 2:
            raise ValueError
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        time_obj = time_type(hour=hour, minute=minute)
        context.user_data["habit"]["time"] = time_obj
    except (ValueError, AttributeError):
        await update.message.reply_text("❌ Неверный формат времени.\nПример: 08:00 или 21:30\nПопробуйте снова:")
        return TIME

    await update.message.reply_text(
        f"✅ Время: {time_text}\n\n"
        "Шаг 3 из 8: Какое действие будет привычкой?\n"
        "Опишите кратко: «выпить стакан воды», «сделать 10 отжиманий»"
    )
    return ACTION


async def habit_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод действия"""
    action = update.message.text.strip()

    if len(action) < 5:
        await update.message.reply_text(
            "❌ Действие должно быть описано подробнее (минимум 5 символов).\nПопробуйте снова:"
        )
        return ACTION

    context.user_data["habit"]["action"] = action
    await update.message.reply_text(
        f"✅ Действие: {action}\n\n"
        "Шаг 4 из 8: Это приятная привычка?\n"
        "Приятная привычка — это вознаграждение за выполнение полезной привычки.\n\n"
        "Выберите: Да / Нет",
        reply_markup=ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True, resize_keyboard=True),
    )
    return IS_PLEASANT


async def habit_is_pleasant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор типа привычки с унифицированной обработкой ответа"""
    text = update.message.text.strip().lower()

    if text not in ["да", "нет"]:
        await update.message.reply_text(
            "❌ Выберите «Да» или «Нет»",
            reply_markup=ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True, resize_keyboard=True),
        )
        return IS_PLEASANT

    is_pleasant = text == "да"
    context.user_data["habit"]["is_pleasant"] = is_pleasant

    if is_pleasant:
        context.user_data["habit"]["reward"] = None
        context.user_data["habit"]["related_habit_id"] = None

        await update.message.reply_text(
            "✅ Приятная привычка (вознаграждение)\n\n"
            "Шаг 5 из 8: Сколько времени займёт выполнение?\n"
            "Максимум 120 секунд:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return DURATION
    else:
        chat_id = update.effective_chat.id
        pleasant_habits = await get_user_habits_data(chat_id)
        pleasant_habits = [h for h in pleasant_habits if h["is_pleasant"]]

        if pleasant_habits:
            keyboard = [[f"{i + 1}. {h['action']}"[:30]] for i, h in enumerate(pleasant_habits)]
            keyboard.append(["Пропустить"])

            context.user_data["habit"]["pleasant_habits_list"] = pleasant_habits

            await update.message.reply_text(
                "Шаг 5 из 8: Выберите приятную привычку как вознаграждение:\n"
                "(Это действие, которое вы сделаете сразу после выполнения полезной привычки)",
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
            )
            return RELATED_HABIT
        else:
            context.user_data["habit"]["related_habit_id"] = None
            await update.message.reply_text(
                "ℹ️ У вас пока нет приятных привычек.\n\n"
                "Шаг 6 из 8: Укажите вознаграждение:\n"
                "Например: «посмотреть серию», «съесть шоколадку»",
                reply_markup=ReplyKeyboardRemove(),
            )
            return REWARD


async def habit_related_habit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор связанной приятной привычки"""
    text = update.message.text.strip().lower()

    if text == "пропустить":
        context.user_data["habit"]["related_habit_id"] = None
        await update.message.reply_text(
            "Шаг 6 из 8: Укажите вознаграждение:\n" "Например: «посмотреть серию», «съесть шоколадку»"
        )
        return REWARD

    try:
        habit_num = int(text.split(".")[0]) - 1
        pleasant_habits = context.user_data["habit"]["pleasant_habits_list"]

        if 0 <= habit_num < len(pleasant_habits):
            selected_habit = pleasant_habits[habit_num]
            context.user_data["habit"]["related_habit_id"] = selected_habit["id"]
            context.user_data["habit"]["reward"] = None

            await update.message.reply_text(
                f"✅ Связанная привычка: {selected_habit['action']}\n\n"
                "Шаг 7 из 8: Сколько времени займёт выполнение?\n"
                "Максимум 120 секунд:"
            )
            return DURATION
        else:
            raise ValueError
    except (ValueError, IndexError, KeyError, TypeError):
        await update.message.reply_text(
            "❌ Неверный выбор. Попробуйте снова:",
            reply_markup=ReplyKeyboardMarkup(
                [
                    [f"{i + 1}. {h['action']}"[:30]]
                    for i, h in enumerate(context.user_data["habit"]["pleasant_habits_list"])
                ]
                + [["Пропустить"]],
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )
        return RELATED_HABIT


async def habit_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод вознаграждения"""
    reward = update.message.text.strip()

    if len(reward) < 3:
        await update.message.reply_text("❌ Вознаграждение должно быть не менее 3 символов.\nПопробуйте снова:")
        return REWARD

    context.user_data["habit"]["reward"] = reward
    context.user_data["habit"]["related_habit_id"] = None

    await update.message.reply_text(
        f"✅ Вознаграждение: {reward}\n\n" "Шаг 7 из 8: Сколько времени займёт выполнение?\n" "Максимум 120 секунд:"
    )
    return DURATION


async def habit_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод времени выполнения"""
    try:
        duration = int(update.message.text.strip())

        if duration < 1 or duration > 120:
            await update.message.reply_text("❌ От 1 до 120 секунд.\nПопробуйте снова:")
            return DURATION

        context.user_data["habit"]["duration"] = duration
        await update.message.reply_text(
            f"✅ Время: {duration} сек\n\n"
            "Шаг 8 из 8: Как часто выполнять привычку?\n"
            "Периодичность в днях (1-7):\n"
            "1 = ежедневно, 7 = раз в неделю"
        )
        return PERIODICITY
    except ValueError:
        await update.message.reply_text("❌ Введите число от 1 до 120.\nПопробуйте снова:")
        return DURATION


async def habit_periodicity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод периодичности"""
    try:
        periodicity = int(update.message.text.strip())

        if periodicity < 1 or periodicity > 7:
            await update.message.reply_text("❌ От 1 до 7 дней.\nПопробуйте снова:")
            return PERIODICITY

        context.user_data["habit"]["periodicity"] = periodicity
        await update.message.reply_text(
            f"✅ Периодичность: каждые {periodicity} дн.\n\n"
            "Последний шаг: Сделать привычку публичной?\n"
            "Публичные привычки видны другим как примеры.\n\n"
            "Выберите: Да / Нет",
            reply_markup=ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True, resize_keyboard=True),
        )
        return IS_PUBLIC
    except ValueError:
        await update.message.reply_text("❌ Введите число от 1 до 7.\nПопробуйте снова:")
        return PERIODICITY


async def habit_is_public(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор публичности с унифицированной обработкой ответа"""
    text = update.message.text.strip().lower()

    if text not in ["да", "нет"]:
        await update.message.reply_text(
            "❌ Выберите «Да» или «Нет»",
            reply_markup=ReplyKeyboardMarkup([["Да", "Нет"]], one_time_keyboard=True, resize_keyboard=True),
        )
        return IS_PUBLIC

    is_public = text == "да"
    context.user_data["habit"]["is_public"] = is_public

    # Удаляем временный ключ перед созданием привычки
    context.user_data["habit"].pop("pleasant_habits_list", None)

    # Создаём привычку
    try:
        habit = await create_habit(**context.user_data["habit"])

        message = (
            "🎉 <b>Привычка создана!</b>\n\n"
            f"📍 Место: {habit.place}\n"
            f"⏰ Время: {habit.time.strftime('%H:%M')}\n"
            f"🎯 Действие: {habit.action}\n"
        )

        if habit.is_pleasant:
            message += "✨ Тип: Приятная привычка\n"
        else:
            if habit.related_habit:
                message += f"🔄 После: {habit.related_habit.action}\n"
            elif habit.reward:
                message += f"🎁 Вознаграждение: {habit.reward}\n"

        message += (
            f"⏱ Выполнение: {habit.duration} сек\n"
            f"📅 Периодичность: каждые {habit.periodicity} дн.\n"
            f"{'🌐 Публичная' if habit.is_public else '🔒 Приватная'}\n\n"
            f"💡 Напоминания будут приходить ежедневно в {habit.time.strftime('%H:%M')}!"
        )

        await update.message.reply_text(message, parse_mode="HTML")
        logger.info(f"Новая привычка: {habit.action} (user_id={habit.user.id})")

    except Exception as e:
        logger.error(f"Ошибка создания привычки: {e}")
        await update.message.reply_text(f"❌ Ошибка при создании привычки:\n{str(e)[:150]}\n\nПопробуйте снова.")

    return ConversationHandler.END


# ========== ПРОСМОТР ПРИВЫЧЕК ==========


async def show_habits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список привычек пользователя БЕЗ синхронных операций в асинхронном контексте"""
    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)

    if not user:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь!\nНапишите /start")
        return

    # Получаем данные через безопасную асинхронную обёртку
    habits_data = await get_user_habits_data(chat_id)

    if not habits_data:
        await update.message.reply_text("📋 У вас пока нет активных привычек.\n" "Создайте первую с помощью /create")
        return

    message = "📋 <b>Ваши привычки:</b>\n\n"
    for i, habit in enumerate(habits_data, 1):
        message += f"{i}. 🕐 {habit['time'].strftime('%H:%M')} — <b>{habit['action']}</b>\n"
        message += f"   📍 {habit['place']}\n"

        if habit["is_pleasant"]:
            message += "   ✨ Приятная привычка\n"
        else:
            if habit["related_habit"]:
                message += f"   🔄 После: {habit['related_habit']['action']}\n"
            elif habit["reward"]:
                message += f"   🎁 {habit['reward']}\n"

        message += f"   ⏱ {habit['duration']} сек | 📅 каждые {habit['periodicity']} дн.\n"
        message += "\n"

    # Ограничение длины сообщения Telegram (макс. 4096 символов)
    if len(message) > 4000:
        message = message[:4000] + "\n\n<i>... список обрезан из-за ограничения Telegram</i>"

    await update.message.reply_text(message, parse_mode="HTML")


# ========== УДАЛЕНИЕ ПРИВЫЧКИ ==========


async def delete_habit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало удаления привычки"""
    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)

    if not user:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь!\nНапишите /start")
        return ConversationHandler.END

    # Получаем данные привычек безопасным способом
    habits_data = await get_user_habits_data(chat_id)

    if not habits_data:
        await update.message.reply_text("📋 У вас нет привычек для удаления.\nСоздайте привычку с помощью /create")
        return ConversationHandler.END

    context.user_data["habits_list"] = habits_data

    message = "🗑 <b>Выберите привычку для удаления:</b>\n\n"
    for i, habit in enumerate(habits_data, 1):
        message += f"{i}. {habit['action']} ({habit['time'].strftime('%H:%M')})\n"

    message += "\nВведите номер привычки:"

    await update.message.reply_text(message, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    return SELECT_HABIT_TO_DELETE


async def select_habit_to_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор привычки для удаления с безопасной обработкой ошибок"""
    # Получаем список привычек ДО попытки преобразования в число
    habits = context.user_data.get("habits_list", [])

    if not habits:
        await update.message.reply_text("❌ Список привычек пуст. Начните удаление заново с помощью /delete")
        return ConversationHandler.END

    try:
        habit_num = int(update.message.text.strip()) - 1

        if 0 <= habit_num < len(habits):
            selected_habit = habits[habit_num]
            context.user_data["habit_to_delete"] = selected_habit

            keyboard = [["Да, удалить", "Отмена"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

            await update.message.reply_text(
                f"❓ Вы уверены, что хотите удалить привычку?\n\n"
                f"<b>{selected_habit['action']}</b>\n"
                f"Время: {selected_habit['time'].strftime('%H:%M')}\n"
                f"Место: {selected_habit['place']}",
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
            return CONFIRM_DELETE
        else:
            raise ValueError("Номер вне диапазона")

    except (ValueError, AttributeError):
        count = len(habits)
        await update.message.reply_text(f"❌ Неверный ввод. Введите число от 1 до {count}:")
        return SELECT_HABIT_TO_DELETE


async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления с унифицированной обработкой ответа"""
    text = update.message.text.strip().lower()

    if text in ["отмена", "нет"]:
        await update.message.reply_text("❌ Удаление отменено.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    if text not in ["да", "да, удалить"]:
        await update.message.reply_text(
            "❓ Вы уверены? Выберите «Да, удалить» или «Отмена»:",
            reply_markup=ReplyKeyboardMarkup(
                [["Да, удалить", "Отмена"]], one_time_keyboard=True, resize_keyboard=True
            ),
        )
        return CONFIRM_DELETE

    habit = context.user_data["habit_to_delete"]
    user = await get_user_by_chat_id(update.effective_chat.id)

    success = await delete_habit(habit["id"], user.id)

    if success:
        await update.message.reply_text(
            f"✅ Привычка «{habit['action']}» удалена!", reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text("❌ Ошибка при удалении привычки.", reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


# ========== СТАТИСТИКА ==========


async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику пользователя"""
    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)

    if not user:
        await update.message.reply_text("❌ Сначала зарегистрируйтесь!\nНапишите /start")
        return

    stats = await get_habit_statistics(chat_id)

    if not stats or stats["total_habits"] == 0:
        await update.message.reply_text("📊 У вас пока нет статистики.\nСоздайте первую привычку с помощью /create")
        return

    message = (
        "📊 <b>Ваша статистика:</b>\n\n"
        f"Всего привычек: {stats['total_habits']}\n"
        f"Полезных привычек: {stats['useful_habits']}\n"
        f"Приятных привычек: {stats['pleasant_habits']}\n\n"
        f"💡 Совет: Создайте баланс полезных и приятных привычек для лучшего результата!"
    )

    await update.message.reply_text(message, parse_mode="HTML")


# ========== ОТМЕНА И ПОМОЩЬ ==========


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена операции"""
    await update.message.reply_text("❌ Операция отменена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    chat_id = update.effective_chat.id
    user = await get_user_by_chat_id(chat_id)

    if user:
        message = (
            "🤖 <b>Доступные команды:</b>\n\n"
            "/create — Создать новую привычку ✨\n"
            "/habits — Показать мои привычки 📋\n"
            "/delete — Удалить привычку 🗑\n"
            "/stats — Показать статистику 📊\n"
            "/help — Эта справка ℹ️\n\n"
            "💡 <b>Советы по методике «Атомных привычек»:</b>\n"
            "• Привычка должна занимать ≤ 2 минут (120 сек)\n"
            "• Выполняйте ежедневно для формирования\n"
            "• Связывайте полезные с приятными привычками"
        )
    else:
        message = (
            "🤖 <b>Доступные команды:</b>\n\n"
            "/start — Начать работу с ботом 👋\n"
            "/help — Показать эту справку ℹ️\n\n"
            "💡 Чтобы начать:\n"
            "1. Нажмите «Регистрация» для создания аккаунта 📝\n"
            "2. Или «Привязать аккаунт» если уже есть в системе 🔗"
        )

    await update.message.reply_text(message, parse_mode="HTML")


# ========== ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА ==========


def main():
    """Запуск бота"""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не найден в .env!")
        sys.exit(1)

    logger.info("🤖 Запуск бота трекера привычек...")

    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Обработчик регистрации
    registration_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^(Регистрация|регистрация)$"), register_start),
            CommandHandler("register", register_start),
            CommandHandler("start", start),
        ],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_username)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_email)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Обработчик привязки аккаунта
    bind_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^(Привязать аккаунт|привязать аккаунт|Привязать|привязать)$"), bind_account),
            CommandHandler("bind", bind_account),
        ],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, bind_username)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Обработчик создания привычки
    create_habit_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^(Создать привычку|создать привычку)$"), create_habit_start),
            CommandHandler("create", create_habit_start),
            CommandHandler("create_habit", create_habit_start),
        ],
        states={
            PLACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, habit_place)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, habit_time)],
            ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, habit_action)],
            IS_PLEASANT: [MessageHandler(filters.Regex("^(Да|Нет|да|нет)$"), habit_is_pleasant)],
            RELATED_HABIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, habit_related_habit)],
            REWARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, habit_reward)],
            DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, habit_duration)],
            PERIODICITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, habit_periodicity)],
            IS_PUBLIC: [MessageHandler(filters.Regex("^(Да|Нет|да|нет)$"), habit_is_public)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Обработчик удаления привычки
    delete_habit_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^(Удалить привычку|удалить привычку)$"), delete_habit_start),
            CommandHandler("delete", delete_habit_start),
        ],
        states={
            SELECT_HABIT_TO_DELETE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_habit_to_delete)],
            CONFIRM_DELETE: [
                MessageHandler(
                    filters.Regex("^(Да, удалить|да, удалить|Отмена|отмена|Да|да|Нет|нет)$"), confirm_delete
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Регистрация обработчиков
    application.add_handler(registration_handler)
    application.add_handler(bind_handler)
    application.add_handler(create_habit_handler)
    application.add_handler(delete_habit_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("habits", show_habits))
    application.add_handler(CommandHandler("stats", show_statistics))
    application.add_handler(CommandHandler("help", help_command))

    # Резервные текстовые обработчики
    application.add_handler(
        MessageHandler(filters.Text(["Мои привычки", "мои привычки", "Привычки", "привычки"]), show_habits)
    )
    application.add_handler(
        MessageHandler(filters.Text(["Статистика", "статистика", "Стат", "стат"]), show_statistics)
    )
    application.add_handler(MessageHandler(filters.Text(["Помощь", "помощь", "Help", "help"]), help_command))

    logger.info("✅ Бот запущен и готов к работе!")
    if hasattr(settings, "TELEGRAM_BOT_NAME"):
        logger.info(f"👉 Напишите боту: https://t.me/{settings.TELEGRAM_BOT_NAME}")
    else:
        logger.info("👉 Найдите вашего бота в Telegram по имени")

    application.run_polling()


if __name__ == "__main__":
    main()
