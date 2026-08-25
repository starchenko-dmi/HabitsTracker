from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HabitsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "habits"
    verbose_name = _("Привычки")
