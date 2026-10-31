FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml LICENSE README.md ./
COPY src ./src
COPY connections.example.yaml ./

# Устанавливаем со всеми драйверами БД
RUN pip install --no-cache-dir ".[all]"

RUN mkdir -p /app/data /app/exports /app/charts /app/dashboards /app/embeddings

ENV DATASEARCHER_MCP_CONNECTIONS_FILE=/app/connections.yaml
ENV DATASEARCHER_MCP_EXPORTS_DIR=/app/exports
ENV DATASEARCHER_MCP_CHARTS_DIR=/app/charts
ENV DATASEARCHER_MCP_DASHBOARDS_DIR=/app/dashboards
ENV DATASEARCHER_MCP_EMBEDDINGS_DIR=/app/embeddings

EXPOSE 8000

# По умолчанию http-транспорт для Docker (stdio требует отдельного процесса)
ENTRYPOINT ["datasearcher-mcp"]
CMD ["--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
