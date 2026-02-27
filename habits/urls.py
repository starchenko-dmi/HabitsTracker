from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import HabitViewSet

router = DefaultRouter()
router.register(r"", HabitViewSet, basename="habit")

urlpatterns = [
    path("", include(router.urls)),
]
