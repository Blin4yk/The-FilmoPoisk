# The-FilmoPoisk

Онлайн-кинотеатр с системой авторизации и управления доступом на основе ролей.

## Описание проекта

The-FilmoPoisk - это сервис для онлайн-кинотеатра, построенный на FastAPI. Проект включает в себя:
- API для работы с фильмами (поиск, просмотр, фильтрация)
- Систему авторизации с JWT токенами
- Управление ролями и правами доступа
- Контроль доступа к контенту на основе подписки

## Технологический стек

- **FastAPI** - современный веб-фреймворк для создания API
- **PostgreSQL** - реляционная база данных для хранения пользователей, ролей и истории входов
- **Elasticsearch** - поисковый движок для фильмов
- **Redis** - кэширование и хранение blacklist токенов
- **SQLAlchemy** (async) - ORM для работы с БД
- **Alembic** - миграции базы данных
- **JWT** - токены доступа (access и refresh)
- **Pydantic** - валидация данных
- **Python-jose** - работа с JWT токенами
- **Passlib** - хеширование паролей (bcrypt)

## Архитектура

Проект следует принципам чистой архитектуры:
- **API Layer** - эндпоинты REST API (`api/v1/`)
- **Service Layer** - бизнес-логика (`services/`)
- **Repository Layer** - работа с БД (`db/repositories/`)
- **Model Layer** - SQLAlchemy модели (`models/`)
- **Dependency Layer** - FastAPI зависимости (`api/v1/dependencies/`)

## Установка и запуск

### Требования

- Docker и Docker Compose
- Python 3.12+
- (Опционально) PostgreSQL, Redis, Elasticsearch для локальной разработки

### Переменные окружения

Создайте файл `.env` в корне проекта или установите переменные окружения:

```env
# Application
PROJECT_NAME=FilmoPoisk
ENVIRONMENT=development

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=auth_db
POSTGRES_USER=auth_user
POSTGRES_PASSWORD=auth_password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Elasticsearch
ELASTIC_HOST=elasticsearch-with-dump
ELASTIC_PORT=9200

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Запуск через Docker Compose

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd The-FilmoPoisk
```

2. Запустите все сервисы:
```bash
cd run
docker-compose -f docker-compose-local.yaml up -d
```

3. Дождитесь запуска всех сервисов (особенно PostgreSQL и Elasticsearch).

4. Выполните миграции базы данных:
```bash
# Войдите в контейнер FastAPI
docker exec -it fastapi bash

# Запустите миграции
alembic upgrade head
```

5. Создайте суперпользователя:
```bash
# В контейнере или локально
python -m cli create-superuser --username admin --email admin@example.com --password your_secure_password
```

6. Откройте API документацию:
- Swagger UI: http://localhost:8000/api/openapi

### Локальная разработка

1. Установите зависимости:
```bash
cd src
pip install -r requirements.txt
```

2. Запустите только инфраструктуру (PostgreSQL, Redis, Elasticsearch):
```bash
cd run
docker-compose -f docker-compose-local.yaml up -d postgres redis elasticsearch-with-dump
```

3. Выполните миграции:
```bash
cd src
alembic upgrade head
```

4. Запустите приложение:
```bash
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Документация

После запуска приложения доступна интерактивная документация:
- Swagger UI: http://localhost:8000/api/openapi

### Основные эндпоинты

#### Аутентификация (`/api/v1/auth`)
- `POST /api/v1/auth/register` - Регистрация пользователя
- `POST /api/v1/auth/login` - Вход в систему (получение токенов)
- `POST /api/v1/auth/refresh` - Обновление access токена
- `POST /api/v1/auth/logout` - Выход из системы
- `POST /api/v1/auth/logout-all` - Выход из всех устройств
- `PATCH /api/v1/auth/profile` - Изменение профиля (логин/пароль)
- `GET /api/v1/auth/login-history` - История входов

#### Управление ролями (`/api/v1/roles`)
- `POST /api/v1/roles/` - Создание роли (требуется admin)
- `GET /api/v1/roles/` - Список всех ролей (требуется admin)
- `GET /api/v1/roles/{role_id}` - Получение роли (требуется admin)
- `PATCH /api/v1/roles/{role_id}` - Изменение роли (требуется admin)
- `DELETE /api/v1/roles/{role_id}` - Удаление роли (требуется admin)
- `POST /api/v1/roles/{role_id}/assign/{user_id}` - Назначение роли (требуется admin)
- `DELETE /api/v1/roles/{role_id}/revoke/{user_id}` - Отзыв роли (требуется admin)
- `POST /api/v1/roles/check-permission` - Проверка прав доступа

#### Фильмы (`/api/v1/films`)
- `GET /api/v1/films/` - Список фильмов с фильтрацией и сортировкой
- `GET /api/v1/films/{film_id}` - Детали фильма
- `GET /api/v1/films/search/` - Поиск фильмов

## Миграции базы данных

Проект использует Alembic для управления миграциями.

### Создание миграции

```bash
cd src
alembic revision --autogenerate -m "Description of changes"
```

### Применение миграций

```bash
cd src
alembic upgrade head
```

### Откат миграции

```bash
cd src
alembic downgrade -1
```

## CLI Команды

### Создание суперпользователя

```bash
# Интерактивный режим
python -m cli create-superuser

