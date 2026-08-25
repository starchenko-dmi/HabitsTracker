@echo off
echo Запуск всех сервисов...

start "Django Server" cmd /k "poetry run python manage.py runserver"
timeout /t 3 /nobreak > nul

start "Celery Worker" cmd /k "poetry run celery -A config worker -l info --pool=solo"
timeout /t 3 /nobreak > nul

start "Celery Beat" cmd /k "poetry run celery -A config beat -l info"

echo Все сервисы запущены!
pause