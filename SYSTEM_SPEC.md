# GeekCodeBattle — Подробное ТЗ для кодогенерации (MVP)

## 1. Назначение документа
Этот документ является единственным источником требований для автоматической кодогенерации проекта **GeekCodeBattle**.
Все решения в коде должны следовать этому документу. Если пункт не определен, использовать безопасное и минимальное поведение без усложнений.

## 2. Цель продукта
Система проводит очные батлы по программированию среди школьников:
- в батле участвует множество учеников,
- ученики распределяются по комнатам раунда,
- получают задачу,
- победитель раунда определяется по времени **первой accepted-попытки**.
- размер комнаты настраиваемый (`room_size >= 2`), по умолчанию 2.
- при нечетном числе участников и `room_size=2` формируется одна комната из 3 участников.

## 3. Технологический стек (фиксированный для MVP)

### 3.1 Backend
- Python 3.12+
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-JWT-Extended (или эквивалент для работы с внешним JWT)
- Flask-SocketIO (или эквивалент websocket-слоя)
- Celery/RQ (опционально, но рекомендовано для асинхронной проверки)

### 3.2 Frontend
- Vue 3
- Vite
- Pinia
- Vue Router
- Socket.IO client (или websocket-клиент совместимый с backend)

### 3.3 Infra
- PostgreSQL 15+
- Docker + docker-compose
- Nginx (опционально как reverse proxy)

## 4. Интеграции

### 4.1 Авторизация
- Источник истины: **GeekClass JWT**.
- Локальная модель пользователя создается/обновляется при первом входе.

### 4.2 Проверка решений
- Источник проверки: **GeekPaste API**.
- У задачи есть `check_type`:
  - `tests` — проверка тестами,
  - `gpt` — оценка нейронкой.
- Приоритет оценки задается типом задачи, смешанный режим в MVP не поддерживается.

### 4.3 Совместимость с текущим API GeekPasteV2
- Endpoint проверки: `POST /api/external/check`.
- Авторизация: `Authorization: Bearer <service_jwt>`, подпись `HS256`, секрет `JWT_SECRET` (общий с GeekPasteV2).
- Обязательные поля запроса:
  - `callback_url`,
  - `callback_id`,
  - `code`,
  - `lang`.
- Опциональные поля:
  - `task_text`,
  - `check_type` (`tests|gpt`),
  - `check_config` (JSON).
- Ответ при успешной постановке в очередь: `{"status":"queued","job_id":"..."}`.

### 4.4 Совместимость с авторизацией GeekClass (по аналогии с GeekExam/GeekPasteV2)
- Логин-флоу:
  1. редирект на `{GEEKCLASS_HOST}/insider/jwt?redirect_url={url}`,
  2. возврат JWT в query-параметре `token`,
  3. decode JWT по `JWT_SECRET`, `alg=HS256`,
  4. проверка `iat` (TTL токена 60 секунд),
  5. upsert пользователя в локальной БД,
  6. запись авторизации в server-side session.
- JWT payload (ожидаемый):
```json
{
  "id": 123,
  "role": "student",
  "name": "Иван Иванов",
  "iat": 1713272000
}
```

## 5. Роли и права

### 5.1 student
- Вход в систему,
- Нажатие кнопки `Готов`,
- Участие в матчах,
- Отправка решений,
- Просмотр текущего и итогового результата.

### 5.2 teacher
- Все права `student`,
- CRUD задач,
- Импорт/экспорт задач,
- Создание битвы, открытие лобби, запуск, остановка и завершение битвы,
- Просмотр лога битвы,
- Переоценка результата раунда с обязательным комментарием.

### 5.3 admin
- Все права `teacher`,
- Управление пользователями и ролями,
- Системные настройки.

## 6. Основные сущности домена

