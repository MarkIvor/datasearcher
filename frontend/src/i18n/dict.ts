/* DataSearcher i18n — словари. en типизирован по ключам ru: пропуски ловит tsc. */

const ru: Record<string, string> = {
  // ── common ──
  "common.loading": "Загрузка...",
  "common.loadingData": "Загрузка данных...",
  "common.cancel": "Отмена",
  "common.copy": "Копировать",
  "common.copied": "Скопировано",
  "common.download": "Скачать",
  "common.delete": "Удалить",
  "common.close": "Закрыть",
  "common.save": "Сохранить",
  "common.back": "Назад",
  "common.next": "Далее",
  "common.confirm": "Confirm",
  "common.test": "Проверить",
  "common.create": "Создать",
  "common.error": "Ошибка",
  "common.saved": "Сохранение...",
  "common.langTitle": "Переключить язык / Switch language",
  "common.langName": "Русский",

  // ── login / register ──
  "login.title": "Вход",
  "login.sub": "Введите email и пароль вашего аккаунта",
  "login.email": "Email",
  "login.password": "Пароль",
  "login.passwordHint": "Минимум 6 символов",
  "login.submit": "Войти",
  "login.submitting": "Вход...",
  "login.noAccount": "Нет аккаунта? Зарегистрироваться",
  "login.haveAccount": "Уже есть аккаунт? Войти",
  "login.failed": "Ошибка входа",
  "login.heroTitle": "Анализ данных через диалог",
  "login.heroSub": "Загрузите таблицу или подключитесь к БД. DataSearcher сам напишет SQL, построит графики и найдёт инсайты.",
  "login.feature1": "46 аналитических инструментов",
  "login.feature2": "SQL по вопросу на русском",
  "login.feature3": "Графики, дашборды, ML-прогнозы",
  "register.title": "Регистрация",
  "register.sub": "Создайте аккаунт для работы с DataSearcher",
  "register.name": "Имя",
  "register.namePlaceholder": "Как вас называть?",
  "register.passwordShort": "Пароль минимум 6 символов",
  "register.failed": "Ошибка регистрации",
  "register.submit": "Зарегистрироваться",
  "register.submitting": "Регистрация...",

  // ── profile card ──
  "profile.setupDone": "Настройка завершена",
  "profile.step": "Step {n} of {total}",
  "profile.newSession": "Новая сессия анализа",
  "profile.notifications": "Уведомления",
  "profile.roleAdmin": "Administrator",
  "profile.roleAnalyst": "Analyst",
  "profile.roleViewer": "Viewer",
  "profile.user": "Пользователь",

  // ── left column ──
  "left.title": "Сессии",
  "left.chip.files": "Файлы",
  "left.chip.history": "История",
  "left.chip.schema": "Схема",
  "left.chip.databases": "БД",
  "left.chip.dashboards": "Дашборды",
  "left.chip.kb": "База",
  "left.chip.logs": "Логи",
  "left.columns": "Колонки",
  "left.noFiles": "Нет загруженных файлов.",
  "left.noFilesHint": "Перетащите файл в поток анализа.",
  "left.noHistory": "Пока нет запросов",
  "left.clearHistory": "Очистить историю",
  "left.fileMeta": "{rows} стр · {cols} кол · {type}",
  "left.preview": "Предпросмотр",
  "left.mode": "Режим: {mode}",
  "left.modeAuto": "SQL в БД, ML в DuckDB",
  "left.modeRemote": "всё в БД",
  "left.modeDump": "выгрузить в DuckDB",
  "left.modeFederated": "кросс-БД JOIN",
  "left.attach": "Подключить",
  "left.noConnections": "Нет подключений",
  "left.public": "public",
  "left.dashboards": "Дашборды",
  "left.noDashboards": "Нет дашбордов",
  "left.dashMeta": "{tables} табл · {views} просм.",
  "left.open": "Открыть",
  "left.deleteConn": "Удалить подключение",
  "left.deleteDash": "Удалить дашборд",
  "left.deleteConfirmConn": "Удалить подключение \"{name}\"?",
  "left.deleteConfirmDash": "Удалить дашборд \"{name}\"?",
  "left.attachError": "Ошибка подключения к БД",
  "left.attachFailed": "Ошибка подключения",
  "left.footer.admin": "Админ-панель",
  "left.footer.llm": "Настройки LLM",
  "left.footer.bi": "BI Link Builder",
  "left.footer.compare": "Сравнить анализы",
  "left.footer.pdf": "Скачать PDF-отчёт",
  "left.footer.setup": "Первичная настройка",
  "left.footer.clear": "Очистить чат",
  "left.footer.logout": "Выйти",
  "left.quickAnalysis": "Новый быстрый анализ",

  // ── right column ──
  "right.summary": "Состояние",
  "right.draft": "Draft",
  "right.active": "Active",
  "right.type": "Тип использования",
  "right.llm": "LLM модель",
  "right.tables": "Таблиц загружено",
  "right.stream": "Стрим",
  "right.streamActive": "выполняется",
  "right.streamIdle": "ожидание",
  "right.rowsMetric": "Строк в анализе",
  "right.colsPill": "Колонок",
  "right.connsPill": "Подключений БД",
  "right.action": "Анализ",
  "right.template.overview": "Обзор данных",
  "right.template.dashboard": "Дашборд",
  "right.template.audit": "Аудит качества",
  "right.template.insights": "Инсайты",
  "right.cta.run": "Запустить анализ",
  "right.cta.noData": "Загрузите данные",
  "right.cta.hint": "Сначала загрузите данные",
  "right.sec.readonly": "read-only",
  "right.sec.pii": "PII",
  "right.sec.logs": "логи",
  "right.sec.ratelimit": "rate limit",
  "right.modeMcp": "MCP",
  "right.modeInterface": "Interface",
  "right.notSet": "не задана",
  "right.waiting": "ожидание",

  // ── chat stream ──
  "chat.canvasTitle": "Анализ данных",
  "chat.statusStreaming": "Анализ выполняется",
  "chat.statusTables": "{n} таблиц в работе",
  "chat.statusWaiting": "Ожидание данных",
  "chat.heroTitle": "Анализ данных\nчерез диалог",
  "chat.heroSub": "Загрузите таблицу или подключитесь к БД — задайте вопрос, ИИ сам напишет SQL, построит графики и найдёт инсайты.",
  "chat.upload": "Перетащите файл или нажмите",
  "chat.uploadActive": "Загрузка файла...",
  "chat.uploadHint": ".xlsx, .csv, .parquet — до 100 МБ",
  "chat.dbConnect": "Подключить базу данных",
  "chat.dbHint": "PostgreSQL, MySQL, ClickHouse, SQLite",
  "chat.qa1.title": "Обзор данных",
  "chat.qa1.sub": "структура, типы, пропуски",
  "chat.qa2.title": "Дашборд",
  "chat.qa2.sub": "ключевые метрики и графики",
  "chat.qa3.title": "Аудит качества",
  "chat.qa3.sub": "дубликаты, аномалии",
  "chat.qa4.title": "Инсайты",
  "chat.qa4.sub": "топ-5 находок автоматически",
  "chat.query.overview": "Сделай краткий обзор структуры данных: типы колонок, пропуски, уникальные значения",
  "chat.query.dashboard": "Построй дашборд с ключевыми метриками и визуализациями",
  "chat.query.audit": "Проведи аудит качества данных: найди дубликаты, пропуски, аномалии и выбросы",
  "chat.query.insights": "Найди топ-5 инсайтов в данных автоматически",
  "chat.autoMessage": "Сделай краткий обзор структуры данных и построй дашборд с ключевыми метриками",
  "chat.inputPlaceholder": "Опишите, что нужно проанализировать...",
  "chat.inputPlaceholderDisabled": "Загрузите файл или пройдите настройку для начала анализа...",
  "chat.send": "Отправить",
  "chat.stop": "Остановить",
  "chat.attachFile": "Загрузить файл",
  "chat.stopped": "Остановлено",
  "chat.dbForm.title": "Подключение к БД",
  "chat.dbForm.name": "Название",
  "chat.dbForm.namePlaceholder": "Моя БД",
  "chat.dbForm.type": "Тип",
  "chat.dbForm.host": "Хост",
  "chat.dbForm.port": "Порт",
  "chat.dbForm.user": "Пользователь",
  "chat.dbForm.password": "Пароль",
  "chat.dbForm.database": "База данных",
  "chat.dbForm.databasePlaceholder": "mydb",
  "chat.dbForm.sqlitePath": "Путь к файлу",
  "chat.dbForm.sqlitePlaceholder": "/path/to/db.sqlite",
  "chat.dbForm.public": "Публичное (доступно всем)",
  "chat.dbForm.submit": "Подключить",
  "chat.dbForm.submitting": "Подключение...",
  "chat.dbForm.attachFailed": "Не удалось подключить",
  "chat.dbForm.error": "Ошибка подключения",
  "chat.dashPublic": "Публичная ссылка",
  "chat.dashPassword": "Защищён паролем ·",
  "chat.openDash": "Открыть",
  "chat.download": "Скачать",
  "chat.exportRows": "строк",

  // ── templates ──
  "tpl.title": "Шаблоны анализа",
  "tpl.overview": "Обзор данных",
  "tpl.overviewDesc": "Структура, типы, пропуски, топ-значения",
  "tpl.dashboard": "Дашборд",
  "tpl.dashboardDesc": "Ключевые метрики и графики",
  "tpl.audit": "Аудит качества",
  "tpl.auditDesc": "Дубликаты, аномалии, пропуски",
  "tpl.trend": "Тренды и прогноз",
  "tpl.trendDesc": "Временные ряды и прогнозирование",
  "tpl.correlations": "Корреляции",
  "tpl.correlationsDesc": "Связи между переменными",
  "tpl.story": "История данных",
  "tpl.storyDesc": "Полный нарратив и инсайты",
  "tpl.query.trend": "Проанализируй временные тренды и построй прогноз",
  "tpl.query.correlations": "Найди корреляции и взаимосвязи между переменными",
  "tpl.query.story": "Расскажи историю данных — ключевые находки и инсайты",
};

