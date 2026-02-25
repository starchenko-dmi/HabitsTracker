import pytest
from django.core.exceptions import ValidationError
from core.validators import HabitValidator
from habits.models import Habit
from users.models import User


@pytest.mark.django_db
class TestHabitValidator:
    """Тесты для валидатора привычек"""

    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='password123'
        )

    @pytest.fixture
    def pleasant_habit(self, user):
        return Habit.objects.create(
            user=user,
            place='Дом',
            time='08:00',
            action='Выпить чай',
            is_pleasant=True,
            duration=60
        )

    def test_valid_habit(self, user):
        """Тест валидной привычки"""
        data = {
            'user': user,
            'place': 'Дом',
            'time': '08:00',
            'action': 'Пробежка',
            'is_pleasant': False,
            'duration': 120,
            'periodicity': 1,
            'reward': 'Чашка кофе'
        }
        validator = HabitValidator()
        try:
            validator(data)
            assert True
        except ValidationError:
            pytest.fail("Валидная привычка не должна вызывать ошибку")

    def test_duration_exceeds_limit(self, user):
        """Тест времени выполнения > 120 секунд"""
        data = {
            'user': user,
            'place': 'Дом',
            'time': '08:00',
            'action': 'Пробежка',
            'duration': 121,
            'periodicity': 1
        }
        validator = HabitValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator(data)
        assert 'duration' in str(exc_info.value)

    def test_both_reward_and_related_habit(self, user, pleasant_habit):
        """Тест одновременного указания вознаграждения и связанной привычки"""
        data = {
            'user': user,
            'place': 'Дом',
            'time': '08:00',
            'action': 'Пробежка',
            'duration': 60,
            'periodicity': 1,
            'reward': 'Чашка кофе',
            'related_habit': pleasant_habit
        }
        validator = HabitValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator(data)
        assert 'reward' in str(exc_info.value)
        assert 'related_habit' in str(exc_info.value)

    def test_pleasant_habit_with_reward(self, user):
        """Тест приятной привычки с вознаграждением"""
        data = {
            'user': user,
            'place': 'Дом',
            'time': '08:00',
            'action': 'Выпить чай',
            'is_pleasant': True,
            'duration': 60,
            'periodicity': 1,
            'reward': 'Печенька'
        }
        validator = HabitValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator(data)
        assert 'reward' in str(exc_info.value)

    def test_pleasant_habit_with_related_habit(self, user, pleasant_habit):
        """Тест приятной привычки со связанной привычкой"""
        data = {
            'user': user,
            'place': 'Дом',
            'time': '08:00',
            'action': 'Выпить чай',
            'is_pleasant': True,
            'duration': 60,
            'periodicity': 1,
            'related_habit': pleasant_habit
        }
        validator = HabitValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator(data)
        assert 'related_habit' in str(exc_info.value)

    def test_periodicity_exceeds_limit(self, user):
        """Тест периодичности > 7 дней"""
        data = {
            'user': user,
            'place': 'Дом',
            'time': '08:00',
            'action': 'Пробежка',
            'duration': 60,
            'periodicity': 8
        }
        validator = HabitValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator(data)
        assert 'periodicity' in str(exc_info.value)

    def test_related_habit_not_pleasant(self, user):
        """Тест связанной привычки, которая не является приятной"""
        non_pleasant = Habit.objects.create(
            user=user,
            place='Дом',
            time='08:00',
            action='Пробежка',
            is_pleasant=False,
            duration=60
        )
        data = {
            'user': user,
            'place': 'Дом',
            'time': '08:00',
            'action': 'Зарядка',
            'duration': 60,
            'periodicity': 1,
            'related_habit': non_pleasant
        }
        validator = HabitValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator(data)
        assert 'related_habit' in str(exc_info.value)