1. User
2. Battle
3. Task
4. Room (комната текущего раунда)
5. Match (факт одного раунда в комнате)
6. Submission
7. ScoreEvent
8. RatingHistory
9. AuditLog
10. QueueEntry
11. MatchParticipant

## 7. Правила батла

### 7.0 Жизненный цикл битвы
- Учитель создает битву и переводит ее в состояние набора участников (`lobby_open`).
- Участники подключаются к битве и нажимают `Готов`.
- Учитель запускает битву (`running`), после чего начинается матчмейкинг и раунды.
- Учитель может остановить битву в любой момент (`stopped`):
  - все активные раунды принудительно завершаются,
  - каждому участнику в комнате засчитывается текущий прогресс,
  - фиксируются итоги и лидерборд на момент остановки.
- После остановки новые раунды не создаются.

### 7.1 Формирование комнаты
- Игрок попадает в очередь только после нажатия `Готов`.
- Подбор идет по близкому рейтингу.
- Максимальное ожидание до принудительного расширения окна подбора: **2 минуты**.
- Размер комнаты настраиваемый `room_size` (минимум 2, по умолчанию 2).
- Если `room_size=2` и число ожидающих участников нечетное, система формирует одну комнату из 3 участников.
- Один и тот же соперник **не должен** выпадать игроку два раунда подряд (best effort при малом пуле).

### 7.2 Выбор задачи
- У задачи есть сложность: `easy`, `medium`, `hard`.
- С ростом рейтинга игрока вероятность более сложных задач увеличивается.
- В рамках одной битвы один и тот же пользователь не должен получать одну и ту же задачу дважды.

### 7.3 Победа в раунде
- Побеждает участник, который раньше всех получил первую `accepted` попытку.
- Если `accepted` нет до конца таймера:
  - сравнивается прогресс решения всех участников комнаты,
  - при равенстве максимального прогресса — ничья между лидерами.
- Для каждого участника в раунде фиксируется персональный итог: `win|draw|loss|no_result`.

### 7.4 Прогресс решения
- Для `tests`: доля пройденных тестов.
- Для `gpt`: нормализованный балл нейронки (0..1).

### 7.5 Ошибки компиляции/выполнения
- `compile error` и `runtime error` не дают штрафов сами по себе.

### 7.6 Дисконнекты
- Если отключился один или несколько участников: остальные продолжают решать; отключившиеся могут вернуться.
- Если отключились все участники комнаты: ждать 5 минут.
- Если никто не вернулся за 5 минут: завершить раунд как `no_result` (без изменения рейтинга).

### 7.7 Таймер раунда
- Длительность раунда: **20 минут**.

### 7.8 Правила консистентности раунда (обязательные)
- Первая `accepted` фиксируется атомарно в БД и не может быть перезаписана позднейшими сабмитами.
- Обработка сабмитов асинхронная, поэтому результат раунда должен финализироваться транзакционно, только один раз.
- При одновременном `accepted` (разница < 1 секунды) использовать `accepted_at` с миллисекундами; при полном равенстве — `draw`.
- При ручной остановке битвы teacher-ом финализация активных раундов выполняется транзакционно, один раз на комнату.

## 8. Рейтинг и очки

### 8.1 Рейтинг
- Используется Elo.
- `K = 24`.
- Для комнаты из 2+ участников используется pairwise-расчет:
  - для каждого участника считаются пары с каждым другим участником комнаты,
  - `E = 1 / (1 + 10^((R_opp - R_you)/400))`,
  - `S=1` (выше соперника), `S=0` (ниже), `S=0.5` (ничья),
  - итоговый `ΔR` участника = сумма pairwise-дельт, нормированная на `(participants_count - 1)`.

### 8.2 Очки лидерборда
- Победа: +100
- Поражение: +30
- Частичное решение: до +40 пропорционально прогрессу

### 8.3 Бонусы
- Серия побед:
  - 2 подряд: +10
  - 3 подряд: +20
  - 4 и более: +30
