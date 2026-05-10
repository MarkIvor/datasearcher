import { useState, useRef, useCallback, useEffect } from "react";
import { FileSpreadsheet, Trash2, Eye, Download, Table2, Hash, Rows3, Sun, Moon, Clock, GitBranch, Shield, Database, Plug, LayoutDashboard, Plus, ExternalLink, Lock, GripVertical, Loader2, Unplug } from "lucide-react";
import type { FileInfo } from "../../types";
import { SchemaDiagram } from "./SchemaDiagram";
import * as api from "../../api/client";

interface Props {
  files: FileInfo[];
  onRemove: (fileId: string) => void;
  onClearChat: () => void;
  onOpenSettings: () => void;
  onPreviewFile: (file: FileInfo) => void;
  onExportPDF: () => void;
  hasMessages: boolean;
  dark: boolean;
  onToggleTheme: () => void;
  queryHistory: { query: string; timestamp: number }[];
  onHistorySelect: (query: string) => void;
  onHistoryClear: () => void;
  onCompare?: () => void;
  onLogout: () => void;
  onAdmin?: () => void;
  userName: string;
  userRole?: string;
  onSendMessage?: (msg: string) => void;
  onFilesChanged?: () => void;
}

const SIDEBAR_MIN = 260;
const SIDEBAR_MAX = 560;
const SIDEBAR_DEFAULT = 320;
const STORAGE_KEY = "ds-sidebar-width";

