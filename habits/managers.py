from django.db import models


class HabitQuerySet(models.QuerySet):
    """Кастомный QuerySet для привычек"""

    def public(self):
        """Фильтр только публичных привычек"""
        return self.filter(is_public=True)

    def user_habits(self, user):
        """Привычки конкретного пользователя"""
        return self.filter(user=user)

    def pleasant(self):
        """Только приятные привычки"""
        return self.filter(is_pleasant=True)

    def useful(self):
        """Только полезные привычки"""
        return self.filter(is_pleasant=False)


class HabitManager(models.Manager):
    """Кастомный менеджер для привычек"""

    def get_queryset(self):
        return HabitQuerySet(self.model, using=self._db)

    def public(self):
        return self.get_queryset().public()

    def user_habits(self, user):
        return self.get_queryset().user_habits(user)

    def pleasant(self):
        return self.get_queryset().pleasant()

    def useful(self):
        return self.get_queryset().useful()
