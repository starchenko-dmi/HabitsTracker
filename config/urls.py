from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Habits Tracker API",
        default_version="v1",
        description="API для трекера полезных привычек по методике Джеймса Клира",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@habits.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Админка Django
    path("admin/", admin.site.urls),
    # Эндпоинты аутентификации Djoser
    path("api/auth/", include("djoser.urls")),
    path("api/auth/", include("djoser.urls.jwt")),
    # Пользователи
    path("api/", include("users.urls")),
    # Привычки
    path("api/habits/", include("habits.urls")),
    # Telegram бот
    path("api/telegram/", include("telegram_bot.urls")),
    # Документация API
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]

# Раздача медиа и статических файлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
