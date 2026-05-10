import { ChevronDown, ChevronRight, Loader2, CheckCircle, XCircle, Copy } from "lucide-react";
import { useState } from "react";
import type { MessageBlock } from "../../types";

interface Props {
  toolCall: Extract<MessageBlock, { type: "tool_call" }>;
}

const TOOL_ICONS: Record<string, string> = {
  get_schema: "📋", sql_query: "⚡", profile_data: "📊", classify_rows: "🏷️",
  find_duplicates: "🔍", detect_anomalies: "🚨", sample_data: "📝",
  correlation_analysis: "🔗", distribution_analysis: "📈", cross_tab: "⊞",
  pivot_table: "📎", segment_data: "📁", compare_tables: "⇔",
  time_analysis: "📅", data_quality_report: "✅", smart_summary: "💡",
  generate_sql: "🤖", visualize_data: "📊", predict_trend: "🔮",
  cluster_analysis: "🎯", feature_importance: "💪", statistical_test: "🧪",
  auto_insights: "✨", transform_data: "🔄", merge_tables: "🔗",
  export_data: "📥", detect_patterns: "🔎", build_dashboard: "📱",
  data_story: "📖",
};

const TOOL_LABELS: Record<string, string> = {
  get_schema: "Схема", sql_query: "SQL", profile_data: "Профиль",
  classify_rows: "Классификация", find_duplicates: "Дубликаты",
  detect_anomalies: "Аномалии", sample_data: "Выборка",
  correlation_analysis: "Корреляция", distribution_analysis: "Распределение",
  cross_tab: "Кросс-таб", pivot_table: "Сводная", segment_data: "Сегментация",
  compare_tables: "Сравнение", time_analysis: "Временной ряд",
  data_quality_report: "Качество", smart_summary: "Саммари",
  generate_sql: "Генерация SQL", visualize_data: "График",
  predict_trend: "Прогноз", cluster_analysis: "Кластеры",
  feature_importance: "Важность", statistical_test: "Стат. тест",
  auto_insights: "Инсайты", transform_data: "Трансформация",
  merge_tables: "Merge", export_data: "Экспорт",
  detect_patterns: "Паттерны", build_dashboard: "Дашборд",
  data_story: "История",
};

export function ToolCallBadge({ toolCall }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const label = TOOL_LABELS[toolCall.name] || toolCall.name;
  const icon = TOOL_ICONS[toolCall.name] || "🔧";

  const statusIcon =
    toolCall.status === "running" ? (
      <Loader2 size={12} className="spin" />
    ) : toolCall.status === "completed" ? (
      <CheckCircle size={12} className="status-ok" />
    ) : (
      <XCircle size={12} className="status-err" />
    );

  const sqlArg = (toolCall.args.sql || toolCall.args.sql_query) as string | undefined;
  const tableArg = toolCall.args.table_name as string | undefined;

  const handleCopy = () => {
    const text = sqlArg || JSON.stringify(toolCall.args, null, 2);
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className={`tool-call-badge tool-${toolCall.status}`}>
      <div className="tool-call-header" onClick={() => setExpanded(!expanded)}>
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <span className="tool-icon">{icon}</span>
        {statusIcon}
        <span className="tool-label">{label}</span>
        {tableArg && <span className="tool-arg">→ {String(tableArg)}</span>}
        {sqlArg && (
          <span className="tool-arg tool-sql">
            {String(sqlArg).slice(0, 60)}
            {String(sqlArg).length > 60 ? "…" : ""}
          </span>
        )}
        {sqlArg && (
          <button className="tool-copy-btn" onClick={(e) => { e.stopPropagation(); handleCopy(); }}>
            <Copy size={11} />
            {copied && <span className="copied-label">Скопировано</span>}
          </button>
        )}
      </div>
      {expanded && (
        <div className="tool-call-detail">
          <div className="tool-call-section">
            <strong>Аргументы</strong>
            <pre>{JSON.stringify(toolCall.args, null, 2)}</pre>
          </div>
          {toolCall.result && (
            <div className="tool-call-section">
              <strong>Результат</strong>
              <pre>
                {toolCall.result.length > 2000
                  ? toolCall.result.slice(0, 2000) + "…"
                  : toolCall.result}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
