from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db

User = get_user_model()


class TestWebhookView:
    """Тесты вебхука для получения обновлений от Telegram"""

    def test_webhook_get_not_allowed(self, client):
        """Проверка, что GET запрос к вебхуку не разрешён"""
        url = reverse("telegram_webhook")
        response = client.get(url)
        assert response.status_code == 405  # Method Not Allowed

    @patch("telegram_bot.views.application")
    @patch("telegram_bot.views.Update")
    def test_webhook_post_valid_update(self, mock_update_class, mock_application, client):
        """Проверка обработки валидного обновления от Telegram"""
        from telegram_bot import views

        # Сбрасываем глобальную переменную для чистого состояния
        views.application = mock_application

        url = reverse("telegram_webhook")

        # Подготовка моков
        mock_update = MagicMock()
        mock_update_class.de_json.return_value = mock_update

        # Используем реальный объект Bot вместо MagicMock для избежания ошибки tzinfo
        from telegram import Bot

        mock_bot = Bot(token="test_token")
        mock_application.bot = mock_bot

        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: мокаем как СИНХРОННЫЕ методы (вызываются без await в коде)
        mock_application.initialize = MagicMock()
        mock_application.updater = MagicMock()
        mock_application.updater.initialize = MagicMock()
        mock_application.update_queue = MagicMock()
        mock_application.update_queue.put_nowait = MagicMock()  # ← Синхронный мок!

        # Валидные данные обновления от Telegram
        update_data = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {"id": 987654321, "is_bot": False, "first_name": "Test"},
                "chat": {"id": 987654321, "type": "private"},
                "date": 1234567890,
                "text": "/start",
            },
        }

        response = client.post(url, data=update_data, content_type="application/json")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_update_class.de_json.assert_called_once_with(update_data, mock_bot)
        mock_application.update_queue.put_nowait.assert_called_once_with(mock_update)

    @patch("telegram_bot.views.ApplicationBuilder")
    def test_webhook_initializes_application_on_first_call(self, mock_builder_class, client):
        """Проверка инициализации приложения бота при первом вызове вебхука"""
        from telegram_bot import views

        # Сбрасываем глобальную переменную
        views.application = None

        url = reverse("telegram_webhook")

        # Подготовка моков
        from telegram import Bot

        mock_bot = Bot(token="test_token")

        mock_application = MagicMock()
        mock_application.bot = mock_bot

        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: все методы мокаем как СИНХРОННЫЕ
        mock_application.initialize = MagicMock()
        mock_application.updater = MagicMock()
        mock_application.updater.initialize = MagicMock()
        mock_application.update_queue = MagicMock()
        mock_application.update_queue.put_nowait = MagicMock()

        mock_builder = MagicMock()
        mock_builder.token.return_value = mock_builder
        mock_builder.build.return_value = mock_application
        mock_builder_class.return_value = mock_builder

        update_data = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "from": {"id": 987654321, "is_bot": False, "first_name": "Test"},
                "chat": {"id": 987654321, "type": "private"},
                "date": 1234567890,
                "text": "/start",
            },
        }

        response = client.post(url, data=update_data, content_type="application/json")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert views.application is not None  # Приложение инициализировано
        mock_builder.token.assert_called_once()
        mock_application.initialize.assert_called_once()
        mock_application.updater.initialize.assert_called_once()


class TestSetWebhookView:
    """Тесты установки вебхука"""

    @patch("telegram_bot.views.get_bot")
    def test_set_webhook_no_token(self, mock_get_bot, client):
        """Проверка обработки отсутствия токена при установке вебхука"""
        mock_get_bot.return_value = None

        url = reverse("set_webhook")
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"

    @patch("telegram_bot.views.get_bot")
    def test_set_webhook_api_error(self, mock_get_bot, client):
        """Проверка обработки ошибки API при установке вебхука"""
        mock_bot = MagicMock()
        mock_bot.set_webhook.side_effect = Exception("API error")
        mock_get_bot.return_value = mock_bot

        url = reverse("set_webhook")
        response = client.get(url)

        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "API error" in data["message"]


class TestDeleteWebhookView:
    """Тесты удаления вебхука"""

    @patch("telegram_bot.views.get_bot")
    def test_delete_webhook_success(self, mock_get_bot, client):
        """Проверка успешного удаления вебхука"""
        mock_bot = MagicMock()
        mock_bot.delete_webhook = MagicMock()
        mock_get_bot.return_value = mock_bot

        url = reverse("delete_webhook")
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "Webhook deleted"
        mock_bot.delete_webhook.assert_called_once()

    @patch("telegram_bot.views.get_bot")
    def test_delete_webhook_no_token(self, mock_get_bot, client):
        """Проверка обработки отсутствия токена при удалении вебхука"""
        mock_get_bot.return_value = None

        url = reverse("delete_webhook")
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"

    @patch("telegram_bot.views.get_bot")
    def test_delete_webhook_api_error(self, mock_get_bot, client):
        """Проверка обработки ошибки API при удалении вебхука"""
        mock_bot = MagicMock()
        mock_bot.delete_webhook.side_effect = Exception("API error")
        mock_get_bot.return_value = mock_bot

        url = reverse("delete_webhook")
        response = client.get(url)

        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "API error" in data["message"]