export type DictKey = keyof typeof ru;

const en: Record<string, string> = {
  // ── common ──
  "common.loading": "Loading...",
  "common.loadingData": "Loading data...",
  "common.cancel": "Cancel",
  "common.copy": "Copy",
  "common.copied": "Copied",
  "common.download": "Download",
  "common.delete": "Delete",
  "common.close": "Close",
  "common.save": "Save",
  "common.back": "Back",
  "common.next": "Next",
  "common.confirm": "Confirm",
  "common.test": "Test",
  "common.create": "Create",
  "common.error": "Error",
  "common.saved": "Saving...",
  "common.langTitle": "Switch language",
  "common.langName": "English",

  // ── login / register ──
  "login.title": "Sign in",
  "login.sub": "Enter your account email and password",
  "login.email": "Email",
  "login.password": "Password",
  "login.passwordHint": "At least 6 characters",
  "login.submit": "Sign in",
  "login.submitting": "Signing in...",
  "login.noAccount": "No account yet? Register",
  "login.haveAccount": "Already have an account? Sign in",
  "login.failed": "Sign-in failed",
  "login.heroTitle": "Data analysis\nthrough dialogue",
  "login.heroSub": "Upload a table or connect a database. DataSearcher writes the SQL, builds charts and finds insights for you.",
  "login.feature1": "46 analytical tools",
  "login.feature2": "SQL from a plain-language question",
  "login.feature3": "Charts, dashboards, ML forecasts",
  "register.title": "Register",
  "register.sub": "Create an account to work with DataSearcher",
  "register.name": "Name",
  "register.namePlaceholder": "What should we call you?",
  "register.passwordShort": "Password must be at least 6 characters",
  "register.failed": "Registration failed",
  "register.submit": "Create account",
  "register.submitting": "Registering...",

  // ── profile card ──
  "profile.setupDone": "Setup complete",
  "profile.step": "Step {n} of {total}",
  "profile.newSession": "New analysis session",
  "profile.notifications": "Notifications",
  "profile.roleAdmin": "Administrator",
  "profile.roleAnalyst": "Analyst",
  "profile.roleViewer": "Viewer",
  "profile.user": "User",

  // ── left column ──
  "left.title": "Sessions",
  "left.chip.files": "Files",
  "left.chip.history": "History",
  "left.chip.schema": "Schema",
  "left.chip.databases": "DB",
  "left.chip.dashboards": "Dashboards",
  "left.chip.kb": "Knowledge",
  "left.chip.logs": "Logs",
  "left.columns": "Columns",
  "left.noFiles": "No uploaded files.",
  "left.noFilesHint": "Drop a file into the analysis stream.",
  "left.noHistory": "No queries yet",
  "left.clearHistory": "Clear history",
  "left.fileMeta": "{rows} rows · {cols} cols · {type}",
  "left.preview": "Preview",
  "left.mode": "Mode: {mode}",
  "left.modeAuto": "SQL in source DB, ML in DuckDB",
  "left.modeRemote": "everything in source DB",
  "left.modeDump": "dump into DuckDB",
  "left.modeFederated": "cross-DB JOIN",
  "left.attach": "Attach",
  "left.noConnections": "No connections",
  "left.public": "public",
  "left.dashboards": "Dashboards",
  "left.noDashboards": "No dashboards",
  "left.dashMeta": "{tables} tables · {views} views",
  "left.open": "Open",
  "left.deleteConn": "Delete connection",
  "left.deleteDash": "Delete dashboard",
  "left.deleteConfirmConn": "Delete connection \"{name}\"?",
  "left.deleteConfirmDash": "Delete dashboard \"{name}\"?",
  "left.attachError": "Failed to attach database",
  "left.attachFailed": "Connection failed",
  "left.footer.admin": "Admin panel",
  "left.footer.llm": "LLM settings",
  "left.footer.bi": "BI Link Builder",
  "left.footer.compare": "Compare analyses",
  "left.footer.pdf": "Download PDF report",
  "left.footer.setup": "Primary setup",
  "left.footer.clear": "Clear chat",
  "left.footer.logout": "Sign out",
  "left.quickAnalysis": "New quick analysis",

  // ── right column ──
  "right.summary": "State",
  "right.draft": "Draft",
  "right.active": "Active",
  "right.type": "Usage type",
  "right.llm": "LLM model",
  "right.tables": "Tables loaded",
  "right.stream": "Stream",
  "right.streamActive": "running",
  "right.streamIdle": "idle",
  "right.rowsMetric": "Rows in analysis",
  "right.colsPill": "Columns",
  "right.connsPill": "DB connections",
  "right.action": "Analysis",
  "right.template.overview": "Data overview",
  "right.template.dashboard": "Dashboard",
  "right.template.audit": "Quality audit",
  "right.template.insights": "Insights",
  "right.cta.run": "Run analysis",
  "right.cta.noData": "Load data first",
  "right.cta.hint": "Upload data first",
  "right.sec.readonly": "read-only",
  "right.sec.pii": "PII",
  "right.sec.logs": "logs",
  "right.sec.ratelimit": "rate limit",
  "right.modeMcp": "MCP",
  "right.modeInterface": "Interface",
  "right.notSet": "not set",
  "right.waiting": "idle",

  // ── chat stream ──
  "chat.canvasTitle": "Data analysis",
  "chat.statusStreaming": "Analysis in progress",
  "chat.statusTables": "{n} tables in session",
  "chat.statusWaiting": "Waiting for data",
  "chat.heroTitle": "Data analysis\nthrough dialogue",
  "chat.heroSub": "Upload a table or connect a database, then just ask — the AI writes SQL, builds charts and finds insights.",
  "chat.upload": "Drop a file or click to upload",
  "chat.uploadActive": "Uploading file...",
  "chat.uploadHint": ".xlsx, .csv, .parquet — up to 100 MB",
  "chat.dbConnect": "Connect a database",
  "chat.dbHint": "PostgreSQL, MySQL, ClickHouse, SQLite",
  "chat.qa1.title": "Data overview",
  "chat.qa1.sub": "structure, types, gaps",
  "chat.qa2.title": "Dashboard",
  "chat.qa2.sub": "key metrics and charts",
  "chat.qa3.title": "Quality audit",
  "chat.qa3.sub": "duplicates, anomalies",
  "chat.qa4.title": "Insights",
  "chat.qa4.sub": "top-5 findings automatically",
  "chat.query.overview": "Give a brief overview of the data structure: column types, missing values, unique values",
  "chat.query.dashboard": "Build a dashboard with key metrics and visualizations",
  "chat.query.audit": "Run a data quality audit: find duplicates, missing values, anomalies and outliers",
  "chat.query.insights": "Find the top 5 insights in the data automatically",
  "chat.autoMessage": "Give a brief overview of the data structure and build a dashboard with key metrics",
  "chat.inputPlaceholder": "Describe what to analyze...",
  "chat.inputPlaceholderDisabled": "Upload a file or finish setup to start analyzing...",
  "chat.send": "Send",
  "chat.stop": "Stop",
  "chat.attachFile": "Upload file",
  "chat.stopped": "Stopped",
  "chat.dbForm.title": "Database connection",
  "chat.dbForm.name": "Name",
  "chat.dbForm.namePlaceholder": "My DB",
  "chat.dbForm.type": "Type",
  "chat.dbForm.host": "Host",
  "chat.dbForm.port": "Port",
  "chat.dbForm.user": "Username",
  "chat.dbForm.password": "Password",
  "chat.dbForm.database": "Database",
  "chat.dbForm.databasePlaceholder": "mydb",
  "chat.dbForm.sqlitePath": "File path",
  "chat.dbForm.sqlitePlaceholder": "/path/to/db.sqlite",
  "chat.dbForm.public": "Public (visible to everyone)",
  "chat.dbForm.submit": "Connect",
  "chat.dbForm.submitting": "Connecting...",
  "chat.dbForm.attachFailed": "Could not attach",
  "chat.dbForm.error": "Connection error",
  "chat.dashPublic": "Public link",
  "chat.dashPassword": "Password protected ·",
  "chat.openDash": "Open",
  "chat.download": "Download",
  "chat.exportRows": "rows",

  // ── templates ──
  "tpl.title": "Analysis templates",
  "tpl.overview": "Data overview",
  "tpl.overviewDesc": "Structure, types, gaps, top values",
  "tpl.dashboard": "Dashboard",
  "tpl.dashboardDesc": "Key metrics and charts",
  "tpl.audit": "Quality audit",
  "tpl.auditDesc": "Duplicates, anomalies, gaps",
  "tpl.trend": "Trends & forecast",
  "tpl.trendDesc": "Time series and forecasting",
  "tpl.correlations": "Correlations",
  "tpl.correlationsDesc": "Relationships between variables",
  "tpl.story": "Data story",
  "tpl.storyDesc": "Full narrative with insights",
  "tpl.query.trend": "Analyze time trends and build a forecast",
  "tpl.query.correlations": "Find correlations and relationships between variables",
  "tpl.query.story": "Tell the story of this data — key findings and insights",
};

