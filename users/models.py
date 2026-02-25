from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Кастомная модель пользователя с поддержкой Telegram"""

    email = models.EmailField(
        _('email address'),
        unique=True,
        blank=False,
        null=False,
    )

    telegram_chat_id = models.BigIntegerField(
        _('Telegram chat ID'),
        null=True,
        blank=True,
        help_text=_('ID чата пользователя в Telegram для отправки уведомлений')
    )

    telegram_username = models.CharField(
        _('Telegram username'),
        max_length=100,
        blank=True,
        null=True,
        help_text=_('Юзернейм пользователя в Telegram')
    )

    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
        ordering = ['username']

    def __str__(self):
        return self.email or self.username

    def has_telegram(self):
        """Проверка, привязан ли пользователь к Telegram"""
        return self.telegram_chat_id is not None

    has_telegram.boolean = True
    has_telegram.short_description = _('Привязан к Telegram')