- Победа после 3+ поражений подряд: +20
- Лимит всех бонусов за раунд: +30

## 9. Сложность задач по рейтингу
Рекомендованный профиль выдачи (может храниться в конфиге):

- `rating < 1200`: easy 80%, medium 20%, hard 0%
- `1200 <= rating < 1600`: easy 30%, medium 60%, hard 10%
- `rating >= 1600`: easy 10%, medium 50%, hard 40%

## 10. Состояния

### 10.1 Battle.status
- `draft`
- `lobby_open`
- `running`
- `stopped`
- `finished`
- Статусы `scheduled` и `paused` считаются устаревшими и не используются.

### 10.2 Room.status
- `waiting_ready`
- `active`
- `paused_disconnect`
- `finished`
- `cancelled`

### 10.3 MatchParticipant.result_type
- `win`        -- для персонального результата участника
- `draw`
- `loss`
- `no_result`

### 10.4 Submission.verdict
- `queued`
- `running`
- `accepted`
- `wrong_answer`
- `compile_error`
- `runtime_error`
- `time_limit`
- `memory_limit`
- `internal_error`

## 11. Структура БД (минимальный контракт)

```sql
-- users
id UUID PK
external_id TEXT UNIQUE NOT NULL
name TEXT NOT NULL
role TEXT NOT NULL CHECK (role IN ('student','teacher','admin'))
rating INT NOT NULL DEFAULT 1000
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL

-- battles
id UUID PK
title TEXT NOT NULL
status TEXT NOT NULL
room_size INT NOT NULL DEFAULT 2
started_at TIMESTAMP NULL
finished_at TIMESTAMP NULL
created_by UUID NOT NULL REFERENCES users(id)
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL

-- tasks
id UUID PK
title TEXT NOT NULL
statement_md TEXT NOT NULL
difficulty TEXT NOT NULL CHECK (difficulty IN ('easy','medium','hard'))
check_type TEXT NOT NULL CHECK (check_type IN ('tests','gpt'))
config_json JSONB NOT NULL DEFAULT '{}'
is_active BOOLEAN NOT NULL DEFAULT TRUE
created_by UUID NOT NULL REFERENCES users(id)
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL

-- battle_tasks
battle_id UUID NOT NULL REFERENCES battles(id)
task_id UUID NOT NULL REFERENCES tasks(id)
PRIMARY KEY (battle_id, task_id)

-- queue_entries
id UUID PK
battle_id UUID NOT NULL REFERENCES battles(id)
user_id UUID NOT NULL REFERENCES users(id)
is_ready BOOLEAN NOT NULL DEFAULT FALSE
enqueued_at TIMESTAMP NOT NULL
last_opponents_json JSONB NOT NULL DEFAULT '[]'
UNIQUE (battle_id, user_id)

-- rooms
id UUID PK
battle_id UUID NOT NULL REFERENCES battles(id)
status TEXT NOT NULL
started_at TIMESTAMP NULL
finished_at TIMESTAMP NULL
created_at TIMESTAMP NOT NULL

-- matches
id UUID PK
room_id UUID NOT NULL REFERENCES rooms(id)
task_id UUID NOT NULL REFERENCES tasks(id)
finished_by TEXT NULL  -- timeout | accepted | teacher_stop | all_disconnected
created_at TIMESTAMP NOT NULL
finished_at TIMESTAMP NULL

-- match_participants
id UUID PK
match_id UUID NOT NULL REFERENCES matches(id)
student_id UUID NOT NULL REFERENCES users(id)
result_type TEXT NULL CHECK (result_type IN ('win','draw','loss','no_result'))
accepted_at TIMESTAMP NULL
progress NUMERIC(5,4) NULL
place INT NULL
is_disconnected BOOLEAN NOT NULL DEFAULT FALSE
UNIQUE (match_id, student_id)

-- submissions
id UUID PK
match_id UUID NOT NULL REFERENCES matches(id)
student_id UUID NOT NULL REFERENCES users(id)
language TEXT NOT NULL CHECK (language IN ('python','cpp'))
source_code TEXT NOT NULL
verdict TEXT NOT NULL
progress_value NUMERIC(5,4) NOT NULL DEFAULT 0
visible_tests_passed INT NULL
visible_tests_total INT NULL
hidden_tests_passed INT NULL
hidden_tests_total INT NULL
external_run_id TEXT NULL
created_at TIMESTAMP NOT NULL

-- score_events
id UUID PK
match_id UUID NOT NULL REFERENCES matches(id)
student_id UUID NOT NULL REFERENCES users(id)
points_delta INT NOT NULL
rating_delta INT NOT NULL
reason TEXT NOT NULL
created_at TIMESTAMP NOT NULL

-- rating_history
id UUID PK
user_id UUID NOT NULL REFERENCES users(id)
match_id UUID NOT NULL REFERENCES matches(id)
old_rating INT NOT NULL
new_rating INT NOT NULL
created_at TIMESTAMP NOT NULL

-- audit_log
id UUID PK
actor_id UUID NOT NULL REFERENCES users(id)
entity_type TEXT NOT NULL
entity_id UUID NOT NULL
action TEXT NOT NULL
payload_json JSONB NOT NULL DEFAULT '{}'
created_at TIMESTAMP NOT NULL
```