/* ── setup wizard ── */
ru["setup.sideSub"] = "Первичная настройка";
ru["setup.step1"] = "Тип";
ru["setup.step1desc"] = "MCP или Interface";
ru["setup.step2"] = "Параметры";
ru["setup.step2desc"] = "LLM API";
ru["setup.step3"] = "Данные";
ru["setup.step3desc"] = "Файлы и БД";
ru["setup.step4"] = "Готово";
ru["setup.step4desc"] = "Проверка и запуск";
ru["setup.step"] = "Step {n} of {total}";
ru["setup.done"] = "Готово";
ru["setup.step1Title"] = "Как вы будете использовать DataSearcher?";
ru["setup.step1Sub"] = "Выберите тип подключения. Позже его можно изменить в настройках.";
ru["setup.typeInterface"] = "Interface";
ru["setup.typeInterfaceDesc"] = "Веб-приложение с чатом, графиками и дашбордами. Доступно сразу после настройки.";
ru["setup.typeMcp"] = "MCP";
ru["setup.typeMcpDesc"] = "Сервер для Claude Desktop, Cursor и VS Code. На финальном шаге мы сгенерируем готовые конфиги.";
ru["setup.step2Title"] = "Параметры ИИ";
ru["setup.step2Sub"] = "LLM нужен для генерации SQL и интерпретации вопросов на русском.";
ru["setup.baseUrl"] = "LLM BASE URL";
ru["setup.baseUrlPlaceholder"] = "http://localhost:11434/v1";
ru["setup.model"] = "МОДЕЛЬ";
ru["setup.modelPlaceholder"] = "qwen2.5:14b";
ru["setup.apiKey"] = "API KEY (НЕОБЯЗАТЕЛЬНО)";
ru["setup.apiKeyPlaceholder"] = "sk-...";
ru["setup.apiKeySaved"] = "•••• сохранён";
ru["setup.test"] = "Проверить";
ru["setup.testConnected"] = "Подключено";
ru["setup.testHint"] = "OpenAI-совместимый API: Ollama, vLLM, OpenAI, agentplatform. Проверка не обязательна — можно продолжить и настроить позже.";
ru["setup.step3Title"] = "Данные для анализа";
ru["setup.step3Sub"] = "Загрузите файл или подключите базу данных — можно пропустить и сделать позже.";
ru["setup.upload"] = "Загрузить файл";
ru["setup.uploaded"] = "Файл «{name}» загружен";
ru["setup.dbForm.title"] = "Подключение к БД";
ru["setup.dbForm.create"] = "Создать подключение";
ru["setup.dbForm.creating"] = "Создание...";
ru["setup.createdConns"] = "Созданные подключения:";
ru["setup.connCreated"] = "Подключение «{name}» создано";
ru["setup.step4Title"] = "Проверьте и запустите";
ru["setup.step4Sub"] = "Параметры безопасности читаются из env-конфигурации сервера.";
ru["setup.summary"] = "Сводка";
ru["setup.summaryType"] = "Тип";
ru["setup.summaryLlm"] = "LLM";
ru["setup.scopeTitle"] = "Кому применить настройки";
ru["setup.scopeAll"] = "Для всех пользователей";
ru["setup.scopeMe"] = "Только для меня";
ru["setup.scopeHint"] = "Настройки будут применены к вашему аккаунту.";
ru["setup.entHint"] = "Enterprise-тумблеры управляются переменными окружения (.env) и перечитываются при рестарте сервера.";
ru["setup.generate"] = "Сгенерировать конфиг";
ru["setup.finishTitle"] = "Всё готово";
ru["setup.finishSub"] = "Настройка сохранена. Загрузите данные и задайте первый вопрос.";
ru["setup.startAnalysis"] = "Начать анализ";
ru["setup.enterApp"] = "Перейти в DataSearcher";
ru["setup.mcpReadyTitle"] = "Конфигурации MCP готовы";
ru["setup.mcpReadySub"] = "Сгенерировано из ваших подключений ({n}). Скопируйте конфиги и подключите DataSearcher к своему ИИ-клиенту.";
ru["setup.mcpNoConns"] = "Сохраните параметры — конфиг можно сгенерировать позже из вкладки «БД».";
ru["setup.mcpNoConnsHint"] = "Подключения не найдены. Добавьте их во вкладке «БД» и повторите генерацию через «Первичная настройка» в левой колонке.";
ru["setup.configWarn"] = "Конфиг содержит пароли подключений — храните файл в безопасном месте.";
ru["setup.block.yaml"] = "connections.yaml";
ru["setup.block.claude"] = "Claude Desktop — claude_desktop_config.json";
ru["setup.block.cursor"] = "Cursor — .cursor/mcp.json";
ru["setup.block.http"] = "HTTP-запуск";
ru["setup.block.env"] = ".env (LLM)";

