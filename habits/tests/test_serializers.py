import pytest
from datetime import time
from rest_framework.exceptions import ValidationError
from habits.serializers import HabitSerializer, HabitCreateUpdateSerializer
from habits.models import Habit
from users.models import User


@pytest.mark.django_db
class TestHabitSerializer:
    """Тесты для сериализаторов привычек"""

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
            time=time(8, 0),
            action='Выпить чай',
            is_pleasant=True,
            duration=60
        )

    def test_valid_habit_serializer(self, user):
        """Тест валидного сериализатора привычки"""
        data = {
            'place': 'Дом',
            'time': '08:00',
            'action': 'Пробежка',
            'duration': 120,
            'periodicity': 1,
            'reward': 'Чашка кофе'
        }
        serializer = HabitCreateUpdateSerializer(data=data,
                                                 context={'request': type('obj', (object,), {'user': user})()})
        assert serializer.is_valid(), serializer.errors
        habit = serializer.save(user=user)
        assert habit.action == 'Пробежка'
        assert habit.reward == 'Чашка кофе'

    def test_duration_exceeds_limit(self, user):
        """Тест времени выполнения > 120 секунд"""
        data = {
            'place': 'Дом',
            'time': '08:00',
            'action': 'Пробежка',
            'duration': 121,
            'periodicity': 1
        }
        serializer = HabitCreateUpdateSerializer(data=data,
                                                 context={'request': type('obj', (object,), {'user': user})()})
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors or 'duration' in str(serializer.errors)

    def test_both_reward_and_related_habit(self, user, pleasant_habit):
        """Тест одновременного указания вознаграждения и связанной привычки"""
        data = {
            'place': 'Дом',
            'time': '08:00',
            'action': 'Пробежка',
            'duration': 60,
            'periodicity': 1,
            'reward': 'Чашка кофе',
            'related_habit': pleasant_habit.id
        }
        serializer = HabitCreateUpdateSerializer(
            data=data,
            context={'request': type('obj', (object,), {'user': user})()}
        )
        assert not serializer.is_valid()

    def test_pleasant_habit_with_reward(self, user):
        """Тест приятной привычки с вознаграждением"""
        data = {
            'place': 'Дом',
            'time': '08:00',
            'action': 'Выпить чай',
            'is_pleasant': True,
            'duration': 60,
            'periodicity': 1,
            'reward': 'Печенька'
        }
        serializer = HabitCreateUpdateSerializer(data=data,
                                                 context={'request': type('obj', (object,), {'user': user})()})
        assert not serializer.is_valid()

    def test_periodicity_exceeds_limit(self, user):
        """Тест периодичности > 7 дней"""
        data = {
            'place': 'Дом',
            'time': '08:00',
            'action': 'Пробежка',
            'duration': 60,
            'periodicity': 8
        }
        serializer = HabitCreateUpdateSerializer(data=data,
                                                 context={'request': type('obj', (object,), {'user': user})()})
        assert not serializer.is_valid()