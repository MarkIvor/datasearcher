const API_BASE = import.meta.env.VITE_API_URL || "";

export async function uploadFile(file: File): Promise<import("../types").FileInfo> {
  const formData = new FormData();
  formData.append("file", file);
  const resp = await fetch(`${API_BASE}/api/files/upload`, {
    method: "POST",
    body: formData,
    credentials: "include",
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text);
  }
  return resp.json();
}

export async function listFiles(): Promise<{ files: import("../types").FileInfo[] }> {
  const resp = await fetch(`${API_BASE}/api/files/`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to list files");
  return resp.json();
}

export async function deleteFile(fileId: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/files/${fileId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to delete file");
}

export async function previewFile(
  fileId: string,
  rows: number = 50
): Promise<import("../types").FilePreview> {
  const resp = await fetch(
    `${API_BASE}/api/files/${fileId}/preview?rows=${rows}`,
    { credentials: "include" }
  );
  if (!resp.ok) throw new Error("Failed to preview file");
  return resp.json();
}

export async function getLLMSettings(): Promise<import("../types").LLMSettingsResponse> {
  const resp = await fetch(`${API_BASE}/api/settings/`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to get settings");
  return resp.json();
}

export async function updateLLMSettings(
  settings: import("../types").LLMSettings
): Promise<import("../types").ConnectionTestResult> {
  const resp = await fetch(`${API_BASE}/api/settings/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to update settings");
  return resp.json();
}

export async function testLLMConnection(): Promise<import("../types").ConnectionTestResult> {
  const resp = await fetch(`${API_BASE}/api/settings/test`, {
    method: "POST",
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to test connection");
  return resp.json();
}

export function getExportUrl(exportId: string): string {
  return `${API_BASE}/api/chat/export/${exportId}`;
}

export async function* fetchChatStream(
  message: string,
  sessionId?: string,
  signal?: AbortSignal
): AsyncGenerator<import("../types").SSEEvent> {
  const resp = await fetch(`${API_BASE}/api/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
    credentials: "include",
    signal,
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text);
  }

  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      let currentEvent = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          const dataStr = line.slice(6);
          try {
            const data = JSON.parse(dataStr);
            switch (currentEvent) {
              case "token":
                yield { type: "token", content: data.content };
                break;
              case "tool_call":
                yield { type: "tool_call", name: data.name, args: data.args, tool_call_id: data.tool_call_id || "" };
                break;
              case "tool_result":
                yield { type: "tool_result", name: data.name, result: data.result, tool_call_id: data.tool_call_id || "" };
                break;
              case "chart":
                yield { type: "chart", spec: data };
                break;
              case "dashboard":
                yield { type: "dashboard", slug: data.slug, title: data.title, url: data.url, has_password: data.has_password };
                break;
              case "step":
                yield { type: "step", text: data.text };
                break;
              case "export":
                yield { type: "export", export_id: data.export_id, filename: data.filename, rows: data.rows, columns: data.columns };
                break;
              case "error":
                yield { type: "error", error: data.error };
                break;
              case "done":
                yield { type: "done", session_id: data.session_id };
                break;
            }
          } catch {
            // skip malformed JSON
          }
          currentEvent = "";
        }
      }
    }
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === "AbortError") {
      return;
    }
    throw err;
  }
}

// ── Auth API ──────────────────────────────────

export interface AuthUser {
  id: number;
  email: string;
  display_name: string;
  role: string;
  is_active?: boolean;
  created_at?: string;
}

export async function login(email: string, password: string): Promise<{ access_token: string; user: AuthUser }> {
  const resp = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    credentials: "include",
  });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({ detail: "Ошибка входа" }));
    throw new Error(data.detail || "Ошибка входа");
  }
  return resp.json();
}

export async function register(email: string, password: string, display_name: string): Promise<{ access_token: string; user: AuthUser }> {
  const resp = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, display_name }),
    credentials: "include",
  });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({ detail: "Ошибка регистрации" }));
    throw new Error(data.detail || "Ошибка регистрации");
  }
  return resp.json();
}

