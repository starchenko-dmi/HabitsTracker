import pytest

pytestmark = pytest.mark.django_db


class TestCommandHandlers:
    """Тесты базовых команд бота"""

    @pytest.mark.asyncio
    async def test_start_unregistered_user(self, update_mock, context_mock):
        """Проверка /start для незарегистрированного пользователя"""
        from telegram_bot.bot import start

        update_mock.effective_chat.id = 999999999  # Несуществующий пользователь

        await start(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "добро пожаловать" in text
        assert "регистрация" in text

    @pytest.mark.asyncio
    async def test_start_registered_user(self, update_mock, context_mock, db_user):
        """Проверка /start для зарегистрированного пользователя"""
        from telegram_bot.bot import start

        # КРИТИЧЕСКИ ВАЖНО: совпадение chat_id
        update_mock.effective_chat.id = db_user.telegram_chat_id

        await start(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        # Проверяем наличие элементов интерфейса зарегистрированного пользователя
        assert "создать привычку" in text or "мои привычки" in text
        assert "👋" in text or "привет" in text

    @pytest.mark.asyncio
    async def test_help_command_unregistered(self, update_mock, context_mock):
        """Проверка /help для незарегистрированного пользователя"""
        from telegram_bot.bot import help_command

        update_mock.effective_chat.id = 999999999

        await help_command(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "/start" in text
        assert "регистрация" in text

    @pytest.mark.asyncio
    async def test_help_command_registered(self, update_mock, context_mock, db_user):
        """Проверка /help для зарегистрированного пользователя"""
        from telegram_bot.bot import help_command

        update_mock.effective_chat.id = db_user.telegram_chat_id

        await help_command(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "/create" in text
        assert "/habits" in text
        assert "/delete" in text
        assert "/stats" in text

    @pytest.mark.asyncio
    async def test_cancel(self, update_mock, context_mock):
        """Проверка команды отмены"""
        from telegram_bot.bot import ConversationHandler, cancel

        result = await cancel(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        # Учитываем реальное сообщение: "операция отменена"
        assert "отмен" in text  # Ловим корень слова
        assert result == ConversationHandler.END
