export interface FileInfo {
  file_id: string;
  table_name: string;
  file_type: string;
  row_count: number;
  columns: ColumnInfo[];
}

export interface ColumnInfo {
  name: string;
  type: string;
  nullable?: boolean;
}

export type MessageBlock =
  | { type: "text"; content: string }
  | { type: "tool_call"; id: string; name: string; args: Record<string, unknown>; result?: string; status: "running" | "completed" | "error" }
  | { type: "chart"; spec: ChartSpec }
  | { type: "dashboard"; slug: string; title: string; url: string; has_password: boolean }
  | { type: "step"; steps: StepInfo[] }
  | { type: "progress"; tools: Array<{ name: string; status: "running" | "completed" }>; isStreaming?: boolean };

export interface ChartSpec {
  type: "bar" | "line" | "pie" | "scatter" | "area" | "histogram";
  title: string;
  data: Record<string, unknown>[];
  xKey: string;
  yKeys: string[];
  horizontal?: boolean;
  isForecast?: boolean;
  scatterGroup?: string;
}

export interface StepInfo {
  text: string;
  status: "running" | "completed";
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  blocks: MessageBlock[];
  isStreaming?: boolean;
  isStopped?: boolean;
  quickActions?: string[];
}

export type SSEEvent =
  | { type: "token"; content: string }
  | { type: "tool_call"; name: string; args: Record<string, unknown>; tool_call_id: string }
  | { type: "tool_result"; name: string; result: string; tool_call_id: string }
  | { type: "chart"; spec: ChartSpec }
  | { type: "dashboard"; slug: string; title: string; url: string; has_password: boolean }
  | { type: "step"; text: string }
  | { type: "export"; export_id: string; filename: string; rows: string; columns: string }
  | { type: "error"; error: string }
  | { type: "done"; session_id: string };

export interface LLMSettings {
  llm_base_url: string;
  llm_api_key: string;
  llm_model: string;
}

export interface LLMSettingsResponse {
  llm_base_url: string;
  llm_api_key: string;
  llm_model: string;
  llm_connected: boolean;
}

export interface ConnectionTestResult {
  connected: boolean;
  models?: string[];
  error?: string;
}

export interface FilePreview {
  table_name: string;
  columns: string[];
  rows: unknown[][];
  total_rows: number;
}
