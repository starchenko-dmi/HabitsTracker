from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import Habit
from core.validators import HabitValidator


class HabitSerializer(serializers.ModelSerializer):
    """Основной сериализатор для привычек"""

    # Поля только для чтения
    user = serializers.ReadOnlyField(source='user.email')
    is_useful = serializers.SerializerMethodField()

    class Meta:
        model = Habit
        fields = [
            'id',
            'user',
            'place',
            'time',
            'action',
            'is_pleasant',
            'related_habit',
            'periodicity',
            'reward',
            'duration',
            'is_public',
            'created_at',
            'last_completed',
            'next_reminder',
            'is_useful'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'is_useful']

    def get_is_useful(self, obj):
        """Получение признака полезной привычки"""
        return obj.is_useful()

    def validate(self, data):
        """
        Валидация на уровне сериализатора.
        Применяем комплексный валидатор.
        """
        # Получаем экземпляр объекта для обновления
        instance = self.instance

        # Создаём временный объект для валидации
        if instance:
            # Для обновления копируем существующий объект
            temp_habit = Habit(
                user=instance.user,
                place=data.get('place', instance.place),
                time=data.get('time', instance.time),
                action=data.get('action', instance.action),
                is_pleasant=data.get('is_pleasant', instance.is_pleasant),
                related_habit=data.get('related_habit', instance.related_habit),
                periodicity=data.get('periodicity', instance.periodicity),
                reward=data.get('reward', instance.reward),
                duration=data.get('duration', instance.duration),
                is_public=data.get('is_public', instance.is_public),
            )
        else:
            # Для создания нового объекта
            temp_habit = Habit(
                user=self.context['request'].user,
                place=data.get('place'),
                time=data.get('time'),
                action=data.get('action'),
                is_pleasant=data.get('is_pleasant', False),
                related_habit=data.get('related_habit'),
                periodicity=data.get('periodicity', 1),
                reward=data.get('reward'),
                duration=data.get('duration'),
                is_public=data.get('is_public', False),
            )

        # Применяем валидатор
        validator = HabitValidator()
        try:
            validator(temp_habit)
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(str(e))

        return data

    def create(self, validated_data):
        """Создание привычки с автоматическим присвоением пользователя"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class HabitCreateUpdateSerializer(HabitSerializer):
    """Сериализатор для создания и обновления привычек"""

    class Meta(HabitSerializer.Meta):
        read_only_fields = ['id', 'created_at', 'user', 'is_useful', 'last_completed', 'next_reminder']


class PublicHabitSerializer(serializers.ModelSerializer):
    """Сериализатор для публичных привычек (без чувствительных данных)"""

    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Habit
        fields = [
            'id',
            'user',
            'place',
            'time',
            'action',
            'is_pleasant',
            'periodicity',
            'duration',
            'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']


class RelatedHabitSerializer(serializers.ModelSerializer):
    """Сериализатор для выбора связанной привычки (только приятные привычки)"""

    class Meta:
        model = Habit
        fields = ['id', 'action', 'is_pleasant', 'duration']
        read_only_fields = ['id', 'action', 'is_pleasant', 'duration']