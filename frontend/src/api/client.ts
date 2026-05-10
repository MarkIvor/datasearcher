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

export async function attachDBConnection(connId: number): Promise<{ ok: boolean; tables_loaded?: number; message?: string; files?: { file_id: string; table_name: string; file_type: string; row_count: number; columns: { name: string; type: string }[] }[] }> {
  const resp = await fetch(`${API_BASE}/api/connections/${connId}/attach`, {
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
