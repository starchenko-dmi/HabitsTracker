@echo off
echo Запуск Celery Worker...
poetry run celery -A config worker -l info --pool=solo
pause