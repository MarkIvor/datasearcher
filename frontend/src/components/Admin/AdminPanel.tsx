import { useState, useEffect, useCallback } from "react";
import { X, Shield, Users, Database, Settings, Plus, Trash2, Eye, EyeOff, Plug, ChevronRight } from "lucide-react";
import type { AuthUser } from "../../api/client";
import * as api from "../../api/client";

interface Props {
  onClose: () => void;
}

export function AdminPanel({ onClose }: Props) {
  const [tab, setTab] = useState<"users" | "settings" | "connections">("users");
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [appSettings, setAppSettings] = useState<Record<string, string>>({});
  const [connections, setConnections] = useState<api.DBConnectionInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedUser, setSelectedUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    if (tab === "users") loadUsers();
    if (tab === "settings") loadSettings();
    if (tab === "connections") loadConnections();
  }, [tab]);

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
    if (!confirm("Удалить пользователя?")) return;
    await api.deleteAdminUser(userId);
    loadUsers();
  }, [loadUsers]);

  const handleDeleteConnection = useCallback(async (id: number) => {
    if (!confirm("Удалить подключение?")) return;
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
          <div className="admin-title"><Shield size={18} /> Панель администратора</div>
          <button className="admin-close" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="admin-tabs">
          <button className={`admin-tab ${tab === "users" ? "active" : ""}`} onClick={() => setTab("users")}>
            <Users size={13} /> Пользователи
          </button>
          <button className={`admin-tab ${tab === "settings" ? "active" : ""}`} onClick={() => setTab("settings")}>
            <Settings size={13} /> Настройки
          </button>
          <button className={`admin-tab ${tab === "connections" ? "active" : ""}`} onClick={() => setTab("connections")}>
            <Database size={13} /> Базы данных
          </button>
        </div>

        <div className="admin-body">
          {loading && <div className="admin-loading">Загрузка...</div>}

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
                      title={u.is_active ? "Активен" : "Заблокирован"}
                    >
                      {u.is_active ? <Eye size={13} /> : <EyeOff size={13} />}
                    </button>
                    <button className="admin-delete-btn" onClick={() => handleDeleteUser(u.id)}>
                      <Trash2 size={13} />
                    </button>
                    <button className="admin-detail-btn" onClick={() => setSelectedUser(u)} title="Настройки пользователя">
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
                  <span className="admin-setting-label">Регистрация пользователей</span>
                  <span className="admin-setting-desc">Разрешить новым пользователям регистрироваться</span>
                </div>
                <button
                  className={`admin-toggle ${appSettings.allow_registration === "true" ? "on" : "off"}`}
                  onClick={() => toggleSetting("allow_registration")}
                >
                  {appSettings.allow_registration === "true" ? "Вкл" : "Выкл"}
                </button>
              </div>
              <div className="admin-setting-row">
                <div>
                  <span className="admin-setting-label">Пользовательские LLM-настройки</span>
                  <span className="admin-setting-desc">Разрешить пользователям менять свои LLM-параметры</span>
                </div>
                <button
                  className={`admin-toggle ${appSettings.allow_custom_llm === "true" ? "on" : "off"}`}
                  onClick={() => toggleSetting("allow_custom_llm")}
                >
                  {appSettings.allow_custom_llm === "true" ? "Вкл" : "Выкл"}
                </button>
              </div>
              <div className="admin-setting-row">
                <div>
                  <span className="admin-setting-label">Пользовательские подключения к БД</span>
                  <span className="admin-setting-desc">Разрешить пользователям добавлять свои подключения к БД</span>
                </div>
                <button
                  className={`admin-toggle ${appSettings.allow_user_db_connections === "true" ? "on" : "off"}`}
                  onClick={() => toggleSetting("allow_user_db_connections")}
                >
                  {appSettings.allow_user_db_connections === "true" ? "Вкл" : "Выкл"}
                </button>
              </div>

              <div className="admin-section-title">Глобальные LLM-параметры</div>
              <div className="admin-field">
                <label>LLM URL</label>
                <input
                  type="text"
                  value={appSettings.global_llm_url || ""}
                  onChange={(e) => updateSetting("global_llm_url", e.target.value)}
                  placeholder="http://localhost:11434/v1"
                />
              </div>
              <div className="admin-field">
                <label>LLM Model</label>
                <input
                  type="text"
                  value={appSettings.global_llm_model || ""}
                  onChange={(e) => updateSetting("global_llm_model", e.target.value)}
                  placeholder="qwen2.5:14b"
                />
              </div>
              <div className="admin-field">
                <label>LLM API Key</label>
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
                      if (r.ok) alert(`Подключено! Загружено таблиц: ${r.tables_loaded}`);
                      else alert(r.message);
                    }}>
                      <Plug size={13} /> Подключить
                    </button>
                    <button className="admin-delete-btn" onClick={() => handleDeleteConnection(c.id)}>
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              ))}
              {connections.length === 0 && <div className="admin-empty">Нет подключений к БД</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function UserDetailModal({ user, onBack }: { user: AuthUser; onBack: () => void }) {
  const [section, setSection] = useState<"permissions" | "llm" | "connections">("permissions");
  const [llm, setLlm] = useState({ llm_url: "", llm_model: "", llm_api_key: "" });
  const [userConns, setUserConns] = useState<{ id: number; name: string; db_type: string; is_public: boolean }[]>([]);
  const [canCustomLLM, setCanCustomLLM] = useState((user as any).can_use_custom_llm !== false);
  const [canDBConns, setCanDBConns] = useState((user as any).can_use_db_connections !== false);
  const [saving, setSaving] = useState(false);
  const [addConnOpen, setAddConnOpen] = useState(false);

  useEffect(() => {
    loadUserLLM();
    loadUserConns();
  }, []);

  const loadUserLLM = async () => {
    try { setLlm(await api.getAdminUserLLM(user.id)); } catch { /* ignore */ }
  };

  const loadUserConns = async () => {
    try { setUserConns(await api.getAdminUserConnections(user.id)); } catch { /* ignore */ }
  };

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
    if (!confirm("Удалить подключение?")) return;
    try { await api.deleteAdminUserConnection(user.id, connId); loadUserConns(); } catch { /* ignore */ }
  };

  return (
    <div className="user-detail">
      <div className="user-detail-header">
        <button className="user-detail-back" onClick={onBack}>&larr; Назад</button>
        <div className="user-detail-name">{(user as any).display_name || user.email}</div>
        <div className="user-detail-email">{user.email}</div>
      </div>

      <div className="user-detail-tabs">
        <button className={`admin-tab ${section === "permissions" ? "active" : ""}`} onClick={() => setSection("permissions")}>
          Права
        </button>
        <button className={`admin-tab ${section === "llm" ? "active" : ""}`} onClick={() => setSection("llm")}>
          LLM
        </button>
        <button className={`admin-tab ${section === "connections" ? "active" : ""}`} onClick={() => setSection("connections")}>
          <Database size={12} /> БД
        </button>
      </div>

      <div className="user-detail-body">
        {section === "permissions" && (
          <div className="user-detail-section">
            <div className="admin-setting-row">
              <div>
                <span className="admin-setting-label">Кастомные LLM-настройки</span>
                <span className="admin-setting-desc">Разрешить пользователю свои параметры LLM</span>
              </div>
              <button
                className={`admin-toggle ${canCustomLLM ? "on" : "off"}`}
                onClick={() => setCanCustomLLM(!canCustomLLM)}
              >
                {canCustomLLM ? "Вкл" : "Выкл"}
              </button>
            </div>
            <div className="admin-setting-row">
              <div>
                <span className="admin-setting-label">Подключения к БД</span>
                <span className="admin-setting-desc">Разрешить пользователю подключать базы данных</span>
              </div>
              <button
                className={`admin-toggle ${canDBConns ? "on" : "off"}`}
                onClick={() => setCanDBConns(!canDBConns)}
              >
                {canDBConns ? "Вкл" : "Выкл"}
              </button>
            </div>
            <button className="admin-submit-btn" onClick={savePermissions} disabled={saving} style={{ marginTop: 12 }}>
              {saving ? "Сохранение..." : "Сохранить права"}
            </button>
          </div>
        )}

        {section === "llm" && (
          <div className="user-detail-section">
            <p className="user-detail-hint">Настройки LLM для этого пользователя. Оставьте поля пустыми, чтобы использовались глобальные.</p>
            <div className="admin-field">
              <label>LLM URL</label>
              <input type="text" value={llm.llm_url} onChange={(e) => setLlm({ ...llm, llm_url: e.target.value })} placeholder="http://localhost:11434/v1" />
            </div>
            <div className="admin-field">
              <label>LLM Model</label>
              <input type="text" value={llm.llm_model} onChange={(e) => setLlm({ ...llm, llm_model: e.target.value })} placeholder="qwen2.5:14b" />
            </div>
            <div className="admin-field">
              <label>LLM API Key</label>
              <input type="password" value={llm.llm_api_key} onChange={(e) => setLlm({ ...llm, llm_api_key: e.target.value })} placeholder="sk-..." />
            </div>
            <button className="admin-submit-btn" onClick={saveLLM} disabled={saving} style={{ marginTop: 12 }}>
              {saving ? "Сохранение..." : "Сохранить LLM"}
            </button>
          </div>
        )}

        {section === "connections" && (
          <div className="user-detail-section">
            {!addConnOpen && (
              <button className="admin-add-btn" onClick={() => setAddConnOpen(true)} style={{ marginBottom: 12 }}>
                <Plus size={14} /> Добавить подключение
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
            {userConns.length === 0 && !addConnOpen && <div className="admin-empty">Нет подключений</div>}
          </div>
        )}
      </div>
    </div>
  );
}

function AddUserConnectionForm({ userId, onCreated, onCancel }: { userId: number; onCreated: () => void; onCancel: () => void }) {
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
      alert(err instanceof Error ? err.message : "Ошибка");
    }
    setSubmitting(false);
  };

  return (
    <form className="admin-add-form" onSubmit={handleSubmit}>
      <div className="admin-field">
        <label>Название</label>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} required />
      </div>
      <div className="admin-field">
        <label>Тип БД</label>
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
              <label>Хост</label>
              <input type="text" value={host} onChange={(e) => setHost(e.target.value)} placeholder="localhost" />
            </div>
            <div className="admin-field" style={{ width: 80 }}>
              <label>Порт</label>
              <input type="number" value={port} onChange={(e) => setPort(Number(e.target.value))} />
            </div>
          </div>
          <div className="admin-field">
            <label>Пользователь</label>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="admin-field">
            <label>Пароль</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
        </>
      )}
      <div className="admin-field">
        <label>{dbType === "sqlite" ? "Путь к файлу БД" : "База данных"}</label>
        <input type="text" value={database} onChange={(e) => setDatabase(e.target.value)} required />
      </div>
      <div className="admin-field-check">
        <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} id="user-conn-public" />
        <label htmlFor="user-conn-public">Публичное подключение (доступно всем)</label>
      </div>
      <div className="admin-form-actions">
        <button type="submit" className="admin-submit-btn" disabled={submitting}>{submitting ? "Создание..." : "Создать"}</button>
        <button type="button" className="admin-cancel-btn" onClick={onCancel}>Отмена</button>
      </div>
    </form>
  );
}

