import pytest

pytestmark = pytest.mark.django_db


class TestRegistrationExtra:
    """Дополнительные тесты регистрации"""

    @pytest.mark.asyncio
    async def test_register_start_new_user_parse_mode(self, update_mock, context_mock):
        """Проверка parse_mode на первом шаге регистрации"""
        from telegram_bot.bot import register_start

        update_mock.effective_chat.id = 999999999

        result = await register_start(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        call_kwargs = update_mock.message.reply_text.call_args[1]
        assert call_kwargs.get("parse_mode") == "HTML"
        assert result == 0  # USERNAME статус

    @pytest.mark.asyncio
    async def test_register_username_invalid_special_chars(self, update_mock, context_mock):
        """Проверка недопустимых спецсимволов в имени пользователя"""
        from telegram_bot.bot import register_username

        update_mock.message.text = "user@name#"
        context_mock.user_data = {}

        result = await register_username(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "только буквы" in text or "цифры" in text
        assert result == 0  # Остаёмся на USERNAME

    @pytest.mark.asyncio
    async def test_register_email_invalid_missing_at(self, update_mock, context_mock):
        """Проверка отсутствия @ в email"""
        from telegram_bot.bot import register_email

        update_mock.message.text = "userexample.com"
        context_mock.user_data = {"username": "testuser"}

        result = await register_email(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "неверный формат" in text
        assert result == 1  # Остаёмся на EMAIL

    @pytest.mark.asyncio
    async def test_register_email_invalid_missing_domain(self, update_mock, context_mock):
        """Проверка отсутствия домена в email"""
        from telegram_bot.bot import register_email

        update_mock.message.text = "user@"
        context_mock.user_data = {"username": "testuser"}

        result = await register_email(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "неверный формат" in text
        assert result == 1  # Остаёмся на EMAIL

    @pytest.mark.asyncio
    async def test_register_password_invalid_only_digits(self, update_mock, context_mock):
        """Проверка пароля из одних цифр"""
        from telegram_bot.bot import register_password

        update_mock.message.text = "12345678"
        context_mock.user_data = {
            "username": "testuser",
            "email": "test@example.com",
        }

        result = await register_password(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "буквы и цифры" in text
        assert result == 2  # Остаёмся на PASSWORD

    @pytest.mark.asyncio
    async def test_register_password_invalid_only_letters(self, update_mock, context_mock):
        """Проверка пароля из одних букв"""
        from telegram_bot.bot import register_password

        update_mock.message.text = "password"
        context_mock.user_data = {
            "username": "testuser",
            "email": "test@example.com",
        }

        result = await register_password(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "буквы и цифры" in text
        assert result == 2  # Остаёмся на PASSWORD

    @pytest.mark.asyncio
    async def test_register_password_invalid_short(self, update_mock, context_mock):
        """Проверка короткого пароля"""
        from telegram_bot.bot import register_password

        update_mock.message.text = "pass123"
        context_mock.user_data = {
            "username": "testuser",
            "email": "test@example.com",
        }

        result = await register_password(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "8 символов" in text
        assert result == 2  # Остаёмся на PASSWORD

    @pytest.mark.asyncio
    async def test_bind_account_new_user(self, update_mock, context_mock):
        """Проверка начала привязки для нового пользователя"""
        from telegram_bot.bot import bind_account

        update_mock.effective_chat.id = 999999999

        result = await bind_account(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        text = update_mock.message.reply_text.call_args[0][0].lower()
        assert "привязка аккаунта" in text or "логин" in text
        assert result == 0  # USERNAME статус

    @pytest.mark.asyncio
    async def test_bind_account_new_user_parse_mode(self, update_mock, context_mock):
        """Проверка parse_mode при привязке аккаунта"""
        from telegram_bot.bot import bind_account

        update_mock.effective_chat.id = 999999999

        await bind_account(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        call_kwargs = update_mock.message.reply_text.call_args[1]
        assert call_kwargs.get("parse_mode") == "HTML"

    @pytest.mark.asyncio
    async def test_bind_username_success_parse_mode(self, update_mock, context_mock, db_user):
        """Проверка parse_mode при успешной привязке"""
        from asgiref.sync import sync_to_async

        from telegram_bot.bot import bind_username

        # Создаём пользователя без привязки
        @sync_to_async
        def create_unbound_user():
            from django.contrib.auth import get_user_model

            User = get_user_model()
            return User.objects.create_user(
                username="unbound_user", email="unbound@example.com", password="TestPass123!"
            )

        unbound_user = await create_unbound_user()

        update_mock.effective_chat.id = 111222333
        update_mock.message.text = unbound_user.username

        await bind_username(update_mock, context_mock)

        assert update_mock.message.reply_text.called
        call_kwargs = update_mock.message.reply_text.call_args[1]
        assert call_kwargs.get("parse_mode") == "HTML"