en["setup.sideSub"] = "Primary setup";
en["setup.step1"] = "Type";
en["setup.step1desc"] = "MCP or Interface";
en["setup.step2"] = "Parameters";
en["setup.step2desc"] = "LLM API";
en["setup.step3"] = "Data";
en["setup.step3desc"] = "Files and DBs";
en["setup.step4"] = "Finish";
en["setup.step4desc"] = "Review and launch";
en["setup.step"] = "Step {n} of {total}";
en["setup.done"] = "Done";
en["setup.step1Title"] = "How will you use DataSearcher?";
en["setup.step1Sub"] = "Choose the usage type. You can change it later in settings.";
en["setup.typeInterface"] = "Interface";
en["setup.typeInterfaceDesc"] = "Web app with chat, charts and dashboards. Ready right after setup.";
en["setup.typeMcp"] = "MCP";
en["setup.typeMcpDesc"] = "Server for Claude Desktop, Cursor and VS Code. The final step generates ready-to-use configs.";
en["setup.step2Title"] = "AI parameters";
en["setup.step2Sub"] = "The LLM generates SQL and interprets plain-language questions.";
en["setup.baseUrl"] = "LLM BASE URL";
en["setup.baseUrlPlaceholder"] = "http://localhost:11434/v1";
en["setup.model"] = "MODEL";
en["setup.modelPlaceholder"] = "qwen2.5:14b";
en["setup.apiKey"] = "API KEY (OPTIONAL)";
en["setup.apiKeyPlaceholder"] = "sk-...";
en["setup.apiKeySaved"] = "•••• saved";
en["setup.test"] = "Test";
en["setup.testConnected"] = "Connected";
en["setup.testHint"] = "OpenAI-compatible API: Ollama, vLLM, OpenAI, agentplatform. Testing is optional — you can continue and configure later.";
en["setup.step3Title"] = "Data to analyze";
en["setup.step3Sub"] = "Upload a file or connect a database — you can skip this and do it later.";
en["setup.upload"] = "Upload file";
en["setup.uploaded"] = "File \"{name}\" uploaded";
en["setup.dbForm.title"] = "Database connection";
en["setup.dbForm.create"] = "Create connection";
en["setup.dbForm.creating"] = "Creating...";
en["setup.createdConns"] = "Created connections:";
en["setup.connCreated"] = "Connection \"{name}\" created";
en["setup.step4Title"] = "Review and launch";
en["setup.step4Sub"] = "Security settings are read from the server env configuration.";
en["setup.summary"] = "Summary";
en["setup.summaryType"] = "Type";
en["setup.summaryLlm"] = "LLM";
en["setup.scopeTitle"] = "Who should these settings apply to";
en["setup.scopeAll"] = "All users";
en["setup.scopeMe"] = "Only me";
en["setup.scopeHint"] = "Settings will be applied to your account.";
en["setup.entHint"] = "Enterprise toggles are managed via environment variables (.env) and re-read on server restart.";
en["setup.generate"] = "Generate config";
en["setup.finishTitle"] = "All set";
en["setup.finishSub"] = "Setup saved. Upload data and ask your first question.";
en["setup.startAnalysis"] = "Start analyzing";
en["setup.enterApp"] = "Open DataSearcher";
en["setup.mcpReadyTitle"] = "MCP configurations are ready";
en["setup.mcpReadySub"] = "Generated from your connections ({n}). Copy the configs and plug DataSearcher into your AI client.";
en["setup.mcpNoConns"] = "Save the parameters — you can generate the config later from the \"DB\" tab.";
en["setup.mcpNoConnsHint"] = "No connections found. Add them in the \"DB\" tab and regenerate via \"Primary setup\" in the left column.";
en["setup.configWarn"] = "The config contains connection passwords — keep the file in a safe place.";
en["setup.block.yaml"] = "connections.yaml";
en["setup.block.claude"] = "Claude Desktop — claude_desktop_config.json";
en["setup.block.cursor"] = "Cursor — .cursor/mcp.json";
en["setup.block.http"] = "HTTP launch";
en["setup.block.env"] = ".env (LLM)";

