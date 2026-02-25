import os
from celery import Celery

# Устанавливаем модуль настроек Django по умолчанию для программы 'celery'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Создаём экземпляр Celery приложения
app = Celery('habits_tracker')

# Используем строку, чтобы воркеру не нужно было сериализовать
# объект конфигурации для дочерних процессов
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически загружаем задачи из всех зарегистрированных приложений Django
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """Отладочная задача для тестирования Celery"""
    print(f'Запрос: {self.request!r}')