class TestAsyncCommandHandlers:
    """Тесты асинхронных команд из views.py"""

    @pytest.fixture(autouse=True)
    def setup_fixtures(self, db_user, update_mock, context_mock):
        """Настройка фикстур для всех тестов"""
        self.db_user = db_user
        self.update_mock = update_mock
        self.context_mock = context_mock
        # Гарантируем наличие всех необходимых атрибутов
        self.update_mock.effective_user = MagicMock()
        self.update_mock.effective_user.id = db_user.telegram_chat_id
        self.update_mock.effective_user.first_name = "TestUser"
        self.update_mock.message = AsyncMock()
        self.update_mock.message.reply_html = AsyncMock()
        self.update_mock.message.reply_text = AsyncMock()

    @pytest.mark.asyncio
    async def test_start_command_registered_user(self):
        """Покрытие строк 19-29: команда /start для зарегистрированного пользователя"""
        from telegram_bot.views import start_command

        await start_command(self.update_mock, self.context_mock)

        assert self.update_mock.message.reply_html.called
        text = self.update_mock.message.reply_html.call_args[0][0]
        assert "Привет" in text or "👋" in text
        assert str(self.update_mock.effective_user.id) in text

    @pytest.mark.asyncio
    async def test_start_command_unregistered_user(self):
        """Покрытие строк 19-29: команда /start для незарегистрированного пользователя"""
        from telegram_bot.views import start_command

        # Меняем chat_id на несуществующий
        self.update_mock.effective_user.id = 999999999

        await start_command(self.update_mock, self.context_mock)

        assert self.update_mock.message.reply_html.called
        text = self.update_mock.message.reply_html.call_args[0][0]
        assert "Привет" in text or "👋" in text
        assert str(999999999) in text

    @pytest.mark.asyncio
    async def test_help_command_unregistered_user(self):
        """Покрытие строк 32-41: команда /help для незарегистрированного пользователя"""
        from telegram_bot.views import help_command

        self.update_mock.effective_user.id = 999999999

        await help_command(self.update_mock, self.context_mock)

        assert self.update_mock.message.reply_html.called
        text = self.update_mock.message.reply_html.call_args[0][0].lower()
        assert "/start" in text
        assert "/help" in text

    @pytest.mark.asyncio
    async def test_help_command_registered_user(self):
        """Покрытие строк 32-41: команда /help для зарегистрированного пользователя"""
        from telegram_bot.views import help_command

        self.update_mock.effective_user.id = self.db_user.telegram_chat_id

        await help_command(self.update_mock, self.context_mock)

        assert self.update_mock.message.reply_html.called
        text = self.update_mock.message.reply_html.call_args[0][0].lower()
        # ВНИМАНИЕ: В views.py команда /help НЕ включает /create!
        # Проверяем правильные команды из справки views.py
        assert "/start" in text
        assert "/help" in text
        assert "/habits" in text  # ← Исправлено: /habits вместо /create
        assert "/stats" in text  # ← Исправлено: /stats вместо /create

    @pytest.mark.asyncio
    async def test_habits_command_user_not_found(self):
        """Покрытие строк 74-76: обработка User.DoesNotExist в /habits (с моками)"""
        from telegram_bot.views import habits_command
        from users.models import User

        # Мокаем синхронные вызовы с исключением
        with patch.object(User.objects, "get") as mock_get_user:
            mock_get_user.side_effect = User.DoesNotExist()

            await habits_command(self.update_mock, self.context_mock)

            assert self.update_mock.message.reply_html.called
            text = self.update_mock.message.reply_html.call_args[0][0].lower()
            assert "аккаунт не привязан" in text or "⚠️" in text

    @pytest.mark.asyncio
    async def test_stats_command_user_not_found(self):
        """Покрытие строк 102-104: обработка User.DoesNotExist в /stats (с моками)"""
        from telegram_bot.views import stats_command
        from users.models import User

        # Мокаем синхронные вызовы с исключением
        with patch.object(User.objects, "get") as mock_get_user:
            mock_get_user.side_effect = User.DoesNotExist()

            await stats_command(self.update_mock, self.context_mock)

            assert self.update_mock.message.reply_html.called
            text = self.update_mock.message.reply_html.call_args[0][0].lower()
            assert "аккаунт не привязан" in text or "⚠️" in text

    def test_set_webhook_no_token(self, client):
        """Покрытие строк 154-156: set_webhook без токена (без инициализации Application)"""
        from telegram_bot import views

        # Сохраняем оригинальный токен
        original_token = views.settings.TELEGRAM_BOT_TOKEN
        views.settings.TELEGRAM_BOT_TOKEN = None

        try:
            response = client.get("/api/telegram/set-webhook/")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "token" in data["message"].lower() or "bot" in data["message"].lower()
        finally:
            views.settings.TELEGRAM_BOT_TOKEN = original_token

    def test_delete_webhook_no_token(self, client):
        """Покрытие строк 177-179: delete_webhook без токена (без инициализации Application)"""
        from telegram_bot import views

        # Сохраняем оригинальный токен
        original_token = views.settings.TELEGRAM_BOT_TOKEN
        views.settings.TELEGRAM_BOT_TOKEN = None

        try:
            response = client.get("/api/telegram/delete-webhook/")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "token" in data["message"].lower() or "bot" in data["message"].lower()
        finally:
            views.settings.TELEGRAM_BOT_TOKEN = original_token

    def test_webhook_invalid_json(self, client):
        """Покрытие строк 132-135, 143-145: обработка невалидного JSON"""

        url = "/api/telegram/webhook/"
        response = client.post(url, data="invalid json", content_type="application/json")

        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "message" in data
