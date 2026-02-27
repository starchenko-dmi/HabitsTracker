@echo off
title Django Server
echo Запуск Django сервера...
poetry run python manage.py runserver
pause