# Трекер полезных привычек (HabitsTracker)

Бэкенд SPA-приложения для формирования и отслеживания привычек по методике Джеймса Клира «Атомные привычки». Реализует единую бизнес-логику для веб-API и Telegram-бота, обеспечивая синхронизацию данных и точные напоминания.

## 📖 Описание проекта

Приложение помогает пользователям внедрять микро-привычки (до 2 минут), связывая полезные действия с приятными вознаграждениями. Ключевая особенность — **бесшовная интеграция**: создание привычки через API или бот подчиняется единым правилам валидации, а напоминания отправляются точно в назначенное время через Celery + Telegram API.

### Возможности
- Создание/редактирование привычек с валидацией бизнес-правил
- Система «триггер → действие → награда» (полезная ↔ приятная привычка)
- Публичная лента идей для вдохновения
- Ежеминутные напоминания в Telegram с учетом часового пояса Asia/Novosibirsk
- Проверка неактивных привычек (>7 дней без выполнения)
- Полное покрытие тестами (82%) и линтинг Flake8

---

## 🏗️ Архитектура и ключевые решения

Проект спроектирован с акцентом на консистентность данных и масштабируемость:

1.  **Единый слой валидации (`HabitValidator`)**  
    Бизнес-правила инкапсулированы в независимый класс, который работает как с моделями Django, так и со словарями сериализаторов. Это гарантирует идентичную проверку при создании через API, админку или Telegram-бот.

2.  **Асинхронная безопасная работа с БД**  
    Telegram-бот использует `ConversationHandler` для пошаговых диалогов. Все операции с ORM обернуты в декоратор `@sync_to_async`, что позволяет безопасно обращаться к базе данных внутри асинхронного цикла событий без блокировок.

3.  **Независимая отправка уведомлений**  
    Задачи Celery (`send_habit_reminders`) используют утилиту `send_message` на прямых HTTP-запросах к Telegram API. Это устраняет зависимость от polling-цикла бота и позволяет отправлять напоминания даже если основной процесс бота перезагружается.

4.  **Кастомные менеджеры QuerySet**  
    Фильтрация данных вынесена в методы `HabitQuerySet` (`public()`, `pleasant()`, `useful()`). ViewSet остаются декларативными, а логика фильтрации переиспользуется в разных контекстах (API, бот, задачи).

5.  **Модель данных**  
    Кастомная модель `User` наследует `AbstractUser` и связана с `Habit` через ForeignKey (CASCADE). Привычки могут ссылаться друг на друга (`related_habit`) для реализации методики триггеров. Валидация на уровне модели (`full_clean()`) защищает целостность данных при любом способе сохранения.

---

## ⚙️ Бизнес-правила валидации

Система строго контролирует корректность данных:
- ⛔ Нельзя одновременно указать вознаграждение и связанную привычку
- ️ Время выполнения ≤ 120 секунд
- 😊 Связанная привычка должна быть обязательно «приятной»
- 🚫 У приятной привычки не может быть награды или связанной привычки
- 📅 Периодичность ≤ 7 дней

---

## 🚀 Быстрый старт

### Предварительные требования
- Python 3.10+
- Poetry
- Redis (для Celery)
- SQLite (по умолчанию) или PostgreSQL

### Установка и запуск

1.  Клонируйте репозиторий:
    ```bash
    git clone https://github.com/starchenko-dmi/HabitsTracker.git
    cd HabitsTracker
    ```

2.  Установите зависимости:
    ```bash
    poetry install
    ```

3.  Создайте и настройте файл окружения:
    ```bash
    cp .env.example .env
    ```
    Откройте `.env` и заполните ключевые параметры:
    ```env
    SECRET_KEY=your-secret-key-here
    DEBUG=True
    ALLOWED_HOSTS=localhost,127.0.0.1
    DB_ENGINE=django.db.backends.sqlite3
    DB_NAME=db.sqlite3
    TELEGRAM_BOT_TOKEN=your_bot_token_here
    CELERY_BROKER_URL=redis://localhost:6379/0
    CELERY_RESULT_BACKEND=redis://localhost:6379/0
    TIME_ZONE=Asia/Novosibirsk
    ```

4.  Примените миграции и создайте суперпользователя:
    ```bash
    poetry run python manage.py migrate
    poetry run python manage.py createsuperuser
    ```