export async function getMe(): Promise<AuthUser> {
  const resp = await fetch(`${API_BASE}/api/auth/me`, { credentials: "include" });
  if (!resp.ok) return null as unknown as AuthUser;
  return resp.json();
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE}/api/auth/logout`, { method: "POST", credentials: "include" });
}

export async function refreshToken(): Promise<{ access_token: string; user: AuthUser } | null> {
  const resp = await fetch(`${API_BASE}/api/auth/refresh`, { method: "POST", credentials: "include" });
  if (!resp.ok) return null;
  return resp.json();
}

// ── Admin API ─────────────────────────────────

export async function getAdminUsers(): Promise<AuthUser[]> {
  const resp = await fetch(`${API_BASE}/api/admin/users`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to get users");
  return resp.json();
}

export async function updateAdminUser(userId: number, data: Partial<AuthUser> & { password?: string }): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/admin/users/${userId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to update user");
}

export async function deleteAdminUser(userId: number): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/admin/users/${userId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to delete user");
}

export async function getAdminSettings(): Promise<Record<string, string>> {
  const resp = await fetch(`${API_BASE}/api/admin/settings`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to get settings");
  return resp.json();
}

export async function updateAdminSettings(s: Record<string, string>): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/admin/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ settings: s }),
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to update settings");
}

// ── DB Connections API ────────────────────────

export interface DBConnectionInfo {
  id: number;
  name: string;
  db_type: string;
  is_public: boolean;
  is_owner: boolean;
}

export async function listDBConnections(): Promise<DBConnectionInfo[]> {
  const resp = await fetch(`${API_BASE}/api/connections/`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to list connections");
  return resp.json();
}

export async function createDBConnection(data: {
  name: string; db_type: string; host?: string; port?: number;
  database?: string; username?: string; password?: string; is_public?: boolean;
}): Promise<{ id: number; name: string; db_type: string }> {
  const resp = await fetch(`${API_BASE}/api/connections/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to create connection");
  return resp.json();
}

