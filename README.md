# GeekCodeBattle

GeekCodeBattle — платформа очных батлов по программированию для школьников.

## Что реализовано

- Backend: Flask + SQLAlchemy + Socket.IO + Alembic
- Frontend: Vue 3 + Vite + Socket.IO client
- PostgreSQL + Redis
- JWT авторизация (GeekClass) + dev-login
- Битвы: `open-lobby -> start -> stop -> finish`
- Матчмейкинг с поддержкой комнат 2..N
- Спец-правило: при нечетном числе и `room_size=2` создается комната из 3
- Проверка решений через GeekPasteV2 (`tests|gpt`)
- Callback с проверкой подписи, `iat`, дедупликацией
- Финализация раундов, pairwise Elo, очки, streak-бонусы
- Rejudge для teacher/admin
- Realtime события: queue/match/round/leaderboard/status

## Production запуск (server)

1. Подготовьте переменные:

```bash
cp .env.example .env
# заполните SECRET_KEY, JWT_SECRET, GEEKPASTE_API_URL, пароли БД
```

2. Запустите:

```bash
docker compose up -d --build
```

3. Сервис доступен на `http://<server-ip>` (frontend через Nginx на порту 80).

Особенности production compose:
- frontend — статическая сборка в Nginx
- backend — `gunicorn + eventlet`
- фоновые задачи — `celery_worker + celery_beat`
- миграции (`flask db upgrade`) выполняются на старте backend контейнера
- dev-сервера Vite нет

## Development запуск

Используйте отдельный файл:

```bash
docker compose -f docker-compose.dev.yml up --build
```

- Frontend dev server: `http://localhost:5173`
- Backend API: `http://localhost:8090`

## Миграции

Миграции находятся в `backend/migrations`.

Команды:

```bash
cd backend
export FLASK_APP=manage:app
flask db upgrade
```

## Тесты backend

```bash
cd backend
python3 -m pytest -q
```

## Важные env-параметры

- `MATCHMAKING_DELAY_SECONDS` — задержка перед стартом раунда, чтобы улучшить подбор
- `ROUND_DURATION_MINUTES` — лимит раунда
- `DISCONNECT_GRACE_SECONDS` — grace-период при полном дисконнекте комнаты
- `ROUND_TIMEOUT_POLL_SECONDS` — период celery beat-проверки таймаутов
- `CELERY_ENABLED` — включение celery-задач
- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` — broker/backend celery
- `GEEKPASTE_CALLBACK_*` — параметры верификации callback
- `SUBMISSION_CHECK_TIMEOUT_SECONDS` — через сколько секунд ожидания callback посылка автоматически помечается как невыполненная (по умолчанию `180`)
- `AUTO_CREATE_DB` — автосоздание таблиц на startup (рекомендуется `false`, использовать `true` только для временных локальных экспериментов без Alembic)
