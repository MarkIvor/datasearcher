import { useState } from "react";
import { ArrowUpRight, Check } from "lucide-react";
import type { FileInfo } from "../../types";
import type { SetupState } from "../../api/client";

interface Props {
  files: FileInfo[];
  setup: SetupState | null;
  isStreaming: boolean;
  onAction: (query: string) => void;
}

const TEMPLATES = [
  { id: "overview", label: "Обзор данных", query: "Сделай краткий обзор структуры данных: типы колонок, пропуски, уникальные значения" },
  { id: "dashboard", label: "Дашборд", query: "Построй дашборд с ключевыми метриками и визуализациями" },
  { id: "audit", label: "Аудит качества", query: "Проведи аудит качества данных: найди дубликаты, пропуски, аномалии и выбросы" },
  { id: "insights", label: "Инсайты", query: "Найди топ-5 инсайтов в данных автоматически" },
];

export function RightColumn({ files, setup, isStreaming, onAction }: Props) {
  const [selected, setSelected] = useState<string>("overview");
  const active = TEMPLATES.find((t) => t.id === selected) ?? TEMPLATES[0];

  const totalRows = files.reduce((sum, f) => sum + f.row_count, 0);
  const totalCols = files.reduce((sum, f) => sum + f.columns.length, 0);
  const modeLabel = setup?.mode === "mcp" ? "MCP" : setup?.mode === "interface" ? "Interface" : "—";
  const llmModel = setup?.llm?.model || "не задана";

  return (
    <div className="bento-col bento-right">
      <section className="summary-card">
        <div className="summary-head">
          <span className="summary-title">Состояние</span>
          <span className={`summary-status-pill ${files.length > 0 ? "active" : ""}`}>
            <span className="pill-dot" />
            {files.length > 0 ? "Active" : "Draft"}
          </span>
        </div>

        <div className="summary-kv">
          <div className="summary-kv-row">
            <span className="summary-key">Тип использования</span>
            <span className="summary-value">{modeLabel}</span>
          </div>
          <div className="summary-kv-row">
            <span className="summary-key">LLM модель</span>
            <span className="summary-value">{llmModel}</span>
          </div>
          <div className="summary-kv-row">
            <span className="summary-key">Таблиц загружено</span>
            <span className="summary-value">{files.length}</span>
          </div>
          <div className="summary-kv-row">
            <span className="summary-key">Стрим</span>
            <span className="summary-value">{isStreaming ? "выполняется" : "ожидание"}</span>
          </div>
        </div>

        <hr className="summary-divider" />
        <div className="summary-metric-label">Строк в анализе</div>
        <div className="summary-metric-value">{totalRows.toLocaleString("ru-RU")}</div>
      </section>

      <div className="info-pills">
        <div className="info-pill">
          <span className="info-pill-value">{totalCols.toLocaleString("ru-RU")}</span>
          <span className="info-pill-label">Колонок</span>
        </div>
        <div className="info-pill">
          <span className="info-pill-value">{setup?.connections_count ?? 0}</span>
          <span className="info-pill-label">Подключений БД</span>
        </div>
      </div>

      <section className="action-card">
        <div className="action-head">
          <span className="action-title">Анализ</span>
        </div>

        {TEMPLATES.map((t) => (
          <button
            key={t.id}
            className={`toggle-pill ${selected === t.id ? "selected" : ""}`}
            onClick={() => setSelected(t.id)}
            disabled={isStreaming}
          >
            <span>{t.label}</span>
            <span className="toggle-check">
              {selected === t.id && <Check size={13} strokeWidth={3} />}
            </span>
          </button>
        ))}

        <div className="sec-chips">
          {setup?.enterprise && (
            <>
              <span className={`sec-chip ${setup.enterprise.read_only ? "on" : ""}`}>
                <span className="chip-dot" /> read-only
              </span>
              <span className={`sec-chip ${setup.enterprise.pii_masking ? "on" : ""}`}>
                <span className="chip-dot" /> PII
              </span>
              <span className={`sec-chip ${setup.enterprise.log_enabled ? "on" : ""}`}>
                <span className="chip-dot" /> логи
              </span>
              <span className={`sec-chip ${setup.enterprise.rate_limit_enabled ? "on" : ""}`}>
                <span className="chip-dot" /> rate limit
              </span>
            </>
          )}
        </div>

        <button
          className="cta-btn"
          onClick={() => onAction(active.query)}
          disabled={files.length === 0 || isStreaming}
          title={files.length === 0 ? "Сначала загрузите данные" : "Запустить анализ"}
        >
          <span>{files.length === 0 ? "Загрузите данные" : "Запустить анализ"}</span>
          <span className="cta-badge"><ArrowUpRight size={15} /></span>
        </button>
      </section>
    </div>
  );
}