function AddConnectionForm({ onCreated }: { onCreated: () => void }) {
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
      alert(err instanceof Error ? err.message : "Ошибка");
    }
  };

  if (!open) {
    return (
      <button className="admin-add-btn" onClick={() => setOpen(true)}>
        <Plus size={14} /> Добавить подключение
      </button>
    );
  }

  return (
    <form className="admin-add-form" onSubmit={handleSubmit}>
      <div className="admin-field">
        <label>Название</label>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} required />
      </div>
      <div className="admin-field">
        <label>Тип БД</label>
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
              <label>Хост</label>
              <input type="text" value={host} onChange={(e) => setHost(e.target.value)} placeholder="localhost" />
            </div>
            <div className="admin-field" style={{ width: 80 }}>
              <label>Порт</label>
              <input type="number" value={port} onChange={(e) => setPort(Number(e.target.value))} />
            </div>
          </div>
          <div className="admin-field">
            <label>Пользователь</label>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="admin-field">
            <label>Пароль</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
        </>
      )}
      <div className="admin-field">
        <label>{dbType === "sqlite" ? "Путь к файлу БД" : "База данных"}</label>
        <input type="text" value={database} onChange={(e) => setDatabase(e.target.value)} required />
      </div>
      <div className="admin-field-check">
        <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} id="is-public" />
        <label htmlFor="is-public">Публичное подключение (доступно всем)</label>
      </div>
      <div className="admin-form-actions">
        <button type="submit" className="admin-submit-btn">Создать</button>
        <button type="button" className="admin-cancel-btn" onClick={() => setOpen(false)}>Отмена</button>
      </div>
    </form>
  );
}
