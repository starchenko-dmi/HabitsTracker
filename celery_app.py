"""Скрипт для запуска Celery worker и beat"""

import signal
import subprocess
import sys


def start_celery_worker():
    """Запуск Celery worker"""
    print("🚀 Запуск Celery worker...")
    return subprocess.Popen(
        [
            "poetry",
            "run",
            "celery",
            "-A",
            "config",
            "worker",
            "-l",
            "info",
            "-Q",
            "default,reminders",
            "--pool=solo",  # Для Windows используем solo pool
        ]
    )


def start_celery_beat():
    """Запуск Celery beat"""
    print("⏰ Запуск Celery beat (планировщик задач)...")
    return subprocess.Popen(["poetry", "run", "celery", "-A", "config", "beat", "-l", "info"])


def signal_handler(sig, frame):
    """Обработчик сигнала для корректного завершения"""
    print("\n🛑 Остановка сервисов...")
    sys.exit(0)


if __name__ == "__main__":
    # Регистрируем обработчик сигнала
    signal.signal(signal.SIGINT, signal_handler)

    # Запускаем сервисы
    worker = start_celery_worker()
    beat = start_celery_beat()

    try:
        # Ждём завершения
        worker.wait()
        beat.wait()
    except KeyboardInterrupt:
        print("\n🛑 Остановка по запросу пользователя...")
    finally:
        # Завершаем процессы
        worker.terminate()
        beat.terminate()
