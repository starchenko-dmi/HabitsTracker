from django.urls import resolve, reverse

from telegram_bot import views


class TestUrls:
    """Тесты маршрутов Telegram бота"""

    def test_webhook_url_resolves(self):
        """Проверка разрешения маршрута вебхука"""
        url = reverse("telegram_webhook")
        assert url == "/api/telegram/webhook/"

        resolver = resolve(url)
        assert resolver.func == views.telegram_webhook
        assert resolver.kwargs == {}

    def test_set_webhook_url_resolves(self):
        """Проверка разрешения маршрута установки вебхука"""
        url = reverse("set_webhook")
        assert url == "/api/telegram/set-webhook/"

        resolver = resolve(url)
        assert resolver.func == views.set_webhook
        assert resolver.kwargs == {}

    def test_delete_webhook_url_resolves(self):
        """Проверка разрешения маршрута удаления вебхука"""
        url = reverse("delete_webhook")
        assert url == "/api/telegram/delete-webhook/"

        resolver = resolve(url)
        assert resolver.func == views.delete_webhook
        assert resolver.kwargs == {}
