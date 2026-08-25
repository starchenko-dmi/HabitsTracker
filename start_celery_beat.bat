@echo off
echo Запуск Celery Beat...
poetry run celery -A config beat -l info
pause