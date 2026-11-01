import { useState, useEffect, useCallback } from "react";
import { X, Shield, Users, Database, Settings, Plus, Trash2, Eye, EyeOff, Plug, ChevronRight, Lock } from "lucide-react";
import type { AuthUser } from "../../api/client";
import * as api from "../../api/client";
import { useI18n } from "../../i18n";

/* eslint-disable @typescript-eslint/no-explicit-any */

interface Props {
  onClose: () => void;
}

export function AdminPanel({ onClose }: Props) {
  const { t } = useI18n();
  const [tab, setTab] = useState<"users" | "settings" | "connections" | "enterprise">("users");
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [appSettings, setAppSettings] = useState<Record<string, string>>({});
  const [connections, setConnections] = useState<api.DBConnectionInfo[]>([]);
  const [entSettings, setEntSettings] = useState<api.EnterpriseSettings | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedUser, setSelectedUser] = useState<AuthUser | null>(null);

  const loadUsers = async () => {
    setLoading(true);
    try { setUsers(await api.getAdminUsers()); } catch { /* ignore */ }
    setLoading(false);
  };

  const loadSettings = async () => {
    setLoading(true);
    try { setAppSettings(await api.getAdminSettings()); } catch { /* ignore */ }
    setLoading(false);
  };

  const loadConnections = async () => {
    setLoading(true);
    try { setConnections(await api.listDBConnections()); } catch { /* ignore */ }
    setLoading(false);
  };

  const loadEnterprise = async () => {
    setLoading(true);
    try { setEntSettings(await api.getEnterpriseSettings()); } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (tab === "users") loadUsers();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (tab === "settings") loadSettings();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (tab === "connections") loadConnections();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (tab === "enterprise") loadEnterprise();
  }, [tab]);

  const toggleSetting = useCallback(async (key: string) => {
    const newVal = appSettings[key] === "true" ? "false" : "true";
    const updated = { ...appSettings, [key]: newVal };
    setAppSettings(updated);
    await api.updateAdminSettings(updated);
  }, [appSettings]);

  const toggleUserActive = useCallback(async (userId: number, isActive: boolean) => {
    await api.updateAdminUser(userId, { is_active: !isActive } as any);
    loadUsers();
  }, [loadUsers]);

  const changeUserRole = useCallback(async (userId: number, role: string) => {
    await api.updateAdminUser(userId, { role } as any);
    loadUsers();
  }, [loadUsers]);

  const handleDeleteUser = useCallback(async (userId: number) => {
    if (!confirm(t("admin.user.deleteConfirm"))) return;
    await api.deleteAdminUser(userId);
    loadUsers();
  }, [loadUsers]);

  const handleDeleteConnection = useCallback(async (id: number) => {
    if (!confirm(t("admin.connections.deleteConfirm"))) return;
    await api.deleteDBConnection(id);
    loadConnections();
  }, [loadConnections]);

  const updateSetting = useCallback(async (key: string, value: string) => {
    const updated = { ...appSettings, [key]: value };
    setAppSettings(updated);
    await api.updateAdminSettings(updated);
  }, [appSettings]);

  return (
    <div className="admin-overlay" onClick={onClose}>
      <div className="admin-panel" onClick={(e) => e.stopPropagation()}>
        <div className="admin-header">
          <div className="admin-title"><Shield size={18} /> {t("admin.title")}</div>
          <button className="admin-close" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="admin-tabs">
          <button className={`admin-tab ${tab === "users" ? "active" : ""}`} onClick={() => setTab("users")}>
            <Users size={13} /> {t("admin.tab.users")}
          </button>
          <button className={`admin-tab ${tab === "settings" ? "active" : ""}`} onClick={() => setTab("settings")}>
            <Settings size={13} /> {t("admin.tab.settings")}
          </button>
          <button className={`admin-tab ${tab === "connections" ? "active" : ""}`} onClick={() => setTab("connections")}>
            <Database size={13} /> {t("admin.tab.connections")}
          </button>
          <button className={`admin-tab ${tab === "enterprise" ? "active" : ""}`} onClick={() => setTab("enterprise")}>
            <Lock size={13} /> {t("admin.tab.security")}
          </button>
        </div>

        <div className="admin-body">
          {loading && <div className="admin-loading">{t("common.loading")}</div>}

          {tab === "users" && !loading && !selectedUser && (
            <div className="admin-users">
              {users.map((u) => (
                <div key={u.id} className="admin-user-row admin-user-row-clickable" onClick={() => setSelectedUser(u)}>
                  <div className="admin-user-info">
                    <span className="admin-user-name">{(u as any).display_name || u.email}</span>
                    <span className="admin-user-email">{u.email}</span>
                    <div className="admin-user-badges">
                      <span className={`admin-badge admin-badge-${u.role}`}>{u.role}</span>
                      {(u as any).has_custom_llm && <span className="admin-badge admin-badge-llm">LLM</span>}
                      {(u as any).can_use_db_connections === false && <span className="admin-badge admin-badge-restricted">No DB</span>}
                    </div>
                  </div>
                  <div className="admin-user-actions" onClick={(e) => e.stopPropagation()}>
                    <select
                      className="admin-role-select"
                      value={u.role}
                      onChange={(e) => changeUserRole(u.id, e.target.value)}
                    >
                      <option value="admin">Admin</option>
                      <option value="analyst">Analyst</option>
                      <option value="viewer">Viewer</option>
                    </select>
                    <button
                      className={`admin-toggle-btn ${u.is_active ? "active" : "inactive"}`}
                      onClick={() => toggleUserActive(u.id, !!u.is_active)}
                      title={u.is_active ? t("admin.user.active") : t("admin.user.blocked")}
                    >
                      {u.is_active ? <Eye size={13} /> : <EyeOff size={13} />}
                    </button>
                    <button className="admin-delete-btn" onClick={() => handleDeleteUser(u.id)}>
                      <Trash2 size={13} />
                    </button>
                    <button className="admin-detail-btn" onClick={() => setSelectedUser(u)} title={t("admin.user.settings")}>
                      <ChevronRight size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === "users" && selectedUser && !loading && (
            <UserDetailModal
              user={selectedUser}
              onBack={() => { setSelectedUser(null); loadUsers(); }}
            />
          )}

          {tab === "settings" && !loading && (
            <div className="admin-settings-grid">
              <div className="admin-setting-row">
                <div>
                  <span className="admin-setting-label">{t("admin.settings.registration")}</span>
                  <span className="admin-setting-desc">{t("admin.settings.registrationDesc")}</span>
                </div>
                <button
                  className={`admin-toggle ${appSettings.allow_registration === "true" ? "on" : "off"}`}
                  onClick={() => toggleSetting("allow_registration")}
                >
                  {appSettings.allow_registration === "true" ? t("admin.on") : t("admin.off")}
                </button>
              </div>
              <div className="admin-setting-row">
                <div>
                  <span className="admin-setting-label">{t("admin.settings.customLlm")}</span>
                  <span className="admin-setting-desc">{t("admin.settings.customLlmDesc")}</span>
                </div>
                <button
                  className={`admin-toggle ${appSettings.allow_custom_llm === "true" ? "on" : "off"}`}
                  onClick={() => toggleSetting("allow_custom_llm")}
                >
                  {appSettings.allow_custom_llm === "true" ? t("admin.on") : t("admin.off")}
                </button>
              </div>
              <div className="admin-setting-row">
                <div>
                  <span className="admin-setting-label">{t("admin.settings.userDb")}</span>
                  <span className="admin-setting-desc">{t("admin.settings.userDbDesc")}</span>
                </div>
                <button
                  className={`admin-toggle ${appSettings.allow_user_db_connections === "true" ? "on" : "off"}`}
                  onClick={() => toggleSetting("allow_user_db_connections")}
                >
                  {appSettings.allow_user_db_connections === "true" ? t("admin.on") : t("admin.off")}
                </button>
              </div>

              <div className="admin-section-title">{t("admin.settings.globalLlm")}</div>
              <div className="admin-field">
                <label>{t("admin.settings.llmUrl")}</label>
                <input
                  type="text"
                  value={appSettings.global_llm_url || ""}
                  onChange={(e) => updateSetting("global_llm_url", e.target.value)}
                  placeholder="http://localhost:11434/v1"
                />
              </div>
              <div className="admin-field">
                <label>{t("admin.settings.llmModel")}</label>
                <input
                  type="text"
                  value={appSettings.global_llm_model || ""}
                  onChange={(e) => updateSetting("global_llm_model", e.target.value)}
                  placeholder="qwen2.5:14b"
                />
              </div>
              <div className="admin-field">
                <label>{t("admin.settings.llmKey")}</label>
                <input
                  type="password"
                  value={appSettings.global_llm_api_key || ""}
                  onChange={(e) => updateSetting("global_llm_api_key", e.target.value)}
                  placeholder="sk-..."
                />
              </div>
            </div>
          )}

          {tab === "connections" && !loading && (
            <div className="admin-connections">
              <AddConnectionForm onCreated={loadConnections} />
              {connections.map((c) => (
                <div key={c.id} className="admin-conn-row">
                  <div className="admin-conn-info">
                    <Database size={14} />
                    <span className="admin-conn-name">{c.name}</span>
                    <span className="admin-conn-type">{c.db_type}</span>
                    {c.is_public && <span className="admin-conn-badge">public</span>}
                  </div>
                  <div className="admin-conn-actions">
                    <button className="admin-conn-attach" onClick={async () => {
                      const r = await api.attachDBConnection(c.id);
                      if (r.ok) alert(t("admin.connections.attached", { n: r.tables_loaded ?? 0 }));
                      else alert(r.message);
                    }}>
                      <Plug size={13} /> {t("admin.connections.attach")}
                    </button>
                    <button className="admin-delete-btn" onClick={() => handleDeleteConnection(c.id)}>
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              ))}
              {connections.length === 0 && <div className="admin-empty">{t("admin.connections.none")}</div>}
            </div>
          )}

          {tab === "enterprise" && !loading && (
            <div className="admin-settings">
              <div className="admin-note" style={{ marginBottom: 12, fontSize: 12, opacity: 0.7 }}>
                {t("admin.security.note")}
              </div>
              {entSettings ? (
                <div className="admin-settings-list">
                  <div className="admin-setting-row"><span>{t("admin.security.readonly")}</span><strong>{entSettings.read_only ? t("admin.security.on") : t("admin.security.off")}</strong></div>
                  <div className="admin-setting-row"><span>{t("admin.security.pii")}</span><strong>{entSettings.pii_masking ? t("admin.security.on") : t("admin.security.off")}</strong></div>
                  <div className="admin-setting-row"><span>{t("admin.security.piiRows")}</span><strong>{entSettings.pii_scan_rows}</strong></div>
                  <div className="admin-setting-row"><span>{t("admin.security.rate")}</span><strong>{entSettings.rate_limit_enabled ? t("admin.security.on") : t("admin.security.off")}</strong></div>
                  <div className="admin-setting-row"><span>{t("admin.security.sqlRate")}</span><strong>{entSettings.rate_limit_sql}</strong></div>
                  <div className="admin-setting-row"><span>{t("admin.security.mlRate")}</span><strong>{entSettings.rate_limit_ml}</strong></div>
                  <div className="admin-setting-row"><span>{t("admin.security.defaultMode")}</span><strong>{entSettings.default_mode}</strong></div>
                  <div className="admin-setting-row"><span>{t("admin.security.translate")}</span><strong>{entSettings.auto_translate ? t("admin.security.on") : t("admin.security.off")}</strong></div>
                  <div className="admin-setting-row"><span>{t("admin.security.timeout")}</span><strong>{entSettings.query_timeout}</strong></div>
                  <div className="admin-setting-row"><span>{t("admin.security.logging")}</span><strong>{entSettings.log_enabled ? t("admin.security.on") : t("admin.security.off")}</strong></div>
                  <div className="admin-setting-row"><span>{t("admin.security.blocked")}</span><strong>{entSettings.blocked_table_patterns}</strong></div>
                  <div className="admin-setting-row"><span>{t("admin.security.exampleStore")}</span><strong>{entSettings.example_store_enabled ? t("admin.security.on") : t("admin.security.off")}</strong></div>
                  <div className="admin-setting-row"><span>{t("admin.security.semantic")}</span><strong>{entSettings.semantic_search_max_rows}</strong></div>
                  <div className="admin-setting-row"><span>{t("admin.security.datahub")}</span><strong>{entSettings.datahub_url || "—"}</strong></div>
                  <div className="admin-setting-row"><span>{t("admin.security.dbt")}</span><strong>{entSettings.dbt_manifest_path || "—"}</strong></div>
                </div>
              ) : (
                <div className="admin-empty">{t("admin.security.loadFailed")}</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function UserDetailModal({ user, onBack }: { user: AuthUser; onBack: () => void }) {
  const { t } = useI18n();
  const [section, setSection] = useState<"permissions" | "llm" | "connections">("permissions");
  const [llm, setLlm] = useState({ llm_url: "", llm_model: "", llm_api_key: "" });
  const [userConns, setUserConns] = useState<{ id: number; name: string; db_type: string; is_public: boolean }[]>([]);
  const [canCustomLLM, setCanCustomLLM] = useState((user as any).can_use_custom_llm !== false);
  const [canDBConns, setCanDBConns] = useState((user as any).can_use_db_connections !== false);
  const [saving, setSaving] = useState(false);
  const [addConnOpen, setAddConnOpen] = useState(false);

  const loadUserLLM = async () => {
    try { setLlm(await api.getAdminUserLLM(user.id)); } catch { /* ignore */ }
  };

  const loadUserConns = async () => {
    try { setUserConns(await api.getAdminUserConnections(user.id)); } catch { /* ignore */ }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadUserLLM();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadUserConns();
  }, []);

  const savePermissions = async () => {
    setSaving(true);
    try {
      await api.updateAdminUser(user.id, { can_use_custom_llm: canCustomLLM, can_use_db_connections: canDBConns } as any);
    } catch { /* ignore */ }
    setSaving(false);
  };

  const saveLLM = async () => {
    setSaving(true);
    try { await api.setAdminUserLLM(user.id, llm); } catch { /* ignore */ }
    setSaving(false);
  };

  const deleteUserConn = async (connId: number) => {
    if (!confirm(t("admin.connections.deleteConfirm"))) return;
    try { await api.deleteAdminUserConnection(user.id, connId); loadUserConns(); } catch { /* ignore */ }
  };

  return (
    <div className="user-detail">
      <div className="user-detail-header">
        <button className="user-detail-back" onClick={onBack}>{t("admin.detail.back")}</button>
        <div className="user-detail-name">{(user as any).display_name || user.email}</div>
        <div className="user-detail-email">{user.email}</div>
      </div>

      <div className="user-detail-tabs">
        <button className={`admin-tab ${section === "permissions" ? "active" : ""}`} onClick={() => setSection("permissions")}>
          {t("admin.detail.permissions")}
        </button>
        <button className={`admin-tab ${section === "llm" ? "active" : ""}`} onClick={() => setSection("llm")}>
          LLM
        </button>
        <button className={`admin-tab ${section === "connections" ? "active" : ""}`} onClick={() => setSection("connections")}>
          <Database size={12} /> {t("admin.detail.db")}
        </button>
      </div>

      <div className="user-detail-body">
        {section === "permissions" && (
          <div className="user-detail-section">
            <div className="admin-setting-row">
              <div>
                <span className="admin-setting-label">{t("admin.detail.customLlm")}</span>
                <span className="admin-setting-desc">{t("admin.detail.customLlmDesc")}</span>
              </div>
              <button
                className={`admin-toggle ${canCustomLLM ? "on" : "off"}`}
                onClick={() => setCanCustomLLM(!canCustomLLM)}
              >
                {canCustomLLM ? t("admin.on") : t("admin.off")}
              </button>
            </div>
            <div className="admin-setting-row">
              <div>
                <span className="admin-setting-label">{t("admin.detail.dbConns")}</span>
                <span className="admin-setting-desc">{t("admin.detail.dbConnsDesc")}</span>
              </div>
              <button
                className={`admin-toggle ${canDBConns ? "on" : "off"}`}
                onClick={() => setCanDBConns(!canDBConns)}
              >
                {canDBConns ? t("admin.on") : t("admin.off")}
              </button>
            </div>
            <button className="admin-submit-btn" onClick={savePermissions} disabled={saving} style={{ marginTop: 12 }}>
              {saving ? t("common.saved") : t("admin.detail.savePermissions")}
            </button>
          </div>
        )}

        {section === "llm" && (
          <div className="user-detail-section">
            <p className="user-detail-hint">{t("admin.detail.llmHint")}</p>
            <div className="admin-field">
              <label>{t("admin.settings.llmUrl")}</label>
              <input type="text" value={llm.llm_url} onChange={(e) => setLlm({ ...llm, llm_url: e.target.value })} placeholder="http://localhost:11434/v1" />
            </div>
            <div className="admin-field">
              <label>{t("admin.settings.llmModel")}</label>
              <input type="text" value={llm.llm_model} onChange={(e) => setLlm({ ...llm, llm_model: e.target.value })} placeholder="qwen2.5:14b" />
            </div>
            <div className="admin-field">
              <label>{t("admin.settings.llmKey")}</label>
              <input type="password" value={llm.llm_api_key} onChange={(e) => setLlm({ ...llm, llm_api_key: e.target.value })} placeholder="sk-..." />
            </div>
            <button className="admin-submit-btn" onClick={saveLLM} disabled={saving} style={{ marginTop: 12 }}>
              {saving ? t("common.saved") : t("admin.detail.saveLlm")}
            </button>
          </div>
        )}

        {section === "connections" && (
          <div className="user-detail-section">
            {!addConnOpen && (
              <button className="admin-add-btn" onClick={() => setAddConnOpen(true)} style={{ marginBottom: 12 }}>
                <Plus size={14} /> {t("admin.connections.add")}
              </button>
            )}
            {addConnOpen && (
              <AddUserConnectionForm
                userId={user.id}
                onCreated={() => { setAddConnOpen(false); loadUserConns(); }}
                onCancel={() => setAddConnOpen(false)}
              />
            )}
            {userConns.map((c) => (
              <div key={c.id} className="admin-conn-row">
                <div className="admin-conn-info">
                  <Database size={14} />
                  <span className="admin-conn-name">{c.name}</span>
                  <span className="admin-conn-type">{c.db_type}</span>
                  {c.is_public && <span className="admin-conn-badge">public</span>}
                </div>
                <button className="admin-delete-btn" onClick={() => deleteUserConn(c.id)}>
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
            {userConns.length === 0 && !addConnOpen && <div className="admin-empty">{t("admin.detail.noConns")}</div>}
          </div>
        )}
      </div>
    </div>
  );
}

function AddUserConnectionForm({ userId, onCreated, onCancel }: { userId: number; onCreated: () => void; onCancel: () => void }) {
  const { t } = useI18n();
  const [name, setName] = useState("");
  const [dbType, setDbType] = useState("postgresql");
  const [host, setHost] = useState("");
  const [port, setPort] = useState(5432);
  const [database, setDatabase] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.createAdminUserConnection(userId, { name, db_type: dbType, host, port, database, username, password, is_public: isPublic });
      onCreated();
    } catch (err) {
      alert(err instanceof Error ? err.message : t("common.error"));
    }
    setSubmitting(false);
  };

  return (
    <form className="admin-add-form" onSubmit={handleSubmit}>
      <div className="admin-field">
        <label>{t("admin.field.name")}</label>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} required />
      </div>
      <div className="admin-field">
        <label>{t("admin.field.type")}</label>
        <select value={dbType} onChange={(e) => { setDbType(e.target.value); setPort(e.target.value === "mysql" ? 3306 : e.target.value === "clickhouse" ? 8123 : 5432); }}>
          <option value="postgresql">PostgreSQL</option>
          <option value="mysql">MySQL</option>
          <option value="clickhouse">ClickHouse</option>
          <option value="sqlite">SQLite</option>
        </select>
      </div>
      {dbType !== "sqlite" && (
        <>
          <div className="admin-field-row">
            <div className="admin-field">
              <label>{t("admin.field.host")}</label>
              <input type="text" value={host} onChange={(e) => setHost(e.target.value)} placeholder="localhost" />
            </div>
            <div className="admin-field" style={{ width: 80 }}>
              <label>{t("admin.field.port")}</label>
              <input type="number" value={port} onChange={(e) => setPort(Number(e.target.value))} />
            </div>
          </div>
          <div className="admin-field">
            <label>{t("admin.field.user")}</label>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="admin-field">
            <label>{t("admin.field.password")}</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
        </>
      )}
      <div className="admin-field">
        <label>{dbType === "sqlite" ? t("admin.field.sqlitePath") : t("admin.field.database")}</label>
        <input type="text" value={database} onChange={(e) => setDatabase(e.target.value)} required />
      </div>
      <div className="admin-field-check">
        <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} id="user-conn-public" />
        <label htmlFor="user-conn-public">{t("admin.field.public")}</label>
      </div>
      <div className="admin-form-actions">
        <button type="submit" className="admin-submit-btn" disabled={submitting}>{submitting ? t("admin.form.creating") : t("common.create")}</button>
        <button type="button" className="admin-cancel-btn" onClick={onCancel}>{t("common.cancel")}</button>
      </div>
    </form>
  );
}

function AddConnectionForm({ onCreated }: { onCreated: () => void }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [dbType, setDbType] = useState("postgresql");
  const [host, setHost] = useState("");
  const [port, setPort] = useState(5432);
  const [database, setDatabase] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isPublic, setIsPublic] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createDBConnection({ name, db_type: dbType, host, port, database, username, password, is_public: isPublic });
      setOpen(false);
      onCreated();
    } catch (err) {
      alert(err instanceof Error ? err.message : t("common.error"));
    }
  };

  if (!open) {
    return (
      <button className="admin-add-btn" onClick={() => setOpen(true)}>
        <Plus size={14} /> {t("admin.connections.add")}
      </button>
    );
  }

  return (
    <form className="admin-add-form" onSubmit={handleSubmit}>
      <div className="admin-field">
        <label>{t("admin.field.name")}</label>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} required />
      </div>
      <div className="admin-field">
        <label>{t("admin.field.type")}</label>
        <select value={dbType} onChange={(e) => { setDbType(e.target.value); setPort(e.target.value === "mysql" ? 3306 : e.target.value === "clickhouse" ? 8123 : 5432); }}>
          <option value="postgresql">PostgreSQL</option>
          <option value="mysql">MySQL</option>
          <option value="clickhouse">ClickHouse</option>
          <option value="sqlite">SQLite</option>
        </select>
      </div>
      {dbType !== "sqlite" && (
        <>
          <div className="admin-field-row">
            <div className="admin-field">
              <label>{t("admin.field.host")}</label>
              <input type="text" value={host} onChange={(e) => setHost(e.target.value)} placeholder="localhost" />
            </div>
            <div className="admin-field" style={{ width: 80 }}>
              <label>{t("admin.field.port")}</label>
              <input type="number" value={port} onChange={(e) => setPort(Number(e.target.value))} />
            </div>
          </div>
          <div className="admin-field">
            <label>{t("admin.field.user")}</label>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="admin-field">
            <label>{t("admin.field.password")}</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
        </>
      )}
      <div className="admin-field">
        <label>{dbType === "sqlite" ? t("admin.field.sqlitePath") : t("admin.field.database")}</label>
        <input type="text" value={database} onChange={(e) => setDatabase(e.target.value)} required />
      </div>
      <div className="admin-field-check">
        <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} id="is-public" />
        <label htmlFor="is-public">{t("admin.field.public")}</label>
      </div>
      <div className="admin-form-actions">
        <button type="submit" className="admin-submit-btn">{t("common.create")}</button>
        <button type="button" className="admin-cancel-btn" onClick={() => setOpen(false)}>{t("common.cancel")}</button>
      </div>
    </form>
  );
}
