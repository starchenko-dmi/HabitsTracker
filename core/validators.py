from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class HabitValidator:
    """
    Комплексный валидатор для модели привычки.

    Проверяет все бизнес-правила:
    1. Исключает одновременный выбор связанной привычки и вознаграждения
    2. Ограничивает время выполнения до 120 секунд
    3. Проверяет, что связанная привычка является приятной
    4. Проверяет, что у приятной привычки нет вознаграждения и связанной привычки
    5. Ограничивает периодичность до 7 дней
    """

    def __call__(self, data):
        # Извлекаем данные из сериализатора или модели
        is_pleasant = data.get('is_pleasant', False) if isinstance(data, dict) else getattr(data, 'is_pleasant', False)
        reward = data.get('reward', None) if isinstance(data, dict) else getattr(data, 'reward', None)
        related_habit = data.get('related_habit', None) if isinstance(data, dict) else getattr(data, 'related_habit',
                                                                                               None)
        duration = data.get('duration', None) if isinstance(data, dict) else getattr(data, 'duration', None)
        periodicity = data.get('periodicity', None) if isinstance(data, dict) else getattr(data, 'periodicity', None)

        errors = {}

        # Правило 1: Исключить одновременный выбор связанной привычки и вознаграждения
        if reward and related_habit:
            errors['reward'] = _('Нельзя одновременно указывать вознаграждение и связанную привычку.')
            errors['related_habit'] = _('Нельзя одновременно указывать вознаграждение и связанную привычку.')

        # Правило 2: Время выполнения не должно превышать 120 секунд
        if duration and duration > 120:
            errors['duration'] = _('Время выполнения привычки не должно превышать 120 секунд.')

        # Правило 3: Связанная привычка должна быть приятной
        if related_habit:
            if not related_habit.is_pleasant:
                errors['related_habit'] = _('Связанная привычка должна быть приятной привычкой.')

        # Правило 4: У приятной привычки не может быть вознаграждения или связанной привычки
        if is_pleasant:
            if reward:
                errors['reward'] = _('У приятной привычки не может быть вознаграждения.')
            if related_habit:
                errors['related_habit'] = _('У приятной привычки не может быть связанной привычки.')

        # Правило 5: Периодичность не должна превышать 7 дней
        if periodicity and periodicity > 7:
            errors['periodicity'] = _('Нельзя выполнять привычку реже, чем раз в 7 дней.')

        # Если есть ошибки, выбрасываем исключение
        if errors:
            raise ValidationError(errors)