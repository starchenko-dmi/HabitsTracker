from unittest.mock import patch
import pytest

pytestmark = pytest.mark.django_db


class TestRegistrationFlow:
    """Тесты процесса регистрации"""

    @pytest.mark.asyncio
    async def test_register_start_already_registered(self, update_mock, context_mock, db_user):
        """Попытка регистрации уже зарегистрированного пользователя"""
        from telegram_bot.bot import ConversationHandler, register_start

        # chat_id зарегистрированного пользователя
        update_mock.effective_chat.id = db_user.telegram_chat_id

        result = await register_start(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        # Учитываем реальное сообщение: "❌ Вы уже зарегистрированы!"
        assert "зарегистрирован" in text
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_register_start_new_user(self, update_mock, context_mock):
        """Начало регистрации нового пользователя"""
        from telegram_bot.bot import register_start

        update_mock.effective_chat.id = 999999999  # Новый пользователь

        result = await register_start(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "шаг 1" in text
        assert "имя пользователя" in text
        assert result == 0  # USERNAME статус

    @pytest.mark.asyncio
    async def test_register_username_valid(self, update_mock, context_mock):
        """Валидное имя пользователя"""
        from telegram_bot.bot import register_username

        update_mock.message.text = "valid_user123"
        context_mock.user_data = {}

        result = await register_username(update_mock, context_mock)

        assert context_mock.user_data["username"] == "valid_user123"
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "шаг 2" in text
        assert result == 1  # EMAIL статус

    @pytest.mark.asyncio
    async def test_register_username_invalid_short(self, update_mock, context_mock):
        """Слишком короткое имя пользователя"""
        from telegram_bot.bot import register_username

        update_mock.message.text = "ab"
        context_mock.user_data = {}

        result = await register_username(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "3 символ" in text
        assert result == 0  # Остаёмся на USERNAME

    @pytest.mark.asyncio
    async def test_register_email_valid(self, update_mock, context_mock, mocker):
        """Валидный email"""
        from unittest.mock import AsyncMock

        from telegram_bot.bot import register_email

        # Мокаем асинхронную функцию проверки существования email
        mocker.patch(
            "telegram_bot.bot.user_exists_by_email", new_callable=AsyncMock, return_value=False  # Email свободен
        )

        update_mock.message.text = "new@example.com"
        context_mock.user_data = {"username": "newuser"}

        result = await register_email(update_mock, context_mock)

        # Проверяем, что email сохранён в контексте
        assert context_mock.user_data["email"] == "new@example.com"
        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "шаг 3" in text
        assert result == 2  # PASSWORD статус

    @pytest.mark.asyncio
    async def test_register_email_invalid(self, update_mock, context_mock):
        """Невалидный email"""
        from telegram_bot.bot import register_email

        update_mock.message.text = "invalid-email"
        context_mock.user_data = {"username": "newuser"}

        result = await register_email(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "неверный формат" in text
        assert result == 1  # Остаёмся на EMAIL

    @pytest.mark.asyncio
    async def test_register_password_valid(self, update_mock, context_mock):
        """Валидный пароль и успешная регистрация"""
        from unittest.mock import AsyncMock

        from telegram_bot.bot import ConversationHandler, register_password

        # Мокаем создание пользователя
        with patch("telegram_bot.bot.create_user", new_callable=AsyncMock) as mock_create:
            mock_user = AsyncMock()
            mock_user.username = "newuser"
            mock_user.email = "new@example.com"
            mock_user.telegram_chat_id = 999999999
            mock_create.return_value = mock_user

            update_mock.effective_chat.id = 999999999
            update_mock.message.text = "StrongPass123!"
            context_mock.user_data = {
                "username": "newuser",
                "email": "new@example.com",
            }

            result = await register_password(update_mock, context_mock)

            assert update_mock.message.reply_text.called
            text = update_mock.message.reply_text.call_args[0][0].lower()
            assert "успешн" in text or "создан" in text
            assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_bind_account_already_bound(self, update_mock, context_mock, db_user):
        """Попытка привязки уже привязанного аккаунта"""
        from telegram_bot.bot import ConversationHandler, bind_account

        update_mock.effective_chat.id = db_user.telegram_chat_id

        result = await bind_account(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        # Учитываем реальное сообщение: "❌ Аккаунт уже привязан!"
        assert "привязан" in text
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_bind_username_success(self, update_mock, context_mock):
        """Успешная привязка аккаунта"""
        import uuid

        from asgiref.sync import sync_to_async

        from telegram_bot.bot import ConversationHandler, bind_username

        # Генерируем УНИКАЛЬНОЕ имя пользователя для изоляции тестов
        unique_suffix = uuid.uuid4().hex[:8]
        unique_username = f"unbound_user_{unique_suffix}"

        # Создаём пользователя без привязки к Telegram
        @sync_to_async
        def create_unbound_user():
            from django.contrib.auth import get_user_model

            User = get_user_model()
            return User.objects.create_user(
                username=unique_username, email=f"{unique_username}@example.com", password="TestPass123!"
            )

        unbound_user = await create_unbound_user()

        update_mock.effective_chat.id = 111222333  # Новый chat_id
        update_mock.message.text = unbound_user.username

        result = await bind_username(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "привязан" in text
        assert result == ConversationHandler.END
