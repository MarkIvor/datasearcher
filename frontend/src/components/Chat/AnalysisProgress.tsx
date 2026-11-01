import { useI18n } from "../../i18n";

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
  data_story: "📖", create_public_dashboard: "🌐",
  query_explain: "🔍", attach_database: "🔌", refresh_schema: "🔄",
  test_connection: "✅", load_file: "📂", scan_pii: "🔒",
  get_logs: "📜", add_example: "⭐", search_knowledge: "📚",
  load_dbt: "🏗️", sync_datahub: "🌐", list_metrics: "📐",
  update_metadata: "📝", build_bi_link: "🔗", export_xlsx: "📊",
  semantic_search: "🧬",
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
  const { t } = useI18n();
  const unique = dedupTools(tools);
  if (!unique.length) return null;

  const total = unique.length;
  const completed = unique.filter((t2) => t2.status === "completed").length;
  const running = unique.find((t2) => t2.status === "running");

  return (
    <div className="analysis-progress">
      <div className="seg-track">
        {unique.map((t2, i) => (
          <span key={i} className={`seg-segment ${t2.status === "completed" ? "done" : ""}`} />
        ))}
      </div>
      <div className="progress-info">
        <span className="progress-label">
          {running
            ? `${TOOL_ICONS[running.name] || "🔧"} ${t(`tool.${running.name}`)}…`
            : t("progress.steps", { done: completed, total })}
        </span>
        <div className="progress-steps">
          {unique.map((t2, i) => (
            <span key={i} className={`progress-step ${t2.status === "completed" ? "completed" : ""}`}>
              {t(`tool.${t2.name}`)}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
