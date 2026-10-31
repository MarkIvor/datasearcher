# DataSearcher MCP

MCP-сервер DataSearcher — один из двух режимов использования единого продукта.
Полная документация: [корневой README](../README.md), раздел **«Режим MCP»**.

## Установка

```bash
pip install -e ".[all]"
```

## Запуск

```bash
# stdio (Claude Desktop, Cursor, VS Code)
datasearcher-mcp --config /path/to/connections.yaml

# HTTP (удалённый доступ)
datasearcher-mcp --transport http --host 0.0.0.0 --port 8000 --auth-token secret123
```

## Конфигурация

- `connections.yaml` — подключения к БД (пример: `connections.example.yaml`)
- Переменные окружения с префиксом `DATASEARCHER_MCP_` — см. `env.example`

Готовые конфиги можно сгенерировать в веб-интерфейсе:
**Setup-визард → Тип «MCP»** создаёт `connections.yaml` и JSON для Claude Desktop / Cursor
из подключений, настроенных через UI.
