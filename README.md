# DataSearcher

![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-In--process-orange)
![License](https://img.shields.io/badge/License-MIT-green)
![Language](https://img.shields.io/badge/Язык-Русский-red)

> Загрузи таблицу или подключись к БД. Задай вопрос. Получи ответ с графиками.
> 46 аналитических инструментов, ML-прогнозы, дашборды, enterprise-безопасность — всё через чат.

---

## Зачем

Я анализирую данные каждый день. Excel — медленно. Python — порог входа.
BI-системы — оверкилл для быстрого вопроса «сколько клиентов ушли в прошлом
квартале и почему».

Хотелось инструмента, который понимает вопросы на русском, сам пишет SQL,
строит графики, находит аномалии и прогнозирует тренды. Без настройки.
Без дашбордов из 20 виджетов. Просто — загрузил файл или подключился к БД и спросил.

DataSearcher — это попытка сделать аналитику данных разговорной.
Не «напиши SQL», а «какие факторы сильнее всего влияют на отток».
Не «построй график», а «покажи тренд продаж с прогнозом на 3 месяца».

---

## Как это работает

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  React   │────▶│ FastAPI  │────▶│  DuckDB  │
│  Chat UI │◀────│  + LLM   │◀────│ In-mem   │
└──────────┘ SSE └──────────┘     └──────────┘
                  │                      ▲
                  ▸ 46 analysis tools    │
                  ▸ SSE streaming        │
                  ▸ JWT auth             │
                  ▸ Admin panel          │
                  ▸ DB connections       │
                  ▸ read-only guard      │
                  ▸ PII masking          │
                  ▸ Knowledge Base       │
                  │                      │
                  │   ┌──────────────────┘
                  │   │ Source DB (push-down)
                  └──▶ PostgreSQL, MySQL, ClickHouse, SQLite, REST API
```

1. Пользователь загружает .xlsx/.csv/.parquet или подключается к существующей БД
2. Задаёт вопрос на русском
3. LLM выбирает нужные инструменты, выполняет SQL (в DuckDB или push-down в source DB), строит графики
4. Результат стримится в чат с интерактивными таблицами и чартами
5. PII-колонки автоматически маскируются, все запросы логируются для аудита

---

## 46 инструментов анализа

### SQL и подключения

| # | Инструмент | Описание |
|---|-----------|----------|
| 1 | `sql_query` | SQL (DuckDB или push-down в source DB, read-only guard, PII-маскирование, форматы markdown/json/csv) |
| 2 | `query_explain` | План выполнения SQL (EXPLAIN) |
| 3 | `get_schema` | Структура таблицы + метаданные из Knowledge Base + PII-метки |
| 4 | `attach_database` | Подключить новую БД в рантайме (auto/remote/dump/federated) |
| 5 | `refresh_schema` | Обновить схему подключений |
| 6 | `test_connection` | Проверить доступность подключения |
| 7 | `load_file` | Загрузить CSV/Excel/Parquet |

### Аналитика данных

| # | Инструмент | Описание |
|---|-----------|----------|
| 8 | `profile_data` | Детальная статистика по колонкам |
| 9 | `smart_summary` | Умное описание структуры данных |
| 10 | `data_quality_report` | Аудит качества (пропуски, дубликаты) |
| 11 | `find_duplicates` | Поиск дубликатов (точных и fuzzy) |
| 12 | `detect_anomalies` | Выбросы (z-score, IQR) |
| 13 | `sample_data` | Быстрый просмотр данных |
| 14 | `correlation_analysis` | Корреляции (Пирсон/Спирмен) |
| 15 | `distribution_analysis` | Форма распределения |
| 16 | `cross_tab` | Кросс-табуляция + Хи-квадрат |
| 17 | `pivot_table` | Сводная таблица в стиле Excel |
| 18 | `segment_data` | Сегментация (квинтили, RFM) |
| 19 | `compare_tables` | Сравнение двух таблиц |
| 20 | `time_analysis` | Тренды, сезонность, динамика |
| 21 | `auto_insights` | Авто-поиск топ-5 инсайтов |
| 22 | `detect_patterns` | Паттерны в тексте (email, ИНН, телефон) |

### ML и прогнозы

| # | Инструмент | Описание |
|---|-----------|----------|
| 23 | `generate_sql` | Генерация SQL из описания на русском |
| 24 | `visualize_data` | Графики (bar, line, pie, scatter, area, histogram) |
| 25 | `predict_trend` | Прогноз тренда на будущее |
| 26 | `cluster_analysis` | Кластеризация (K-Means, DBSCAN) |
| 27 | `feature_importance` | Важность факторов для целевой переменной |
| 28 | `statistical_test` | t-тест, Mann-Whitney, KS, Хи-квадрат |
| 29 | `classify_rows` | Классификация строк через LLM |
| 30 | `semantic_search` | Семантический поиск через LLM embeddings |

### Управление данными и BI

| # | Инструмент | Описание |
|---|-----------|----------|
| 31 | `transform_data` | Преобразования (нормализация, one-hot, даты) |
| 32 | `merge_tables` | JOIN (с авто-определением ключей по FK) |
| 33 | `export_data` | Экспорт в CSV |
| 34 | `export_xlsx` | Экспорт в XLSX с форматированием |
| 35 | `build_dashboard` | Дашборд из 4-6 графиков в чате |
| 36 | `data_story` | Нарратив с графиками |
| 37 | `create_public_dashboard` | Standalone HTML-дашборд по ссылке |
| 38 | `build_bi_link` | URL для Superset/Grafana/Datalens/Tableau/Power BI |

### Метаданные и аудит (enterprise)

| # | Инструмент | Описание |
|---|-----------|----------|
| 39 | `scan_pii` | Скан PII в таблице |
| 40 | `update_metadata` | Обновить метаописание в Knowledge Base |
| 41 | `list_metrics` | Список расчётных метрик с формулами |
| 42 | `search_knowledge` | Поиск по метаданным и примерам |
| 43 | `add_example` | Добавить эталон «NL→SQL» в Example Store |
| 44 | `load_dbt` | Импорт метаданных из dbt manifest |
| 45 | `sync_datahub` | Синхронизация с DataHub |
| 46 | `get_logs` | Логи запросов/ошибок/аудита |

---

## Функции UI

- **Интерактивные таблицы** — сортировка, поиск, пагинация, экспорт CSV, подсветка NULL
- **Тёмная тема** — переключение Ctrl+D, сохранение в localStorage
- **Экспорт графиков PNG** — кнопка на каждом чарте, 2x pixel ratio
- **PDF-отчёты** — титульная страница, графики как PNG, чистый текст, Ctrl+Shift+P
- **Шаблоны анализов** — 6 карточек для быстрого старта (Обзор, Дашборд, Аудит, Тренды, Корреляции, Стори)
- **Авто-профиль + дашборд** — при загрузке первого файла автоматически запускается анализ
- **Уведомления** — звук + Web Notification при завершении стрима
- **Горячие клавиши** — Ctrl+D тема, Ctrl+K фокус, Ctrl+Shift+P PDF
- **История запросов** — вкладка в sidebar, клик = повтор
- **Умные подсказки** — на основе типов колонок (date→тренд, num→корреляция, cat→кросс-таб)
- **Сравнение анализов** — split-view оверлей
- **ER-схема** — визуальная схема таблиц и колонок
- **Подключения к БД** — PostgreSQL, MySQL, ClickHouse, SQLite с выбором режима (auto/remote/dump/federated)
- **Зона подключения к БД** — на главном экране рядом с загрузкой файла
- **База знаний (sidebar)** — метаданные таблиц/колонок, метрики, поиск, загрузка dbt manifest, синхронизация DataHub
- **Логи (sidebar)** — запросы, ошибки, аудит-логи
- **BI Link Builder** — модалка для генерации URL в Superset/Grafana/Datalens/Tableau/Power BI
- **Админ-панель: Безопасность** — enterprise-настройки (read-only, PII, rate limit, режимы)

---

## Enterprise-фичи

### Read-only guard
Все SQL-запросы к подключённым БД проверяются: INSERT/UPDATE/DELETE/DROP/TRUNCATE/ALTER — заблокированы. Разрешены только SELECT/WITH/EXPLAIN/SHOW/DESCRIBE. `READ_ONLY=false` отключает guard.

### PII auto-detection + masking
При подключении БД и загрузке файлов сервер сканирует текстовые колонки и определяет: email, телефон (РФ), ИНН, СНИЛС, паспорт, банковскую карту, IP. В результатах SQL PII маскируется: `a***@company.com`, `+7(912)***-**-89`. Управляется через `PII_MASKING`.

### Knowledge Base (SQLite)
Бизнес-метаданные в SQLite: описания таблиц, колонок, владельцы, теги, расчётные метрики. Наполняется из 4 источников (fallback-цепочка): схема БД (авто), dbt manifest (`load_dbt`), DataHub (`sync_datahub`), ручная правка (`update_metadata`).

### Логирование и аудит
Каждый SQL-запрос, ML-вызов, ошибка логируются в SQLite (append-only): `query_log`, `error_log`, `audit_log`. Просмотр через вкладку «Логи» или инструмент `get_logs`. Управляется через `LOG_ENABLED`.

### Rate limiting
Per-tool throttling: SQL — 60/мин, ML — 10/мин (настраивается). `RATE_LIMIT_ENABLED=false` отключает.

### Schema ACL
Фильтрация таблиц по бизнес-слою: `BLOCKED_TABLE_PATTERNS=raw_*,stg_*,tmp_*` — glob-паттерны исключений.

### Режимы подключений

| Режим | Как работает | Когда использовать |
|-------|-------------|-------------------|
| `auto` (по умолч.) | SQL → source DB, ML → DuckDB (лениво) | Универсальный |
| `remote` | Всё SQL в source DB, без DuckDB | БД быстрая, ML не нужен |
| `dump` | Таблицы выгружаются в DuckDB | Файлы, маленькие БД |
| `federated` | Source DB прицепляется к DuckDB | Кросс-БД JOIN |

### sqlglot трансляция SQL
Пишите на DuckDB SQL — сервер автоматически транслирует в диалект source DB (PostgreSQL/MySQL/ClickHouse/SQLite). `AUTO_TRANSLATE=false` отключает.

### Semantic search + Example Store
`semantic_search` — поиск по текстовым данным через LLM embeddings. Example Store — база пар «NL-запрос → SQL» для few-shot обучения `generate_sql`.

---

## Авторизация и роли

| Роль | Возможности |
|------|------------|
| **admin** | Управление пользователями, настройками, подключениями к БД, LLM-параметрами (глобальными и индивидуальными) |
| **analyst** | Загрузка файлов, анализ, свои LLM-настройки (если разрешено), свои подключения к БД |
| **viewer** | Просмотр данных и результатов анализа |

### Admin-панель

Три вкладки:

**Пользователи** — список с бейджами (роль, LLM, ограничения). Клик по пользователю открывает детальную карточку с тремя секциями:
- **Права** — индивидуальные переключатели `can_use_custom_llm` / `can_use_db_connections`
- **LLM** — индивидуальные настройки URL/Model/API Key (оставьте пустыми для глобальных)
- **БД** — список подключений пользователя + кнопка «Добавить подключение»

**Настройки** — глобальные переключатели:
- Регистрация пользователей (вкл/выкл)
- Пользовательские LLM-настройки (вкл/выкл)
- Пользовательские подключения к БД (вкл/выкл)
- Глобальные LLM-параметры (URL, Model, API Key)

**Базы данных** — CRUD подключений, тест, подключение к текущей сессии

---

## Быстрый старт

### Предварительные требования

- Python 3.12+
- Node.js 20+
- LLM API (Ollama, vLLM, OpenAI-compatible)

### Установка

```bash
# Backend
cd backend
cp .env.example .env
# Отредактируйте .env — укажите LLM URL и сгенерируйте JWT_SECRET
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

### Первый вход

По умолчанию создаётся администратор:
- **Email:** `admin@datasearcher.com`
- **Пароль:** `admin`

Смените пароль после первого входа через админ-панель.

### Docker (демо-среда с тестовыми БД)

```bash
# Запуск: backend + frontend + PostgreSQL + MySQL + ClickHouse с демо-данными
docker compose up -d --build

# Проверка статуса
docker compose ps

# Логи
docker compose logs -f backend

# Остановка
docker compose down

# Полный сброс (удалить volumes с данными)
docker compose down -v
```

После запуска:
- **Frontend (UI):** http://localhost:3000
- **Backend API:** http://localhost:8000/api/health

#### Демо-базы данных (преднастроены)

docker-compose поднимает 3 БД с авто-инициализацией демо-данных:

| БД | Контейнер | Порт | Database | User | Password | Демо-данные |
|----|-----------|------|----------|------|----------|------------|
| PostgreSQL | `postgres` | 5432 | `ecommerce` | `datasearcher` | `ds_demo_pass_2024` | 12 клиентов, 15 товаров, 25 заказов, 50 позиций |
| MySQL | `mysql` | 3306 | `crm` | `datasearcher` | `ds_demo_pass_2024` | 8 менеджеров, 30 сделок, 40 взаимодействий |
| ClickHouse | `clickhouse` | 8123 | `default` | `datasearcher` | `ds_demo_pass_2024` | 60 просмотров, 30 кликов |

#### Как подключить демо-БД через UI

1. Зайди на http://localhost:3000, войди как `admin@datasearcher.com` / `admin`
2. Открой вкладку **БД** в сайдбаре (или зону подключения на главном экране)
3. Создай подключение:
   - **PostgreSQL:** host=`localhost`, port=`5432`, db=`ecommerce`, user=`datasearcher`, pass=`ds_demo_pass_2024`
   - **MySQL:** host=`localhost`, port=`3306`, db=`crm`, user=`datasearcher`, pass=`ds_demo_pass_2024`
   - **ClickHouse:** host=`localhost`, port=`8123`, db=`default`, user=`datasearcher`, pass=`ds_demo_pass_2024`
4. Выбери режим подключения: `auto` (рекомендуется — SQL в source DB, ML в DuckDB)
5. Нажми «Подключить» — таблицы загрузятся

#### Демо-CSV файл

`demo-data/marketing_metrics.csv` — 30 строк маркетинговой аналитики (каналы, визиты, клики, конверсии, ROI). Загрузи через UI (drag & drop на главном экране).

#### LLM для чата

Для работы чата нужен LLM API (OpenAI-compatible). `.env` преднастроен на agentplatform.ru:
```
LLM_BASE_URL=https://api.agentplatform.ru/v1
LLM_API_KEY=sk-...
LLM_MODEL=deepseek/deepseek-v4-flash
```

Или укажи свой API (Ollama, vLLM, OpenAI) в `.env`. Для Ollama:
```bash
ollama pull qwen2.5:14b
ollama serve
# .env: LLM_BASE_URL=http://host.docker.internal:11434/v1
```

---

## Переменные окружения

### Базовые

| Переменная | По умолчанию | Описание |
|-----------|-------------|----------|
| `LLM_BASE_URL` | `http://localhost:11434/v1` | URL LLM API (OpenAI-compatible) |
| `LLM_API_KEY` | `` | API-ключ для LLM |
| `LLM_MODEL` | `qwen2.5:14b` | Модель LLM |
| `JWT_SECRET` | *auto-generated* | Секрет для JWT (ОБЯЗАТЕЛЬНО задать в prod!) |
| `ENCRYPTION_KEY` | `` | Fernet-ключ для шифрования connection strings |
| `ADMIN_EMAIL` | `admin@datasearcher.com` | Email администратора по умолчанию |
| `ADMIN_PASSWORD` | `admin` | Пароль администратора |
| `UPLOAD_DIR` | `./uploads` | Директория для загрузок |
| `DUCKDB_MEMORY_LIMIT` | `2GB` | Лимит памяти DuckDB |

### Enterprise

| Переменная | По умолчанию | Описание |
|-----------|-------------|----------|
| `DEFAULT_MODE` | `auto` | Режим подключений: auto/remote/dump/federated |
| `QUERY_TIMEOUT` | `60` | Таймаут remote SQL (сек), 0 = без лимита |
| `AUTO_TRANSLATE` | `true` | Трансляция DuckDB SQL → диалект source DB (sqlglot) |
| `DUCKDB_EXTENSIONS` | `postgres_scanner,...` | Расширения DuckDB для federated-режима |
| `READ_ONLY` | `true` | Read-only guard (блок DML/DDL) |
| `BLOCKED_TABLE_PATTERNS` | `raw_*,stg_*,...` | Заблокированные паттерны таблиц (glob) |
| `PII_MASKING` | `true` | Авто-маскирование PII |
| `PII_SCAN_ROWS` | `10` | Строк для скана PII |
| `RATE_LIMIT_ENABLED` | `true` | Rate limiting |
| `RATE_LIMIT_SQL` | `60` | SQL-запросов в минуту |
| `RATE_LIMIT_ML` | `10` | ML-запросов в минуту |
| `LOG_ENABLED` | `true` | Логирование запросов/ошибок/аудита |
| `LOG_DB_PATH` | `` | SQLite-файл логов (пусто = `./datasearcher_logs.db`) |
| `KB_DB_PATH` | `` | SQLite-файл Knowledge Base (пусто = `./datasearcher_kb.db`) |
| `DBT_MANIFEST_PATH` | `` | Путь к dbt manifest.json |
| `DATAHUB_URL` | `` | URL DataHub для синхронизации метаданных |
| `DATAHUB_TOKEN` | `` | Токен DataHub |
| `EXAMPLE_STORE_ENABLED` | `true` | Example Store (few-shot NL→SQL) |
| `SEMANTIC_SEARCH_MAX_ROWS` | `10000` | Лимит строк для semantic_search |
| `EMBEDDINGS_DIR` | `` | Директория кеша embeddings |

> **Безопасность**: В продакшене ОБЯЗАТЕЛЬНО задайте `JWT_SECRET` и `ENCRYPTION_KEY`.
> Сгенерируйте: `python -c "import secrets; print(secrets.token_hex(32))"` для JWT_SECRET
> и `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` для ENCRYPTION_KEY.

---

## Архитектура

```
backend/
  app/
    main.py              # FastAPI, lifespan, routers
    config.py            # pydantic-settings (базовые + enterprise)
    session.py           # SessionManager, DuckDB connections
    models/
      __init__.py        # Pydantic models
      database.py        # SQLAlchemy models (User, AppSettings, UserSettings, DBConnection)
    routers/
      auth.py            # JWT auth (login/register/refresh/logout)
      admin.py           # Admin panel API (users, LLM, enterprise-settings)
      chat.py            # SSE chat + PDF export
      files.py           # File upload/list/delete/preview
      connections.py     # DB connections CRUD + attach (режимы auto/remote/dump/federated)
      settings.py        # LLM settings
      knowledge.py       # Knowledge Base API (таблицы, колонки, метрики, поиск, примеры)
      logs.py            # Логи запросов/ошибок/аудита
      metadata.py        # dbt manifest, DataHub sync, PII scan, BI link builder
      dashboards.py      # Публичные дашборды
    services/
      auth_service.py    # JWT, bcrypt, encryption, per-user LLM
      llm_service.py     # LLM streaming, tool loop, rate limit, logging, remote-table resolve
      pdf_export.py      # PDF generation with charts
      file_service.py    # File handling
      engine.py          # AnalysisEngine (connectors, режимы, KB, PII, sqlglot)
      sql_guard.py       # read-only enforcement
      pii_detector.py    # авто-детекция + маскирование PII
      logging_db.py      # SQLite append-only логи
      error_handler.py   # человекочитаемые SQL-ошибки
      rate_limiter.py     # per-tool throttling
      knowledge_base.py   # SQLite KB (описания, владельцы, метрики)
      dbt_loader.py       # парсинг dbt manifest.json
      datahub_client.py  # DataHub GraphQL клиент
      embeddings.py       # semantic search через embeddings
      example_store.py   # NL→SQL пары + few-shot
      bi_linker.py       # URL builder для BI-инструментов
      connectors/        # PostgreSQL, MySQL, ClickHouse, SQLite, REST API
      services/tools/    # 46 аналитических инструментов

frontend/
  src/
    api/client.ts        # API client (auth, admin, connections, chat, KB, logs, metadata, BI)
    hooks/               # useAuth, useChat, useFiles, useTheme, useNotification, ...
    components/
      Chat/              # MessageBlocks, ChartBlock, InteractiveTable, AnalysisTemplates, ComparisonView
      Layout/            # Sidebar, SchemaDiagram, SettingsModal, FilePreviewModal, KnowledgeTab, LogsTab, BILinkModal
      Admin/             # AdminPanel (Users / Settings / Connections / Безопасность)
      Files/             # FileUpload
      Pages/             # LoginPage, RegisterPage, DashboardPage
```

---

## Технологии

| Слой | Технология |
|------|-----------|
| Frontend | React 19, TypeScript, Vite, Recharts, @tanstack/react-table |
| Backend | FastAPI, DuckDB, SQLAlchemy, JWT (PyJWT), bcrypt (passlib) |
| ML/Анализ | scikit-learn, scipy, numpy |
| DB Drivers | psycopg2 (PostgreSQL), pymysql (MySQL), clickhouse-connect, aiosqlite |
| SQL трансляция | sqlglot (DuckDB → source DB диалект) |
| KB / логи | SQLite (embedded, zero-dependency) |
| Embeddings | OpenAI-compatible /v1/embeddings |
| Файлы | CSV/Parquet (DuckDB), Excel (pandas/openpyxl) |
| PDF | fpdf2 с встроенными графиками PNG |
| Экспорт | html-to-image (PNG графиков), openpyxl (XLSX) |

---

## Тесты

Проект покрыт 374 тестами (332 backend + 42 frontend). Все проходят за ~35 секунд.

### Backend (pytest, 332 теста)

```bash
cd backend
python -m pytest tests/ -v
```

| Файл | Тестов | Что покрывает |
|------|--------|---------------|
| `test_sql_guard.py` | 20 | read-only guard: все разрешённые/заблокированные операторы, CTE-инъекции, disabled-режим |
| `test_pii_detector.py` | 24 | detect по имени/значениям, mask для 7 типов PII, scan_table с KB-записью |
| `test_error_handler.py` | 16 | все 10 паттернов ошибок, markdown-формат, truncate, suggestions |
| `test_rate_limiter.py` | 14 | SQL/ML категории, sliding window, per-user изоляция, disabled |
| `test_bi_linker.py` | 21 | все 5 BI-инструментов + edge cases, params, time_range |
| `test_dbt_loader.py` | 19 | manifest.json парсинг, KB-обогащение, semantic_models.yml, layer detection |
| `test_connectors.py` | 40 | registry, SQLite (CRUD, FK, attach_syntax), ApiConnector (endpoints, flatten) |
| `test_kb_logs_examples.py` | 26 | KB CRUD, search, LoggingDB, ExampleStore (golden, text-search) |
| `test_engine.py` | 21 | load_csv, translate_sql, ensure_table_in_duckdb, FK-эвристика, синглтон |
| `test_tools.py` | 29 | 46 инструментов, sql_query (guard+PII+formats), get_schema, export_xlsx, build_bi_link |
| `test_tools_extra.py` | 31 | export_data, transform_data, profile_data, smart_summary, attach_database, load_file |
| `test_api.py` | 31 | auth, knowledge CRUD, logs, metadata, connections/modes, admin enterprise-settings |

### Frontend (vitest, 42 теста)

```bash
cd frontend
npm test
```

| Файл | Тестов | Что покрывает |
|------|--------|---------------|
| `KnowledgeTab.test.tsx` | 9 | рендер, загрузка tables/metrics, search, dbt/datahub, certified badge |
| `LogsTab.test.tsx` | 8 | 3 таба (query/error/audit), переключение, empty-state |
| `BILinkModal.test.tsx` | 8 | 5 BI-инструментов, валидация URL/JSON, time-range, copy |
| `Sidebar.test.tsx` | 8 | 7 вкладок, BI Link Builder, переключение KB/Logs/БД |
| `AdminPanel.test.tsx` | 9 | 4 таба, enterprise-настройки, error handling |

### Баги, найденные тестами

1. **`sql_guard` CTE-уязвимость** — `WITH t AS (INSERT...) SELECT 1` проходил guard (ранний return для WITH)
2. **`pii_detector.mask_row` KeyError** — несоответствие ключей `column` vs `column_name` между KB и mask_row
3. **`_safe_table_name`** — кириллица заменялась на `_` (regex без `re.UNICODE`)
4. **`dbt_loader`** — невалидный JSON бросал 500 вместо 400
5. **`smart_summary`** — распаковка 3-элементных DuckDB DESCRIBE-кортежей в 2 переменные

---

## Лицензия

MIT
