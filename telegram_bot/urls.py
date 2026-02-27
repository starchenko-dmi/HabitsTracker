from django.urls import path

from . import views

urlpatterns = [
    # Вебхук для получения обновлений от Telegram
    path("webhook/", views.telegram_webhook, name="telegram_webhook"),
    # Установка вебхука
    path("set-webhook/", views.set_webhook, name="set_webhook"),
    # Удаление вебхука
    path("delete-webhook/", views.delete_webhook, name="delete_webhook"),
]
