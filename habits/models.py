from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.validators import HabitValidator
from habits.managers import HabitManager


class Habit(models.Model):
    """Модель привычки"""

    # Основные поля
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="habits",
        verbose_name=_("Пользователь"),
        help_text=_("Создатель привычки"),
    )

    place = models.CharField(
        max_length=255, verbose_name=_("Место"), help_text=_("Место, в котором необходимо выполнять привычку")
    )

    time = models.TimeField(verbose_name=_("Время"), help_text=_("Время, когда необходимо выполнять привычку"))

    action = models.CharField(
        max_length=255, verbose_name=_("Действие"), help_text=_("Действие, которое представляет собой привычка")
    )

    # Признак приятной привычки
    is_pleasant = models.BooleanField(
        default=False,
        verbose_name=_("Признак приятной привычки"),
        help_text=_("Привычка, которую можно привязать к выполнению полезной привычки"),
    )

    # Связанная привычка (для полезных привычек)
    related_habit = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_habits",
        verbose_name=_("Связанная привычка"),
        help_text=_("Привычка, которая связана с другой привычкой (только для полезных привычек)"),
    )

    # Периодичность (по умолчанию ежедневно)
    periodicity = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
        verbose_name=_("Периодичность"),
        help_text=_("Периодичность выполнения привычки в днях (от 1 до 7)"),
    )

    # Вознаграждение
    reward = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Вознаграждение"),
        help_text=_("Чем пользователь должен себя вознаградить после выполнения"),
    )

    # Время на выполнение (в секундах)
    duration = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(120)],
        verbose_name=_("Время на выполнение"),
        help_text=_("Время на выполнение привычки в секундах (не более 120)"),
    )

    # Признак публичности
    is_public = models.BooleanField(
        default=False,
        verbose_name=_("Признак публичности"),
        help_text=_("Привычка доступна для просмотра другими пользователями"),
    )

    # Дата создания
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))

    # Дата последнего выполнения
    last_completed = models.DateField(null=True, blank=True, verbose_name=_("Дата последнего выполнения"))

    # Следующая дата выполнения (для напоминаний)
    next_reminder = models.DateTimeField(null=True, blank=True, verbose_name=_("Следующее напоминание"))

    objects = HabitManager()

    # Валидатор на уровне модели
    class Meta:
        verbose_name = _("Привычка")
        verbose_name_plural = _("Привычки")
        ordering = ["time", "created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.action} в {self.place} в {self.time}"

    def clean(self):
        """Валидация модели перед сохранением"""
        HabitValidator()(self)
        super().clean()

    def save(self, *args, **kwargs):
        """Переопределение метода save для валидации"""
        self.full_clean()
        super().save(*args, **kwargs)

    def is_useful(self):
        """Проверка, является ли привычка полезной (не приятной)"""
        return not self.is_pleasant

    is_useful.boolean = True
    is_useful.short_description = _("Полезная привычка")
