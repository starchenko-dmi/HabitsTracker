from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Habit
from .permissions import IsOwnerOrReadOnly
from .serializers import HabitCreateUpdateSerializer, HabitSerializer, PublicHabitSerializer, RelatedHabitSerializer


class HabitViewSet(viewsets.ModelViewSet):
    """
    Представление для управления привычками.

    Доступные действия:
    - list: Список привычек текущего пользователя (с пагинацией)
    - create: Создание новой привычки
    - retrieve: Просмотр деталей привычки
    - update: Обновление привычки
    - destroy: Удаление привычки
    - public: Список публичных привычек
    - pleasant: Список приятных привычек для выбора как связанной
    """

    queryset = Habit.objects.all()
    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_pleasant", "is_public", "periodicity"]
    search_fields = ["action", "place"]
    ordering_fields = ["time", "created_at", "periodicity"]
    ordering = ["time"]

    def get_queryset(self):
        """
        Возвращает привычки текущего пользователя.
        Для публичных привычек используется отдельный эндпоинт.
        """
        if self.action == "public":
            return Habit.objects.public()
        return Habit.objects.user_habits(self.request.user)

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action in ["create", "update", "partial_update"]:
            return HabitCreateUpdateSerializer
        elif self.action == "public":
            return PublicHabitSerializer
        elif self.action == "pleasant":
            return RelatedHabitSerializer
        return HabitSerializer

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def public(self, request):
        """
        Получение списка публичных привычек.

        Возвращает все публичные привычки всех пользователей.
        Пользователь может только просматривать, но не редактировать или удалять.
        """
        public_habits = Habit.objects.public()
        page = self.paginate_queryset(public_habits)
        if page is not None:
            serializer = PublicHabitSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)

        serializer = PublicHabitSerializer(public_habits, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def pleasant(self, request):
        """
        Получение списка приятных привычек текущего пользователя.

        Используется для выбора связанной привычки при создании полезной привычки.
        """
        pleasant_habits = Habit.objects.user_habits(request.user).pleasant()
        serializer = RelatedHabitSerializer(pleasant_habits, many=True, context={"request": request})
        return Response(serializer.data)