export async function testDBConnection(connId: number): Promise<{ ok: boolean; message: string }> {
  const resp = await fetch(`${API_BASE}/api/connections/${connId}/test`, {
    method: "POST",
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to test connection");
  return resp.json();
}

export async function attachDBConnection(connId: number, mode?: string): Promise<{ ok: boolean; tables_loaded?: number; mode?: string; message?: string; errors?: string[]; files?: { file_id: string; table_name: string; file_type: string; row_count: number; columns: { name: string; type: string }[] }[] }> {
  const qs = mode ? `?mode=${encodeURIComponent(mode)}` : "";
  const resp = await fetch(`${API_BASE}/api/connections/${connId}/attach${qs}`, {
    method: "POST",
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to attach connection");
  return resp.json();
}

export async function deleteDBConnection(connId: number): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/connections/${connId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to delete connection");
}

// ── Admin User Detail API ─────────────────────

export async function getAdminUserLLM(userId: number): Promise<{ llm_url: string; llm_model: string; llm_api_key: string }> {
  const resp = await fetch(`${API_BASE}/api/admin/users/${userId}/llm`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to get user LLM settings");
  return resp.json();
}

export async function setAdminUserLLM(userId: number, data: { llm_url: string; llm_model: string; llm_api_key: string }): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/admin/users/${userId}/llm`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to set user LLM settings");
}

export async function getAdminUserConnections(userId: number): Promise<{ id: number; name: string; db_type: string; is_public: boolean }[]> {
  const resp = await fetch(`${API_BASE}/api/admin/users/${userId}/connections`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to get user connections");
  return resp.json();
}

export async function createAdminUserConnection(userId: number, data: {
  name: string; db_type: string; host?: string; port?: number;
  database?: string; username?: string; password?: string; is_public?: boolean;
}): Promise<{ id: number; name: string; db_type: string }> {
  const resp = await fetch(`${API_BASE}/api/admin/users/${userId}/connections`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to create user connection");
  return resp.json();
}

export async function deleteAdminUserConnection(userId: number, connId: number): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/admin/users/${userId}/connections/${connId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to delete user connection");
}

// ── PDF Export API ────────────────────────────

export async function exportPDF(charts: { title: string; png_base64: string }[]): Promise<Blob> {
  const resp = await fetch(`${API_BASE}/api/chat/export-pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ charts }),
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to export PDF");
  return resp.blob();
}

// ── Dashboard API ────────────────────────────

export interface DashboardCard {
  id: string;
  type: "kpi" | "chart" | "table" | "error";
  title: string;
  columns?: string[];
  rows?: (string | number | null)[][];
  chart_type?: string;
  x?: string;
  y?: string;
  format?: string;
  prefix?: string;
  suffix?: string;
  error?: string;
}

export interface DashboardInfo {
  id: number;
  slug: string;
  title: string;
  description: string;
  has_password: boolean;
  views: number;
  tables_count: number;
  created_at: string;
}

export interface DashboardDetail {
  slug: string;
  title: string;
  description: string;
  has_password: boolean;
  config: {
    title?: string;
    description?: string;
    selectors: { id: string; type: string; column: string; table: string; label: string }[];
    cards: { id: string; type: string; title: string; query: string; chart_type?: string; x?: string; y?: string; format?: string; prefix?: string; suffix?: string }[];
  };
  tables_info: { name: string; row_count: number; columns: { name: string; type: string }[] }[];
  views: number;
  created_at: string;
}

export async function generateDashboard(title?: string, description?: string, password?: string): Promise<{ id: number; slug: string; title: string; url: string; has_password: boolean }> {
  const resp = await fetch(`${API_BASE}/api/dashboards/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: title || "", description: description || "", password: password || "" }),
    credentials: "include",
  });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({ detail: "Ошибка генерации" }));
    throw new Error(data.detail || "Ошибка генерации");
  }
  return resp.json();
}

export async function listDashboards(): Promise<DashboardInfo[]> {
  const resp = await fetch(`${API_BASE}/api/dashboards/`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to list dashboards");
  return resp.json();
}

export async function getDashboard(slug: string): Promise<DashboardDetail> {
  const resp = await fetch(`${API_BASE}/api/dashboards/${slug}`);
  if (!resp.ok) throw new Error("Дашборд не найден");
  return resp.json();
}

export async function authDashboard(slug: string, password: string): Promise<{ token: string }> {
  const resp = await fetch(`${API_BASE}/api/dashboards/${slug}/auth`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!resp.ok) throw new Error("Неверный пароль");
  return resp.json();
}

export async function queryDashboard(slug: string, filters: Record<string, unknown>, token?: string): Promise<{ cards: DashboardCard[] }> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["x-dash-token"] = token;
  const resp = await fetch(`${API_BASE}/api/dashboards/${slug}/query`, {
    method: "POST",
    headers,
    body: JSON.stringify({ filters }),
  });
  if (!resp.ok) throw new Error("Ошибка запроса");
  return resp.json();
}

export async function deleteDashboard(slug: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/dashboards/${slug}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to delete dashboard");
}

// ── Knowledge Base API ───────────────────────

export interface KBTableMeta {
  table_name: string;
  connection: string;
  description: string;
  owner: string;
  layer: string;
  tags: string[];
  is_certified: number;
  source: string;
}

export interface KBColMeta {
  table_name: string;
  column_name: string;
  description: string;
  unit: string;
  pii_type: string;
  is_sensitive: number;
  source: string;
}

export interface KBMetric {
  name: string;
  formula: string;
  description: string;
  owner: string;
}

export async function listKBTables(): Promise<KBTableMeta[]> {
  const resp = await fetch(`${API_BASE}/api/knowledge/tables`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to list KB tables");
  return resp.json();
}

export async function getKBTable(tableName: string): Promise<{ table: KBTableMeta | null; columns: KBColMeta[] }> {
  const resp = await fetch(`${API_BASE}/api/knowledge/tables/${encodeURIComponent(tableName)}`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to get KB table");
  return resp.json();
}

export async function updateKBTable(body: {
  table_name: string; connection?: string; description?: string;
  owner?: string; layer?: string; tags?: string[]; is_certified?: boolean;
}): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/knowledge/tables`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to update KB table");
}

export async function listMetrics(): Promise<KBMetric[]> {
  const resp = await fetch(`${API_BASE}/api/knowledge/metrics`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to list metrics");
  return resp.json();
}

export async function upsertMetric(body: { name: string; formula?: string; description?: string; owner?: string }): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/knowledge/metrics`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to save metric");
}

export async function deleteMetric(name: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/api/knowledge/metrics/${encodeURIComponent(name)}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to delete metric");
}

export async function searchKnowledge(q: string, limit = 10): Promise<Record<string, unknown>[]> {
  const resp = await fetch(`${API_BASE}/api/knowledge/search?q=${encodeURIComponent(q)}&limit=${limit}`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to search KB");
  return resp.json();
}

export async function listExamples(limit = 50): Promise<Record<string, unknown>[]> {
  const resp = await fetch(`${API_BASE}/api/knowledge/examples?limit=${limit}`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to list examples");
  return resp.json();
}

// ── Logs API ─────────────────────────────────

export interface QueryLog {
  id: number; timestamp: string; tool: string; sql: string; table_name: string;
  connection: string; rows_returned: number; duration_ms: number; success: number; error: string; user: string;
}
export interface ErrorLog {
  id: number; timestamp: string; error_type: string; message: string;
  sql: string; connection: string; stack: string; tool: string;
}
export interface AuditLog {
  id: number; timestamp: string; action: string; target: string; details: string;
}

export async function getQueryLogs(limit = 50): Promise<QueryLog[]> {
  const resp = await fetch(`${API_BASE}/api/logs/query?limit=${limit}`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to get query logs");
  return resp.json();
}

export async function getErrorLogs(limit = 50): Promise<ErrorLog[]> {
  const resp = await fetch(`${API_BASE}/api/logs/error?limit=${limit}`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to get error logs");
  return resp.json();
}

export async function getAuditLogs(limit = 50): Promise<AuditLog[]> {
  const resp = await fetch(`${API_BASE}/api/logs/audit?limit=${limit}`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to get audit logs");
  return resp.json();
}

// ── Metadata API (dbt / DataHub / PII) ───────

export async function uploadDbtManifest(file: File): Promise<Record<string, number>> {
  const fd = new FormData();
  fd.append("file", file);
  const resp = await fetch(`${API_BASE}/api/metadata/dbt`, { method: "POST", body: fd, credentials: "include" });
  if (!resp.ok) {
    const d = await resp.json().catch(() => ({ detail: "Ошибка" }));
    throw new Error(d.detail || "Ошибка загрузки dbt");
  }
  return resp.json();
}

export async function uploadDbtSemantic(file: File): Promise<{ success: boolean; metrics_loaded: number }> {
  const fd = new FormData();
  fd.append("file", file);
  const resp = await fetch(`${API_BASE}/api/metadata/dbt/semantic`, { method: "POST", body: fd, credentials: "include" });
  if (!resp.ok) throw new Error("Ошибка загрузки semantic models");
  return resp.json();
}

export async function syncDataHub(limit = 100): Promise<{ success?: boolean; synced?: number; error?: string }> {
  const resp = await fetch(`${API_BASE}/api/metadata/datahub/sync`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ limit }),
    credentials: "include",
  });
  if (!resp.ok) {
    const d = await resp.json().catch(() => ({ detail: "Ошибка" }));
    throw new Error(d.detail || "Ошибка синхронизации DataHub");
  }
  return resp.json();
}

export async function scanTablePII(tableName: string): Promise<{ column: string; pii_type: string }[]> {
  const resp = await fetch(`${API_BASE}/api/metadata/pii/scan/${encodeURIComponent(tableName)}`, {
    method: "POST",
    credentials: "include",
  });
  if (!resp.ok) {
    const d = await resp.json().catch(() => ({ detail: "Ошибка" }));
    throw new Error(d.detail || "Ошибка сканирования PII");
  }
  return resp.json();
}

// ── Connection modes ─────────────────────────

export async function listConnectionModes(): Promise<{ modes: string[]; db_types: string[] }> {
  const resp = await fetch(`${API_BASE}/api/connections/modes`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to get modes");
  return resp.json();
}

export async function buildBILink(body: {
  tool: string; base_url: string; dashboard_id?: string;
  params?: Record<string, string>; time_from?: string; time_to?: string;
}): Promise<{ url: string }> {
  const resp = await fetch(`${API_BASE}/api/metadata/bi-link`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Failed to build BI link");
  return resp.json();
}

export interface EnterpriseSettings {
  read_only: boolean; pii_masking: boolean; pii_scan_rows: number;
  rate_limit_enabled: boolean; rate_limit_sql: number; rate_limit_ml: number;
  default_mode: string; auto_translate: boolean; query_timeout: number;
  log_enabled: boolean; blocked_table_patterns: string;
  example_store_enabled: boolean; semantic_search_max_rows: number;
  datahub_url: string; dbt_manifest_path: string;
}

export async function getEnterpriseSettings(): Promise<EnterpriseSettings> {
  const resp = await fetch(`${API_BASE}/api/admin/enterprise-settings`, { credentials: "include" });
  if (!resp.ok) throw new Error("Failed to get enterprise settings");
  return resp.json();
}