# С параметрами
python -m cli create-superuser --username admin --email admin@example.com --password secure_password
```

## Тестирование

Запуск тестов:
```bash
cd run
docker-compose -f docker-compose-local.yaml up tests
```

Или локально:
```bash
cd src
pytest tests/ -v
```

## Структура проекта

```
The-FilmoPoisk/
├── src/                    # Исходный код приложения
│   ├── api/               # API эндпоинты
│   │   └── v1/
│   │       ├── auth.py    # Эндпоинты авторизации
│   │       ├── roles.py   # Эндпоинты управления ролями
│   │       ├── films.py   # Эндпоинты фильмов
│   │       ├── scheme/    # Pydantic схемы
│   │       └── dependencies/  # FastAPI зависимости
│   ├── core/              # Ядро приложения
│   │   ├── config.py      # Конфигурация
│   │   ├── jwt.py         # JWT утилиты
│   │   └── security.py    # Безопасность (хеширование паролей)
│   ├── db/                # Работа с БД
│   │   ├── postgres.py    # PostgreSQL подключение
│   │   ├── repositories/  # Репозитории
│   │   └── interfaces/    # Интерфейсы хранилищ
│   ├── models/            # SQLAlchemy модели
│   │   ├── user.py        # Модель пользователя
│   │   └── role.py        # Модели ролей
│   ├── services/          # Бизнес-логика
│   │   ├── auth.py        # Сервис авторизации
│   │   ├── role.py        # Сервис ролей
│   │   ├── permission.py  # Сервис проверки разрешений
│   │   └── film.py        # Сервис фильмов
│   ├── cli/               # CLI команды
│   │   ├── create_superuser.py
│   │   └── __main__.py
│   ├── alembic/           # Миграции БД
│   │   ├── env.py
│   │   ├── versions/      # Файлы миграций
│   │   └── script.py.mako
│   └── main.py            # Точка входа
├── run/                   # Docker Compose файлы
├── tests/                 # Тесты
│   └── functional/
│       ├── test_auth.py   # Тесты авторизации
│       └── test_films.py  # Тесты фильмов
├── alembic.ini            # Конфигурация Alembic
├── ARCHITECTURE.md        # Архитектурная документация
└── README.md              # Этот файл
```

## Система прав доступа

### Роли

- **subscriber** - подписчик (доступ к новым фильмам)
- **admin** - администратор (управление ролями)

### Суперпользователь

Суперпользователь (`is_superuser=True`) имеет все права и обходит проверки ролей.

### Анонимные пользователи

Анонимные пользователи имеют доступ ко всем ресурсам, которые не требуют специальных прав (например, фильмы старше 3 лет).

## Безопасность

- Пароли хранятся в виде bcrypt хешей (cost factor 12)
- JWT токены с коротким временем жизни (access: 15 мин, refresh: 7 дней)
- Refresh токены могут быть отозваны (blacklist в Redis)
- Валидация всех входных данных через Pydantic
- Защита от SQL injection через SQLAlchemy ORM

## Производительность

- Кэширование информации о пользователях в Redis (TTL 5 минут)
- Кэширование ролей пользователей (TTL 10 минут)
- Индексы в PostgreSQL для быстрых запросов
- Пагинация всех списков (максимум 100 элементов на страницу)

## Changelog

### Спринт 6 - Система авторизации и управления ролями

#### Реализовано

- ✅ Настройка PostgreSQL и подключение к БД
- ✅ SQLAlchemy модели для пользователей, ролей, истории входов, refresh токенов
- ✅ Репозитории для работы с БД
- ✅ JWT сервис для создания и валидации токенов
- ✅ API для авторизации:
  - Регистрация пользователя
  - Вход в систему (получение токенов)
  - Обновление access токена
  - Выход из системы
  - Выход из всех устройств (logout-all)
  - Изменение логина/пароля
  - Получение истории входов
- ✅ CRUD API для управления ролями (требуется admin)
- ✅ Назначение и отзыв ролей пользователям
- ✅ Проверка прав доступа
- ✅ CLI команда для создания суперпользователя
- ✅ Система зависимостей для проверки авторизации и кэширование в Redis
- ✅ Обработка ошибок и валидация во всех эндпоинтах
- ✅ Интеграция системы разрешений с API фильмов
- ✅ Миграции Alembic
- ✅ Базовые функциональные тесты для API авторизации

#### В разработке / TODO

- ⏳ Доработка ETL-процесса для добавления поля creation_date/release_date в Elasticsearch индексе фильмов
- ⏳ Расширение тестового покрытия (unit-тесты для сервисов, больше edge cases)
- ⏳ Хочу вынести в отдельный микросервис авторизацию
## Участники проекта

- **Я** - реализация системы авторизации, управления ролями, API эндпоинтов

## Полезные команды

```bash
# Просмотр логов
docker-compose -f run/docker-compose-local.yaml logs -f fastapi

# Остановка всех сервисов
docker-compose -f run/docker-compose-local.yaml down

# Пересборка контейнеров
docker-compose -f run/docker-compose-local.yaml build --no-cache

# Очистка данных (ВНИМАНИЕ: удалит все данные)
docker-compose -f run/docker-compose-local.yaml down -v

# Проверка статуса сервисов
docker-compose -f run/docker-compose-local.yaml ps

# Выполнение команды в контейнере
docker exec -it fastapi bash
```