## 12. API-контракты (REST)

Базовый префикс: `/api/v1`

### 12.1 Auth
- `POST /auth/login/geekclass`
  - Вход: Bearer GeekClass JWT
  - Выход: профиль локального пользователя + роль

### 12.2 Профиль
- `GET /me`

### 12.3 Battles
- `GET /battles`
- `POST /battles`
- `GET /battles/{battleId}`
- `PATCH /battles/{battleId}`
- `POST /battles/{battleId}/open-lobby`
- `POST /battles/{battleId}/start`
- `POST /battles/{battleId}/stop`
- `POST /battles/{battleId}/finish`
- `GET /battles/{battleId}/leaderboard`
- `GET /battles/{battleId}/logs`

### 12.4 Tasks
- `GET /tasks`
- `POST /tasks`
- `GET /tasks/{taskId}`
- `PATCH /tasks/{taskId}`
- `DELETE /tasks/{taskId}`
- `POST /tasks/import`
- `GET /tasks/export`

### 12.5 Queue / Matchmaking
- `POST /battles/{battleId}/queue/join`
- `POST /battles/{battleId}/queue/leave`
- `POST /battles/{battleId}/queue/ready`

### 12.6 Rooms / Matches
- `GET /rooms/{roomId}`
- `POST /rooms/{roomId}/submit`
- `GET /matches/{matchId}`
- `GET /matches/{matchId}/participants`
- `POST /matches/{matchId}/rejudge` (teacher/admin)

### 12.7 Пример submit-запроса
```json
{
  "language": "python",
  "source_code": "print('hello')"
}
```

