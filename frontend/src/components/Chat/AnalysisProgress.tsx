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

const TOOL_SHORT: Record<string, string> = {
  get_schema: "Схема", sql_query: "SQL", profile_data: "Профиль",
  classify_rows: "Классификация", find_duplicates: "Дубликаты",
  detect_anomalies: "Аномалии", sample_data: "Выборка",
  correlation_analysis: "Корреляция", distribution_analysis: "Распределение",
  cross_tab: "Кросс-таб", pivot_table: "Сводная", segment_data: "Сегментация",
  compare_tables: "Сравнение", time_analysis: "Временной ряд",
  data_quality_report: "Качество", smart_summary: "Саммари",
  generate_sql: "SQL", visualize_data: "График",
  predict_trend: "Прогноз", cluster_analysis: "Кластеры",
  feature_importance: "Важность", statistical_test: "Тест",
  auto_insights: "Инсайты", transform_data: "Трансформация",
  merge_tables: "Merge", export_data: "Экспорт",
  detect_patterns: "Паттерны", build_dashboard: "Дашборд",
  data_story: "История",
};

interface ToolEntry {
  name: string;
  status: "running" | "completed";
}

interface Props {
  tools: ToolEntry[];
  isStreaming?: boolean;
}

function dedupTools(tools: ToolEntry[]): ToolEntry[] {
  const seen = new Set<string>();
  const result: ToolEntry[] = [];
  for (const t of tools) {
    const key = t.name;
    if (seen.has(key)) {
      const existing = result.find((r) => r.name === key);
      if (existing && t.status === "completed") existing.status = "completed";
      continue;
    }
    seen.add(key);
    result.push({ ...t });
  }
  return result;
}

export function AnalysisProgress({ tools }: Props) {
  const unique = dedupTools(tools);
  if (!unique.length) return null;

  const total = unique.length;
  const completed = unique.filter((t) => t.status === "completed").length;
  const running = unique.find((t) => t.status === "running");
  const progress = total > 0 ? (completed / total) * 100 : 0;

  return (
    <div className="analysis-progress">
      <div className="progress-bar-track">
        <div
          className="progress-bar-fill"
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="progress-info">
        <span className="progress-label">
          {running
            ? `${TOOL_ICONS[running.name] || "🔧"} ${TOOL_SHORT[running.name] || running.name}…`
            : `${completed}/${total} шагов`}
        </span>
        <span className="progress-steps">
          {unique.map((t, i) => (
            <span key={i} className={`progress-step ${t.status}`}>
              {TOOL_SHORT[t.name] || t.name}
            </span>
          ))}
        </span>
      </div>
    </div>
  );
}