export function Sidebar({
  files,
  onRemove,
  onClearChat,
  onOpenSettings,
  onPreviewFile,
  onExportPDF,
  hasMessages,
  dark,
  onToggleTheme,
  queryHistory,
  onHistorySelect,
  onHistoryClear,
  onCompare,
  onLogout,
  onAdmin,
  userName,
  userRole: _userRole,
  onSendMessage,
  onFilesChanged,
}: Props) {
  const [tab, setTab] = useState<"files" | "history" | "schema" | "databases" | "dashboards">("files");
  const [dbConnections, setDbConnections] = useState<api.DBConnectionInfo[]>([]);
  const [dashboards, setDashboards] = useState<api.DashboardInfo[]>([]);
  const [attachingId, setAttachingId] = useState<number | null>(null);
  const [width, setWidth] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, Number(saved))) : SIDEBAR_DEFAULT;
  });
  const resizing = useRef(false);
  const startX = useRef(0);
  const startW = useRef(0);

  const loadConns = async () => {
    try { setDbConnections(await api.listDBConnections()); } catch { /* */ }
  };

  const loadDashes = async () => {
    try { setDashboards(await api.listDashboards()); } catch { /* */ }
  };

  const handleAttach = async (c: api.DBConnectionInfo) => {
    setAttachingId(c.id);
    try {
      const r = await api.attachDBConnection(c.id);
      if (r.ok) {
        setTab("files");
        onFilesChanged?.();
      } else {
        alert(r.message || "Ошибка подключения");
      }
    } catch {
      alert("Ошибка подключения к БД");
    }
    setAttachingId(null);
  };

  const handleDeleteConn = async (c: api.DBConnectionInfo) => {
    if (!confirm(`Удалить подключение "${c.name}"?`)) return;
    try {
      await api.deleteDBConnection(c.id);
      setDbConnections((prev) => prev.filter((x) => x.id !== c.id));
    } catch { /* */ }
  };

  const handleDeleteDash = async (d: api.DashboardInfo) => {
    if (!confirm(`Удалить дашборд "${d.title}"?`)) return;
    try {
      await api.deleteDashboard(d.slug);
      setDashboards((prev) => prev.filter((x) => x.id !== d.id));
    } catch { /* */ }
  };

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    resizing.current = true;
    startX.current = e.clientX;
    startW.current = width;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, [width]);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!resizing.current) return;
      const delta = e.clientX - startX.current;
      const next = Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, startW.current + delta));
      setWidth(next);
    };
    const onMouseUp = () => {
      if (resizing.current) {
        resizing.current = false;
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        localStorage.setItem(STORAGE_KEY, String(width));
      }
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [width]);

  const totalRows = files.reduce((sum, f) => sum + f.row_count, 0);
  const totalCols = files.reduce((sum, f) => sum + f.columns.length, 0);

  return (
    <>
      <aside className="sidebar" style={{ width, minWidth: width, maxWidth: width }}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <rect x="2" y="2" width="7" height="7" rx="1.5" fill="white" />
              <rect x="11" y="2" width="7" height="7" rx="1.5" fill="white" opacity="0.6" />
              <rect x="2" y="11" width="7" height="7" rx="1.5" fill="white" opacity="0.6" />
              <rect x="11" y="11" width="7" height="7" rx="1.5" fill="white" opacity="0.3" />
            </svg>
          </div>
          <div className="sidebar-brand">
            <span className="sidebar-brand-name">DataSearcher</span>
            <span className="sidebar-brand-sub">Анализ данных с ИИ</span>
          </div>
          <button className="theme-toggle" onClick={onToggleTheme} title="Переключить тему (Ctrl+D)">
            {dark ? <Sun size={13} /> : <Moon size={13} />}
          </button>
        </div>

        {files.length > 0 && (
          <div className="sidebar-stats">
            <div className="stat-card">
              <Table2 size={14} />
              <div className="stat-card-info">
                <span className="stat-card-value">{files.length}</span>
                <span className="stat-card-label">Таблиц</span>
              </div>
            </div>
            <div className="stat-card">
              <Rows3 size={14} />
              <div className="stat-card-info">
                <span className="stat-card-value">{totalRows.toLocaleString()}</span>
                <span className="stat-card-label">Строк</span>
              </div>
            </div>
            <div className="stat-card">
              <Hash size={14} />
              <div className="stat-card-info">
                <span className="stat-card-value">{totalCols}</span>
                <span className="stat-card-label">Колонок</span>
              </div>
            </div>
          </div>
        )}

        <div className="sidebar-tabs">
          <button className={`sidebar-tab ${tab === "files" ? "active" : ""}`} onClick={() => setTab("files")}>
            Файлы
          </button>
          <button className={`sidebar-tab ${tab === "history" ? "active" : ""}`} onClick={() => setTab("history")}>
            <Clock size={10} style={{ marginRight: 3 }} />История
          </button>
          {files.length > 0 && (
            <button className={`sidebar-tab ${tab === "schema" ? "active" : ""}`} onClick={() => setTab("schema")}>
              <GitBranch size={10} style={{ marginRight: 3 }} />Схема
            </button>
          )}
          <button className={`sidebar-tab ${tab === "databases" ? "active" : ""}`} onClick={() => { setTab("databases"); loadConns(); }}>
            <Database size={10} style={{ marginRight: 3 }} />БД
          </button>
          <button className={`sidebar-tab ${tab === "dashboards" ? "active" : ""}`} onClick={() => { setTab("dashboards"); loadDashes(); }}>
            <LayoutDashboard size={10} style={{ marginRight: 3 }} />Дашборды
          </button>
        </div>

        <div className="sidebar-content">
          {tab === "files" && (
            <div className="sidebar-section">
              {files.length === 0 ? (
                <p className="no-files">Нет загруженных файлов</p>
              ) : (
                <div className="sidebar-files">
                  {files.map((f) => (
                    <div key={f.file_id} className="sidebar-file">
                      <div className="sidebar-file-icon"><FileSpreadsheet size={16} /></div>
                      <div className="sidebar-file-info" onClick={() => onPreviewFile(f)} style={{ cursor: "pointer" }}>
                        <span className="sidebar-file-name">{f.table_name}</span>
                        <span className="sidebar-file-meta">
                          {f.row_count.toLocaleString()} строк &middot; {f.columns.length} колонок &middot; {f.file_type.toUpperCase()}
                        </span>
                      </div>
                      <button className="sidebar-file-action" onClick={() => onPreviewFile(f)} title="Предпросмотр"><Eye size={14} /></button>
                      <button className="sidebar-file-remove" onClick={() => onRemove(f.file_id)} title="Удалить"><Trash2 size={14} /></button>
                    </div>
                  ))}
                </div>
              )}
              <h4 style={{ marginTop: 8 }}>Колонки</h4>
              {files.length > 0 ? (
                <div className="table-list">
                  {files.flatMap((f) =>
                    f.columns.slice(0, 10).map((col, i) => (
                      <div key={`${f.file_id}-${i}`} className="table-item">
                        <code>{col.name}</code>
                        <span className="table-cols">{col.type}</span>
                      </div>
                    ))
                  )}
                  {files.some((f) => f.columns.length > 10) && (
                    <div className="table-item">
                      <span className="table-cols" style={{ fontStyle: "italic" }}>
                        +{files.reduce((s, f) => s + Math.max(0, f.columns.length - 10), 0)} ещё...
                      </span>
                    </div>
                  )}
                </div>
              ) : (
                <p className="no-files">--</p>
              )}
            </div>
          )}

          {tab === "history" && (
            <div className="sidebar-section">
              {queryHistory.length === 0 ? (
                <p className="no-files">Пока нет запросов</p>
              ) : (
                <div className="history-list">
                  {queryHistory.slice(0, 30).map((h, i) => (
                    <button key={i} className="history-item" onClick={() => onHistorySelect(h.query)}>
                      {h.query}
                    </button>
                  ))}
                  <button className="history-clear" onClick={onHistoryClear}>
                    Очистить историю
                  </button>
                </div>
              )}
            </div>
          )}

          {tab === "schema" && files.length > 0 && (
            <div className="sidebar-section">
              <SchemaDiagram files={files} />
            </div>
          )}

          {tab === "databases" && (
            <div className="sidebar-section">
              <h4 style={{ margin: "0 0 8px" }}>Подключения</h4>
              {dbConnections.length === 0 ? (
                <p className="no-files">Нет подключений</p>
              ) : (
                <div className="sidebar-files">
                  {dbConnections.map((c) => (
                    <div key={c.id} className="sidebar-file">
                      <div className="sidebar-file-icon"><Database size={16} /></div>
                      <div className="sidebar-file-info">
                        <span className="sidebar-file-name">{c.name}</span>
                        <span className="sidebar-file-meta">{c.db_type}{c.is_public ? " · public" : ""}</span>
                      </div>
                      <button
                        className={`sidebar-file-action ${attachingId === c.id ? "sidebar-file-action-loading" : ""}`}
                        onClick={() => handleAttach(c)}
                        disabled={attachingId !== null}
                        title="Подключить"
                      >
                        {attachingId === c.id ? <Loader2 size={14} className="spin" /> : <Plug size={14} />}
                      </button>
                      <button className="sidebar-file-remove" onClick={() => handleDeleteConn(c)} title="Удалить подключение">
                        <Unplug size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === "dashboards" && (
            <div className="sidebar-section">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <h4 style={{ margin: 0 }}>Дашборды</h4>
                {onSendMessage && (
                  <button className="admin-add-btn" style={{ marginBottom: 0, padding: "4px 10px", fontSize: 10 }} onClick={() => onSendMessage("Создай публичный дашборд. Используй инструмент create_public_dashboard с названием дашборда.")}>
                    <Plus size={12} /> Новый
                  </button>
                )}
              </div>
              {dashboards.length === 0 ? (
                <p className="no-files">Нет дашбордов</p>
              ) : (
                <div className="sidebar-files">
                  {dashboards.map((d) => (
                    <div key={d.id} className="sidebar-file">
                      <div className="sidebar-file-icon"><LayoutDashboard size={16} /></div>
                      <div className="sidebar-file-info">
                        <span className="sidebar-file-name">{d.title}</span>
                        <span className="sidebar-file-meta">
                          {d.tables_count} табл. · {d.views} просм.
                          {d.has_password && <Lock size={10} style={{ marginLeft: 4, verticalAlign: "middle" }} />}
                        </span>
                      </div>
                      <a className="sidebar-file-action" href={`/d/${d.slug}`} target="_blank" rel="noopener" title="Открыть">
                        <ExternalLink size={14} />
                      </a>
                      <button className="sidebar-file-remove" onClick={() => handleDeleteDash(d)} title="Удалить дашборд">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="sidebar-footer">
          <div className="sidebar-user">{userName}</div>
          {onAdmin && (
            <button className="settings-btn" onClick={onAdmin}>
              <Shield size={13} style={{ marginRight: 4 }} />Админ-панель
            </button>
          )}
          <button className="settings-btn" onClick={onOpenSettings}>
            Настройки LLM
          </button>
          {hasMessages && onCompare && (
            <button className="export-pdf-btn" onClick={onCompare}>
              <GitBranch size={14} />
              Сравнить анализы
            </button>
          )}
          {hasMessages && (
            <button className="export-pdf-btn" onClick={onExportPDF}>
              <Download size={14} />
              Скачать PDF-отчёт
            </button>
          )}
          <button className="clear-chat-btn" onClick={onClearChat}>
            <Trash2 size={14} />
            Очистить чат
          </button>
          <button className="clear-chat-btn" onClick={onLogout}>
            Выйти
          </button>
        </div>
      </aside>
      <div className="sidebar-resize-handle" onMouseDown={onMouseDown}>
        <GripVertical size={14} />
      </div>
    </>
  );
}