/* ── tool labels (46) ── */
ru["tool.get_schema"] = "Схема";
ru["tool.sql_query"] = "SQL";
ru["tool.profile_data"] = "Профиль";
ru["tool.classify_rows"] = "Классификация";
ru["tool.find_duplicates"] = "Дубликаты";
ru["tool.detect_anomalies"] = "Аномалии";
ru["tool.sample_data"] = "Выборка";
ru["tool.correlation_analysis"] = "Корреляция";
ru["tool.distribution_analysis"] = "Распределение";
ru["tool.cross_tab"] = "Кросс-таб";
ru["tool.pivot_table"] = "Сводная";
ru["tool.segment_data"] = "Сегментация";
ru["tool.compare_tables"] = "Сравнение";
ru["tool.time_analysis"] = "Временной ряд";
ru["tool.data_quality_report"] = "Качество";
ru["tool.smart_summary"] = "Саммари";
ru["tool.generate_sql"] = "Генерация SQL";
ru["tool.visualize_data"] = "График";
ru["tool.predict_trend"] = "Прогноз";
ru["tool.cluster_analysis"] = "Кластеры";
ru["tool.feature_importance"] = "Важность";
ru["tool.statistical_test"] = "Стат. тест";
ru["tool.auto_insights"] = "Инсайты";
ru["tool.transform_data"] = "Трансформация";
ru["tool.merge_tables"] = "Merge";
ru["tool.export_data"] = "Экспорт";
ru["tool.detect_patterns"] = "Паттерны";
ru["tool.build_dashboard"] = "Дашборд";
ru["tool.data_story"] = "История";
ru["tool.create_public_dashboard"] = "Публ. дашборд";
ru["tool.query_explain"] = "EXPLAIN";
ru["tool.attach_database"] = "Подключение БД";
ru["tool.refresh_schema"] = "Обновление схемы";
ru["tool.test_connection"] = "Тест подключения";
ru["tool.load_file"] = "Загрузка файла";
ru["tool.scan_pii"] = "Скан PII";
ru["tool.get_logs"] = "Логи";
ru["tool.add_example"] = "Добавить пример";
ru["tool.search_knowledge"] = "Поиск по KB";
ru["tool.load_dbt"] = "Загрузка dbt";
ru["tool.sync_datahub"] = "Синхр. DataHub";
ru["tool.list_metrics"] = "Метрики";
ru["tool.update_metadata"] = "Метаданные";
ru["tool.build_bi_link"] = "BI-ссылка";
ru["tool.export_xlsx"] = "Экспорт XLSX";
ru["tool.semantic_search"] = "Семантический поиск";
ru["tool.args"] = "Аргументы";
ru["tool.result"] = "Результат";

en["tool.get_schema"] = "Schema";
en["tool.sql_query"] = "SQL";
en["tool.profile_data"] = "Profile";
en["tool.classify_rows"] = "Classification";
en["tool.find_duplicates"] = "Duplicates";
en["tool.detect_anomalies"] = "Anomalies";
en["tool.sample_data"] = "Sample";
en["tool.correlation_analysis"] = "Correlation";
en["tool.distribution_analysis"] = "Distribution";
en["tool.cross_tab"] = "Cross-tab";
en["tool.pivot_table"] = "Pivot";
en["tool.segment_data"] = "Segmentation";
en["tool.compare_tables"] = "Comparison";
en["tool.time_analysis"] = "Time series";
en["tool.data_quality_report"] = "Quality";
en["tool.smart_summary"] = "Summary";
en["tool.generate_sql"] = "Generate SQL";
en["tool.visualize_data"] = "Chart";
en["tool.predict_trend"] = "Forecast";
en["tool.cluster_analysis"] = "Clusters";
en["tool.feature_importance"] = "Importance";
en["tool.statistical_test"] = "Stat test";
en["tool.auto_insights"] = "Insights";
en["tool.transform_data"] = "Transform";
en["tool.merge_tables"] = "Merge";
en["tool.export_data"] = "Export";
en["tool.detect_patterns"] = "Patterns";
en["tool.build_dashboard"] = "Dashboard";
en["tool.data_story"] = "Story";
en["tool.create_public_dashboard"] = "Public dashboard";
en["tool.query_explain"] = "EXPLAIN";
en["tool.attach_database"] = "Attach DB";
en["tool.refresh_schema"] = "Refresh schema";
en["tool.test_connection"] = "Test connection";
en["tool.load_file"] = "Load file";
en["tool.scan_pii"] = "PII scan";
en["tool.get_logs"] = "Logs";
en["tool.add_example"] = "Add example";
en["tool.search_knowledge"] = "KB search";
en["tool.load_dbt"] = "Load dbt";
en["tool.sync_datahub"] = "DataHub sync";
en["tool.list_metrics"] = "Metrics";
en["tool.update_metadata"] = "Metadata";
en["tool.build_bi_link"] = "BI link";
en["tool.export_xlsx"] = "Export XLSX";
en["tool.semantic_search"] = "Semantic search";
en["tool.args"] = "Arguments";
en["tool.result"] = "Result";

/* ── progress / steps ── */
ru["progress.steps"] = "{done}/{total} шагов";
ru["progress.trend"] = "📈 Показать тренд";
ru["progress.forecast"] = "🔮 Спрогнозировать на 3 месяца";
ru["progress.visualize"] = "📊 Визуализировать графиком";
ru["progress.correlations"] = "🔗 Найти корреляции";
ru["progress.crossTab"] = "⊞ Кросс-табуляция";
ru["progress.cluster"] = "🎯 Кластеризация";
ru["progress.statTest"] = "🧪 Статистический тест";
ru["progress.autoInsights"] = "✨ Авто-инсайты";
ru["progress.quality"] = "✅ Качество данных";
ru["progress.visualize2"] = "📊 Визуализировать";
ru["progress.story"] = "📖 История данных";
ru["progress.publicDash"] = "📋 Создай публичный дашборд через create_public_dashboard";

en["progress.steps"] = "{done}/{total} steps";
en["progress.trend"] = "📈 Show trend";
en["progress.forecast"] = "🔮 Forecast 3 months ahead";
en["progress.visualize"] = "📊 Visualize with a chart";
en["progress.correlations"] = "🔗 Find correlations";
en["progress.crossTab"] = "⊞ Cross-tabulation";
en["progress.cluster"] = "🎯 Clustering";
en["progress.statTest"] = "🧪 Statistical test";
en["progress.autoInsights"] = "✨ Auto-insights";
en["progress.quality"] = "✅ Data quality";
en["progress.visualize2"] = "📊 Visualize";
en["progress.story"] = "📖 Data story";
en["progress.publicDash"] = "📋 Create a public dashboard via create_public_dashboard";

/* ── table / chart / status ── */
ru["table.rowsCols"] = "{rows} строк × {cols} колонок";
ru["table.search"] = "Поиск...";
ru["table.nothing"] = "Ничего не найдено";
ru["table.copyCsv"] = "Копировать CSV";
ru["chart.unsupported"] = "Неподдерживаемый тип графика: {type}";
ru["chart.savePng"] = "Сохранить PNG";
ru["chart.chart"] = "График";
ru["status.tables"] = "{n} таблиц";
ru["status.rows"] = "{n} строк";
ru["status.cols"] = "{n} колонок";
ru["status.seconds"] = "{n}s";
ru["files.title"] = "Файлы";
ru["files.drop"] = "Перетащите файл или нажмите";
ru["files.uploading"] = "Загрузка...";
ru["files.hint"] = ".xlsx, .csv";
ru["files.rowsShort"] = "{n} стр.";
ru["upload.loading"] = "Загрузка...";