5.  Запустите сервер разработки:
    ```bash
    poetry run python manage.py runserver
    ```

6.  **(Опционально)** Запустите фоновые задачи:
    ```bash
    # Терминал 1: Worker
    poetry run celery -A config worker -l info --pool=solo
    
    # Терминал 2: Beat (планировщик)
    poetry run celery -A config beat -l info
    ```
    > 💡 Для Windows используйте скрипт `start_all_services.bat`

---

## 📚 Документация API

После запуска сервера документация доступна по адресам:
- Swagger UI: `/swagger/`
- ReDoc: `/redoc/`

![Swagger UI](docs/swagger-screenshot.png)
*Интерфейс автоматической документации API*

### Основные эндпоинты

| Метод | URL | Описание |
| :--- | :--- | :--- |
| POST | `/api/auth/users/` | Регистрация пользователя |
| POST | `/api/auth/jwt/create/` | Получение JWT токена |
| GET | `/api/habits/` | Список привычек текущего пользователя |
| POST | `/api/habits/` | Создание новой привычки |
| GET | `/api/habits/public/` | Публичная лента привычек |
| GET | `/api/habits/pleasant/` | Приятные привычки (для выбора триггера) |

### Примеры запросов и ответов

#### Создание полезной привычки с вознаграждением
**Request:**
```http
POST /api/habits/
Authorization: Bearer <ваш_токен>
Content-Type: application/json

{
    "place": "Дома",
    "time": "08:00",
    "action": "Утренняя зарядка",
    "duration": 120,
    "periodicity": 1,
    "reward": "Чашка кофе"
}
```

**Response (201 Created):**
```json
{
    "id": 15,
    "user": "dmitry@example.com",
    "place": "Дома",
    "time": "08:00:00",
    "action": "Утренняя зарядка",
    "is_pleasant": false,
    "related_habit": null,
    "periodicity": 1,
    "reward": "Чашка кофе",
    "duration": 120,
    "is_public": false,
    "created_at": "2026-08-26T10:00:00Z",
    "last_completed": null,
    "next_reminder": null,
    "is_useful": true
}
```

#### Ошибка валидации (нарушение бизнес-правил)
**Request:**
```json
{
    "place": "Дома",
    "time": "08:00",
    "action": "Тест",
    "duration": 150,
    "reward": "Кофе",
    "related_habit": 5
}
```

**Response (400 Bad Request):**
```json
{
    "duration": ["Время выполнения привычки не должно превышать 120 секунд."],
    "reward": ["Нельзя одновременно указывать вознаграждение и связанную привычку."],
    "related_habit": ["Нельзя одновременно указывать вознаграждение и связанную привычку."]
}
```

---

## 🧪 Тестирование и качество кода

```bash
# Запуск всех тестов
poetry run pytest

# Отчет о покрытии (HTML)
poetry run pytest --cov=habits --cov=users --cov=telegram_bot --cov-report=html
start htmlcov/index.html

# Линтинг
poetry run flake8

# Форматирование
poetry run black .
```

**Статистика качества:**
- ✅ Покрытие кода: **82%**
- ✅ Количество тестов: **32**
- ✅ Flake8: **0 ошибок**

---

## ️ Технологический стек

**Backend & API:**
- Python 3.13.5
- Django 4.2 + DRF 3.14
- Djoser 2.2 (JWT Auth)
- drf-yasg 1.21 (Swagger/ReDoc)
- django-filter, django-cors-headers

**Async & Tasks:**
- Celery 5.3 + Redis 5.0
- python-telegram-bot 20.6

**DevOps & Quality:**
- Poetry (dependency management)
- pytest + pytest-cov + factory-boy
- flake8 + black
- dotenv

---

##  Безопасность

- Переменные окружения изолированы в `.env` (`.gitignore` настроен)
- JWT-аутентификация с ротацией refresh-токенов
- Права доступа `IsOwnerOrReadOnly`: пользователи видят только свои данные
- CORS ограничен конкретными origin'ами фронтенда
- Валидация входных данных на всех уровнях (сериализатор → модель → задача)

---

## 👤 Автор

**Дмитрий Старченко**  
📧 Starchenko.Dmitr@mail.ru  
 GitHub: [ваш-логин](https://github.com/starchenko-dmi/)

> *«Маленькие привычки создают большую жизнь»*

Лицензия: MIT