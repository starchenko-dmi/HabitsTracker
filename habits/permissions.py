from django.utils.translation import gettext_lazy as _
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Разрешение, позволяющее только владельцу объекта редактировать его.
    Для остальных пользователей — только чтение.
    """

    message = _("У вас нет прав на изменение этой привычки.")

    def has_object_permission(self, request, view, obj):
        # Разрешаем чтение всем (для публичных привычек)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Разрешаем запись только владельцу объекта
        return obj.user == request.user