en["table.rowsCols"] = "{rows} rows × {cols} columns";
en["table.search"] = "Search...";
en["table.nothing"] = "Nothing found";
en["table.copyCsv"] = "Copy CSV";
en["chart.unsupported"] = "Unsupported chart type: {type}";
en["chart.savePng"] = "Save PNG";
en["chart.chart"] = "Chart";
en["status.tables"] = "{n} tables";
en["status.rows"] = "{n} rows";
en["status.cols"] = "{n} columns";
en["status.seconds"] = "{n}s";
en["files.title"] = "Files";
en["files.drop"] = "Drop a file or click to upload";
en["files.uploading"] = "Uploading...";
en["files.hint"] = ".xlsx, .csv";
en["files.rowsShort"] = "{n} rows";
en["upload.loading"] = "Uploading...";

/* ── modals ── */
ru["modal.llmTitle"] = "Подключение LLM";
ru["modal.baseUrl"] = "Base URL";
ru["modal.baseUrlHint"] = "OpenAI-совместимый API (Ollama, vLLM, OpenAI и др.)";
ru["modal.apiKey"] = "API Key";
ru["modal.apiKeyPlaceholder"] = "sk-... (оставьте пустым для локальных моделей)";
ru["modal.apiKeyHint"] = "Необязательно для локальных моделей (Ollama, LM Studio)";
ru["modal.model"] = "Модель";
ru["modal.modelHint"] = "Имя модели, распознаваемое вашим LLM-провайдером";
ru["modal.testStatus.testing"] = "Проверка подключения...";
ru["modal.testStatus.ok"] = "Подключено";
ru["modal.testStatus.fail"] = "Не удалось подключиться";
ru["modal.save"] = "Сохранить";
ru["modal.saving"] = "Сохранение...";
ru["modal.connectedModels"] = "({n} моделей)";
ru["modal.preview.rows"] = "{rows} строк · {cols} колонок";
ru["modal.preview.first50"] = "Показано первых 50 строк";
ru["modal.preview.error"] = "Ошибка: {msg}";
ru["modal.bi.title"] = "BI Link Builder";
ru["modal.bi.tool"] = "BI-инструмент";
ru["modal.bi.baseUrl"] = "Базовый URL";
ru["modal.bi.dashId"] = "ID дашборда / чарта";
ru["modal.bi.timeFrom"] = "С (для Grafana)";
ru["modal.bi.timeTo"] = "По";
ru["modal.bi.filters"] = "Фильтры (JSON)";
ru["modal.bi.generate"] = "Сгенерировать ссылку";
ru["modal.bi.generating"] = "Генерация…";
ru["modal.bi.generated"] = "Сгенерированная ссылка:";
ru["modal.bi.baseUrlRequired"] = "Укажите базовый URL";
ru["modal.bi.paramsJson"] = "params должен быть валидным JSON";

en["modal.llmTitle"] = "LLM connection";
en["modal.baseUrl"] = "Base URL";
en["modal.baseUrlHint"] = "OpenAI-compatible API (Ollama, vLLM, OpenAI and others)";
en["modal.apiKey"] = "API Key";
en["modal.apiKeyPlaceholder"] = "sk-... (leave empty for local models)";
en["modal.apiKeyHint"] = "Optional for local models (Ollama, LM Studio)";
en["modal.model"] = "Model";
en["modal.modelHint"] = "Model name recognized by your LLM provider";
en["modal.testStatus.testing"] = "Testing connection...";
en["modal.testStatus.ok"] = "Connected";
en["modal.testStatus.fail"] = "Connection failed";
en["modal.save"] = "Save";
en["modal.saving"] = "Saving...";
en["modal.connectedModels"] = "({n} models)";
en["modal.preview.rows"] = "{rows} rows · {cols} columns";
en["modal.preview.first50"] = "Showing first 50 rows";
en["modal.preview.error"] = "Error: {msg}";
en["modal.bi.title"] = "BI Link Builder";
en["modal.bi.tool"] = "BI tool";
en["modal.bi.baseUrl"] = "Base URL";
en["modal.bi.dashId"] = "Dashboard / chart ID";
en["modal.bi.timeFrom"] = "From (for Grafana)";
en["modal.bi.timeTo"] = "To";
en["modal.bi.filters"] = "Filters (JSON)";
en["modal.bi.generate"] = "Generate link";
en["modal.bi.generating"] = "Generating…";
en["modal.bi.generated"] = "Generated link:";
en["modal.bi.baseUrlRequired"] = "Provide the base URL";
en["modal.bi.paramsJson"] = "params must be valid JSON";

/* ── knowledge / logs / schema ── */
ru["kb.title"] = "База знаний";
ru["kb.search"] = "Поиск по метаданным…";
ru["kb.results"] = "Результаты поиска:";
ru["kb.tables"] = "Таблицы ({n})";
ru["kb.metrics"] = "Метрики ({n})";
ru["kb.noMetadata"] = "Нет метаданных. Загрузите dbt или подключите БД.";
ru["kb.dbtTitle"] = "Загрузить dbt manifest.json";
ru["kb.datahubTitle"] = "Синхронизировать DataHub";
ru["kb.dbtLoaded"] = "dbt загружен: моделей {models}, источников {sources}, колонок {columns}";
ru["kb.datahubSynced"] = "Синхронизировано из DataHub: {n}";
ru["kb.metricName"] = "Имя метрики";
ru["kb.metricFormula"] = "Формула";
ru["kb.metricDesc"] = "Описание";
ru["kb.metricOwner"] = "Владелец";
ru["kb.deleteMetric"] = "Удалить метрику \"{name}\"?";
ru["logs.title"] = "Логи";
ru["logs.tab.query"] = "Запросы";
ru["logs.tab.error"] = "Ошибки";
ru["logs.tab.audit"] = "Аудит";
ru["logs.empty.query"] = "Лог запросов пуст";
ru["logs.empty.error"] = "Лог ошибок пуст";
ru["logs.empty.audit"] = "Лог аудита пуст";
ru["schema.title"] = "Схема данных";
ru["schema.rows"] = "{n} строк";