### 12.8 Единый формат ошибок
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "language must be one of: python, cpp",
    "details": {}
  }
}
```

### 12.9 Контракт интеграции с GeekPasteV2 (обязательный)
Запрос в GeekPasteV2:
```json
{
  "callback_url": "https://<battle-host>/api/v1/integrations/geekpaste/callback",
  "callback_id": "submission_uuid",
  "code": "print('hello')",
  "lang": "python",
  "task_text": "Условие задачи в plain text",
  "check_type": "tests",
  "check_config": {
    "tests": [
      {"input": "1 2", "expected": "3"}
    ]
  }
}
```

Ожидаемый callback от GeekPasteV2:
```json
{
  "callback_id": "submission_uuid",
  "job_id": "celery_job_uuid",
  "status": "success",
  "points": 8,
  "max_points": 10,
  "comment": "8 из 10 тестов пройдено",
  "details": []
}
```

Правила callback-обработчика:
- Endpoint: `POST /api/v1/integrations/geekpaste/callback`.
- Обязательный заголовок: `Authorization: Bearer <jwt>` (HS256, общий `JWT_SECRET`).
- JWT callback должен содержать claim `service=geekpaste`.
- JWT callback проверяется по `iat` (TTL по умолчанию 120 секунд).
- Обработчик идемпотентен по `callback_id` (повторные доставки не должны дублировать начисления).
- Если `callback_id` неизвестен: вернуть `404`.
- Если callback уже обработан: вернуть `200` и no-op.
- После успешной обработки обновить `submission`, `match_participant`, при необходимости финализировать раунд и отправить websocket-события.

## 13. WebSocket события

Каналы:
- battle-room channel: `battle:{battleId}`
- room channel: `room:{roomId}`
- user channel: `user:{userId}`

События:
1. `queue_updated`
2. `match_found`
3. `room_started`
4. `submission_progress`
5. `submission_verdict`
6. `opponent_disconnected`
7. `opponent_reconnected`
8. `round_finished`
9. `leaderboard_updated`
10. `battle_status_changed`

## 14. UI-экраны MVP

1. Login
2. Battle Lobby
   - список участников,
   - статус очереди,
   - кнопка `Готов`.
3. Room
   - условие задачи (markdown-render),
   - редактор кода,
   - выбор языка (`python`, `cpp`),
   - таймер,
   - прогресс тестов,
  - статусы остальных участников комнаты.
4. Battle Leaderboard
5. Teacher/Admin Panel
   - CRUD задач,
   - импорт/экспорт,
   - управление статусом битвы,
   - лог событий,
   - переоценка.

## 15. Импорт/экспорт задач

### 15.1 Формат JSON массива задач
```json
[
  {
    "title": "Two Sum",
    "statement_md": "# Найдите пару...",
    "difficulty": "easy",
    "check_type": "tests",
    "languages": ["python", "cpp"],
    "config": {
      "time_limit_ms": 2000,
      "memory_limit_mb": 256,
      "tests": []
    }
  }
]
```

### 15.2 Правила валидации
- обязательные поля: `title`, `statement_md`, `difficulty`, `check_type`
- неизвестные поля игнорировать
- невалидные записи отклонять с указанием индекса элемента и причины

## 16. Переоценка (rejudge)

### 16.1 Право
- Только `teacher` и `admin`.

### 16.2 Вход
- `POST /matches/{matchId}/rejudge`
```json
{
  "new_results": [
    {"student_id": "uuid-1", "result_type": "win"},
    {"student_id": "uuid-2", "result_type": "loss"}
  ],
  "reason": "Neural check produced incorrect score"
}
```

### 16.3 Правила
- `reason` обязателен.
- `new_results` должен покрывать всех участников комнаты, иначе `400`.
- Создается запись в `audit_log`.
- Старые `score_events` помечаются неактуальными или компенсируются обратными событиями.
- Рейтинг и лидерборд пересчитываются детерминированно.

## 17. Нефункциональные требования

1. Все сервисы должны подниматься командой `docker compose up`.
2. Бэкенд должен выполнять миграции при старте (или отдельной командой в compose).
3. API покрывается OpenAPI-схемой (генерируемая swagger-страница).
4. Логирование: структурные JSON-логи в stdout.
5. UTC в БД, локальное время только на клиенте.
6. Матчмейкинг и финализация раунда выполняются под транзакционной блокировкой (`SELECT ... FOR UPDATE`) для исключения гонок.
7. Все внешние запросы в GeekPasteV2 должны иметь timeout и retry-политику с экспоненциальной задержкой.
8. В callback-пайплайне обязательна идемпотентность и безопасная повторная доставка.
9. Ограничение размера `source_code` в API: 256 KB на один submit (ошибка `413` при превышении).
10. Все временные вычисления (таймер раунда, 2 минуты очереди, 5 минут disconnect) выполняются на backend, frontend только отображает.

## 18. Ограничения MVP / вне области

1. Античит механики не реализуются.
2. Поддержка языков кроме `python` и `cpp` не реализуется.
3. Расширенная операционка (HA, сложный мониторинг) не обязательна.
4. Командные матчи не реализуются (формат FFA в рамках одной комнаты).

## 19. Критерии приемки (Definition of Done)

1. Пользователь может войти через GeekClass JWT.
2. Teacher может создать битву, добавить задачи и запустить битву.
3. Teacher может открыть лобби, участники могут подключиться и нажать `Готов`, затем teacher запускает битву.
4. Student может войти в очередь, нажать `Готов`, получить комнату раунда.
5. При нечетном числе ожидающих и `room_size=2` создается одна комната из 3 участников.
6. Повторного соперника подряд нет (best effort при малом пуле).
7. Один и тот же task не повторяется у одного студента в рамках битвы.
8. Submit на Python/C++ проходит через внешний чекер.
9. Победитель определяется по первой `accepted` в комнате.
10. Дисконнект-правила реализованы, включая сценарий 5 минут при отключении всех участников комнаты.
11. При остановке битвы teacher-ом все активные раунды завершаются и засчитывают текущий результат.
12. Лидерборд обновляется после завершения раунда.
13. Teacher может сделать rejudge, и изменения отражаются в логе и рейтинге.

## 20. Порядок реализации для кодогенерации

### Этап 1: Каркас
- docker-compose
- Flask app factory
- Подключение PostgreSQL
- Alembic migrations
- Модель users + auth middleware

### Этап 2: Доменные сущности
- battles, tasks, queue_entries, rooms, matches, match_participants, submissions
- CRUD для задач и битв

### Этап 3: Матчмейкинг + раунды
- queue join/ready/leave
- подбор комнат (2..N участников)
- создание room/match/match_participants
- таймер и финализация

### Этап 4: Проверка решений
- интеграция с GeekPaste API
- сохранение verdict/progress
- правила определения победителя
- обработка callback + идемпотентность + дедупликация

### Этап 5: Очки и рейтинг
- score_events
- elo update
- leaderboard

### Этап 6: Realtime и UI
- websocket-события
- lobby/room/leaderboard
- teacher панель

### Этап 7: Rejudge + аудит
- ручная переоценка
- перерасчет рейтинга
- аудит-лог

## 21. Критичные уточнения, добавленные после сверки с соседними системами
1. `check_type` в системе и GeekPasteV2 единый: `tests|gpt`.
2. Callback GeekPasteV2 подписан сервисным JWT (`service=geekpaste`, HS256, общий `JWT_SECRET`) и проверяется по `iat`.
3. `check_config.tests` может содержать как видимые, так и скрытые тесты; в UI студента показывать только агрегированный прогресс и только те детали, которые явно помечены как видимые.
4. Для исключения двойного начисления очков все `score_events` привязывать к `match_id` + `student_id` + `reason` и обеспечивать защиту от дублей.
5. В API и БД сохранять поля внешней интеграции: `external_job_id`, `callback_received_at`, `checker_status_raw`, `checker_comment_raw`.
6. Rejudge должен создавать новый `score_event`(компенсация), а не «молчаливо» переписывать историю.
7. Битва имеет двухшаговый запуск: `open-lobby` (набор участников) -> `start` (старт раундов).
8. `stop` от teacher завершает все активные комнаты с фиксацией текущего прогресса.
9. Модель комнаты поддерживает произвольное число участников (минимум 2), при нечетном пуле и `room_size=2` используется комната из 3.

---
Если требуется, следующий документ: `IMPLEMENTATION_PROMPTS.md` — набор готовых prompt-блоков для пошаговой кодогенерации backend/frontend по этому ТЗ.