en["kb.title"] = "Knowledge base";
en["kb.search"] = "Search metadata…";
en["kb.results"] = "Search results:";
en["kb.tables"] = "Tables ({n})";
en["kb.metrics"] = "Metrics ({n})";
en["kb.noMetadata"] = "No metadata. Upload dbt or attach a DB.";
en["kb.dbtTitle"] = "Upload dbt manifest.json";
en["kb.datahubTitle"] = "Sync DataHub";
en["kb.dbtLoaded"] = "dbt loaded: {models} models, {sources} sources, {columns} columns";
en["kb.datahubSynced"] = "Synced from DataHub: {n}";
en["kb.metricName"] = "Metric name";
en["kb.metricFormula"] = "Formula";
en["kb.metricDesc"] = "Description";
en["kb.metricOwner"] = "Owner";
en["kb.deleteMetric"] = "Delete metric \"{name}\"?";
en["logs.title"] = "Logs";
en["logs.tab.query"] = "Queries";
en["logs.tab.error"] = "Errors";
en["logs.tab.audit"] = "Audit";
en["logs.empty.query"] = "Query log is empty";
en["logs.empty.error"] = "Error log is empty";
en["logs.empty.audit"] = "Audit log is empty";
en["schema.title"] = "Data schema";
en["schema.rows"] = "{n} rows";

/* ── admin panel ── */
ru["admin.title"] = "Панель администратора";
ru["admin.tab.users"] = "Пользователи";
ru["admin.tab.settings"] = "Настройки";
ru["admin.tab.connections"] = "Базы данных";
ru["admin.tab.security"] = "Безопасность";
ru["admin.loading"] = "Загрузка...";
ru["admin.badge.llm"] = "LLM";
ru["admin.badge.noDb"] = "No DB";
ru["admin.role.admin"] = "Admin";
ru["admin.role.analyst"] = "Analyst";
ru["admin.role.viewer"] = "Viewer";
ru["admin.user.active"] = "Активен";
ru["admin.user.blocked"] = "Заблокирован";
ru["admin.user.settings"] = "Настройки пользователя";
ru["admin.user.deleteConfirm"] = "Удалить пользователя?";
ru["admin.settings.registration"] = "Регистрация пользователей";
ru["admin.settings.registrationDesc"] = "Разрешить новым пользователям регистрироваться";
ru["admin.settings.customLlm"] = "Пользовательские LLM-настройки";
ru["admin.settings.customLlmDesc"] = "Разрешить пользователям менять свои LLM-параметры";
ru["admin.settings.userDb"] = "Пользовательские подключения к БД";
ru["admin.settings.userDbDesc"] = "Разрешить пользователям добавлять свои подключения к БД";
ru["admin.settings.globalLlm"] = "Глобальные LLM-параметры";
ru["admin.settings.llmUrl"] = "LLM URL";
ru["admin.settings.llmModel"] = "LLM Model";
ru["admin.settings.llmKey"] = "LLM API Key";
ru["admin.on"] = "Вкл";
ru["admin.off"] = "Выкл";
ru["admin.connections.add"] = "Добавить подключение";
ru["admin.connections.none"] = "Нет подключений к БД";
ru["admin.connections.deleteConfirm"] = "Удалить подключение?";
ru["admin.connections.attach"] = "Подключить";
ru["admin.connections.attached"] = "Подключено! Загружено таблиц: {n}";
ru["admin.security.note"] = "Enterprise-настройки задаются через переменные окружения (env) и читаются при старте. Измените .env и перезапустите сервер.";
ru["admin.security.readonly"] = "🔒 Read-only guard (блок DML/DDL)";
ru["admin.security.pii"] = "🛡️ PII-маскирование";
ru["admin.security.piiRows"] = "🔍 Строк для скана PII";
ru["admin.security.rate"] = "⏱️ Rate limiting";
ru["admin.security.sqlRate"] = "⚡ SQL-запросов/мин";
ru["admin.security.mlRate"] = "🧪 ML-запросов/мин";
ru["admin.security.defaultMode"] = "🔗 Режим подключений по умолчанию";
ru["admin.security.translate"] = "🔄 sqlglot трансляция диалектов";
ru["admin.security.timeout"] = "⏳ Таймаут SQL (сек)";
ru["admin.security.logging"] = "📜 Логирование";
ru["admin.security.blocked"] = "🚫 Заблокированные паттерны таблиц";
ru["admin.security.exampleStore"] = "⭐ Example Store";
ru["admin.security.semantic"] = "🧬 Лимит semantic_search";
ru["admin.security.datahub"] = "🌐 DataHub URL";
ru["admin.security.dbt"] = "🏗️ dbt manifest";
ru["admin.security.on"] = "вкл";
ru["admin.security.off"] = "выкл";
ru["admin.security.loadFailed"] = "Не удалось загрузить настройки";
ru["admin.detail.back"] = "← Назад";
ru["admin.detail.permissions"] = "Права";
ru["admin.detail.llm"] = "LLM";
ru["admin.detail.db"] = "БД";
ru["admin.detail.customLlm"] = "Кастомные LLM-настройки";
ru["admin.detail.customLlmDesc"] = "Разрешить пользователю свои параметры LLM";
ru["admin.detail.dbConns"] = "Подключения к БД";
ru["admin.detail.dbConnsDesc"] = "Разрешить пользователю подключать базы данных";
ru["admin.detail.savePermissions"] = "Сохранить права";
ru["admin.detail.saveLlm"] = "Сохранить LLM";
ru["admin.detail.llmHint"] = "Настройки LLM для этого пользователя. Оставьте поля пустыми, чтобы использовались глобальные.";
ru["admin.detail.addConn"] = "Добавить подключение";
ru["admin.detail.noConns"] = "Нет подключений";
ru["admin.field.name"] = "Название";
ru["admin.field.type"] = "Тип БД";
ru["admin.field.host"] = "Хост";
ru["admin.field.port"] = "Порт";
ru["admin.field.user"] = "Пользователь";
ru["admin.field.password"] = "Пароль";
ru["admin.field.database"] = "База данных";
ru["admin.field.sqlitePath"] = "Путь к файлу БД";
ru["admin.field.public"] = "Публичное подключение (доступно всем)";
ru["admin.form.creating"] = "Создание...";

en["admin.title"] = "Admin panel";
en["admin.tab.users"] = "Users";
en["admin.tab.settings"] = "Settings";
en["admin.tab.connections"] = "Databases";
en["admin.tab.security"] = "Security";
en["admin.loading"] = "Loading...";
en["admin.badge.llm"] = "LLM";
en["admin.badge.noDb"] = "No DB";
en["admin.role.admin"] = "Admin";
en["admin.role.analyst"] = "Analyst";
en["admin.role.viewer"] = "Viewer";
en["admin.user.active"] = "Active";
en["admin.user.blocked"] = "Blocked";
en["admin.user.settings"] = "User settings";
en["admin.user.deleteConfirm"] = "Delete user?";
en["admin.settings.registration"] = "User registration";
en["admin.settings.registrationDesc"] = "Allow new users to register";
en["admin.settings.customLlm"] = "Custom LLM settings";
en["admin.settings.customLlmDesc"] = "Allow users to change their LLM parameters";
en["admin.settings.userDb"] = "Custom DB connections";
en["admin.settings.userDbDesc"] = "Allow users to add their own DB connections";
en["admin.settings.globalLlm"] = "Global LLM parameters";
en["admin.settings.llmUrl"] = "LLM URL";
en["admin.settings.llmModel"] = "LLM Model";
en["admin.settings.llmKey"] = "LLM API Key";
en["admin.on"] = "On";
en["admin.off"] = "Off";
en["admin.connections.add"] = "Add connection";
en["admin.connections.none"] = "No DB connections";
en["admin.connections.deleteConfirm"] = "Delete connection?";
en["admin.connections.attach"] = "Attach";
en["admin.connections.attached"] = "Attached! Tables loaded: {n}";
en["admin.security.note"] = "Enterprise settings are defined via environment variables (env) and read at startup. Edit .env and restart the server.";
en["admin.security.readonly"] = "🔒 Read-only guard (blocks DML/DDL)";
en["admin.security.pii"] = "🛡️ PII masking";
en["admin.security.piiRows"] = "🔍 Rows for PII scan";
en["admin.security.rate"] = "⏱️ Rate limiting";
en["admin.security.sqlRate"] = "⚡ SQL requests/min";
en["admin.security.mlRate"] = "🧪 ML requests/min";
en["admin.security.defaultMode"] = "🔗 Default connection mode";
en["admin.security.translate"] = "🔄 sqlglot dialect translation";
en["admin.security.timeout"] = "⏳ SQL timeout (sec)";
en["admin.security.logging"] = "📜 Logging";
en["admin.security.blocked"] = "🚫 Blocked table patterns";
en["admin.security.exampleStore"] = "⭐ Example Store";
en["admin.security.semantic"] = "🧬 semantic_search limit";
en["admin.security.datahub"] = "🌐 DataHub URL";
en["admin.security.dbt"] = "🏗️ dbt manifest";
en["admin.security.on"] = "on";
en["admin.security.off"] = "off";
en["admin.security.loadFailed"] = "Failed to load settings";
en["admin.detail.back"] = "← Back";
en["admin.detail.permissions"] = "Permissions";
en["admin.detail.llm"] = "LLM";
en["admin.detail.db"] = "DB";
en["admin.detail.customLlm"] = "Custom LLM settings";
en["admin.detail.customLlmDesc"] = "Allow this user to set personal LLM parameters";
en["admin.detail.dbConns"] = "DB connections";
en["admin.detail.dbConnsDesc"] = "Allow this user to attach databases";
en["admin.detail.savePermissions"] = "Save permissions";
en["admin.detail.saveLlm"] = "Save LLM";
en["admin.detail.llmHint"] = "LLM settings for this user. Leave fields empty to use global ones.";
en["admin.detail.addConn"] = "Add connection";
en["admin.detail.noConns"] = "No connections";
en["admin.field.name"] = "Name";
en["admin.field.type"] = "DB type";
en["admin.field.host"] = "Host";
en["admin.field.port"] = "Port";
en["admin.field.user"] = "Username";
en["admin.field.password"] = "Password";
en["admin.field.database"] = "Database";
en["admin.field.sqlitePath"] = "DB file path";
en["admin.field.public"] = "Public connection (visible to everyone)";
en["admin.form.creating"] = "Creating...";

/* ── public dashboard page ── */
ru["dash.notFound"] = "Дашборд не найден";
ru["dash.protected"] = "Этот дашборд защищён паролем";
ru["dash.password"] = "Введите пароль";
ru["dash.wrongPassword"] = "Неверный пароль";
ru["dash.login"] = "Войти";
ru["dash.filters"] = "{n} фильтр";
ru["dash.refresh"] = "Обновить";
ru["dash.copyLink"] = "Скопировать ссылку";
ru["dash.footer.create"] = "Создать свой дашборд";
ru["dash.loading"] = "Загрузка...";
ru["dash.createdTitle"] = "Дашборд создан!";
ru["dash.openLink"] = "Открыть дашборд →";
ru["dash.createTitle"] = "Создать публичный дашборд";
ru["dash.createHint"] = "ИИ проанализирует ваши данные и автоматически создаст интерактивный дашборд с KPI-карточками, графиками и селекторами фильтров.";
ru["dash.titlePlaceholder"] = "Продажи Q1 2026";
ru["dash.descPlaceholder"] = "Дашборд по продажам";
ru["dash.passPlaceholder"] = "Оставьте пустым для публичного доступа";
ru["dash.createCta"] = "Создать дашборд";
ru["dash.passLabel"] = "Пароль (необязательно)";

en["dash.notFound"] = "Dashboard not found";
en["dash.protected"] = "This dashboard is password protected";
en["dash.password"] = "Enter the password";
en["dash.wrongPassword"] = "Wrong password";
en["dash.login"] = "Enter";
en["dash.filters"] = "{n} filters";
en["dash.refresh"] = "Refresh";
en["dash.copyLink"] = "Copy link";
en["dash.footer.create"] = "Create your own dashboard";
en["dash.loading"] = "Loading...";
en["dash.createdTitle"] = "Dashboard created!";
en["dash.openLink"] = "Open dashboard →";
en["dash.createTitle"] = "Create public dashboard";
en["dash.createHint"] = "The AI will analyze your data and automatically build an interactive dashboard with KPI cards, charts and filter selectors.";
en["dash.titlePlaceholder"] = "Sales Q1 2026";
en["dash.descPlaceholder"] = "Sales dashboard";
en["dash.passPlaceholder"] = "Leave empty for public access";
en["dash.createCta"] = "Create dashboard";
en["dash.passLabel"] = "Password (optional)";

/* ── comparison / misc ── */
ru["compare.analysisA"] = "Анализ A";
ru["compare.analysisB"] = "Анализ B";
ru["errorBoundary"] = "Ошибка рендеринга";
ru["mcp.noConns"] = "Нет подключений к БД — добавьте их на шаге «Данные» или во вкладке «БД»";
ru["notify.done"] = "Анализ завершён";
ru["api.loginFailed"] = "Ошибка входа";
ru["api.registerFailed"] = "Ошибка регистрации";
ru["api.generationFailed"] = "Ошибка генерации";
ru["api.dashNotFound"] = "Дашборд не найден";
ru["api.wrongPassword"] = "Неверный пароль";
ru["api.queryError"] = "Ошибка запроса";
ru["api.error"] = "Ошибка";
ru["api.dbtUpload"] = "Ошибка загрузки dbt";
ru["api.semanticUpload"] = "Ошибка загрузки semantic models";
ru["api.datahubSync"] = "Ошибка синхронизации DataHub";
ru["api.piiScan"] = "Ошибка сканирования PII";
ru["api.mcpConfig"] = "Ошибка генерации конфига";
ru["dash.all"] = "Все";

en["compare.analysisA"] = "Analysis A";
en["compare.analysisB"] = "Analysis B";
en["errorBoundary"] = "Rendering error";
en["mcp.noConns"] = "No DB connections — add them in the \"Data\" step or in the \"DB\" tab";

/* ── экспорт словарей ── */
export type Lang = "ru" | "en";
export const dictionaries: Record<Lang, Record<string, string>> = { ru, en };
export type Translate = (key: string, params?: Record<string, string | number>) => string;

export function translate(lang: Lang, key: string, params?: Record<string, string | number>): string {
  let value = dictionaries[lang]?.[key] ?? dictionaries.ru[key] ?? key;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      value = value.split(`{${k}}`).join(String(v));
    }
  }
  return value;
}
