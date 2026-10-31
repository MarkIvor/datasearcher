import { useState, useEffect } from "react";
import {
  FileSpreadsheet, Trash2, Eye, Clock, GitBranch, Shield, Database,
  LayoutDashboard, ExternalLink, Loader2, Plug, Unplug,
  BookOpen, Link2, Download, Plus, Search,
} from "lucide-react";
import type { FileInfo } from "../../types";
import { ProfileCard } from "./ProfileCard";
import { SchemaDiagram } from "../Layout/SchemaDiagram";
import { KnowledgeTab } from "../Layout/KnowledgeTab";
import { LogsTab } from "../Layout/LogsTab";
import { BILinkModal } from "../Layout/BILinkModal";
import * as api from "../../api/client";
import type { SetupState } from "../../api/client";

type Tab = "files" | "history" | "schema" | "databases" | "dashboards" | "kb" | "logs";

interface Props {
  files: FileInfo[];
  onRemove: (fileId: string) => void;
  onClearChat: () => void;
  onOpenSettings: () => void;
  onPreviewFile: (file: FileInfo) => void;
  onExportPDF: () => void;
  hasMessages: boolean;
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
  setup: SetupState | null;
  onOpenSetup: () => void;
}

const CHIPS: { id: Tab; label: string }[] = [
  { id: "files", label: "Файлы" },
  { id: "history", label: "История" },
  { id: "databases", label: "БД" },
  { id: "dashboards", label: "Дашборды" },
  { id: "kb", label: "База" },
  { id: "logs", label: "Логи" },
];

export function LeftColumn({
  files,
  onRemove,
  onClearChat,
  onOpenSettings,
  onPreviewFile,
  onExportPDF,
  hasMessages,
  queryHistory,
  onHistorySelect,
  onHistoryClear,
  onCompare,
  onLogout,
  onAdmin,
  userName,
  userRole,
  onSendMessage,
  onFilesChanged,
  setup,
  onOpenSetup,
}: Props) {
  const [tab, setTab] = useState<Tab>("files");
  const [dbConnections, setDbConnections] = useState<api.DBConnectionInfo[]>([]);
  const [dashboards, setDashboards] = useState<api.DashboardInfo[]>([]);
  const [attachingId, setAttachingId] = useState<number | null>(null);
  const [attachMode, setAttachMode] = useState("auto");
  const [showBILink, setShowBILink] = useState(false);

  const loadConns = async () => {
    try { setDbConnections(await api.listDBConnections()); } catch { /* */ }
  };

  const loadDashes = async () => {
    try { setDashboards(await api.listDashboards()); } catch { /* */ }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (tab === "databases") loadConns();
    if (tab === "dashboards") loadDashes();
  }, [tab]);

  const handleAttach = async (c: api.DBConnectionInfo) => {
    setAttachingId(c.id);
    try {
      const r = await api.attachDBConnection(c.id, attachMode);
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

  const chips: { id: Tab; label: string }[] = files.length > 0
    ? [{ id: "schema", label: "Схема" }, ...CHIPS]
    : CHIPS;

  return (
    <>
      <div className="bento-col bento-left">
        <ProfileCard
          userName={userName}
          role={userRole === "admin" ? "Administrator" : userRole === "viewer" ? "Viewer" : "Analyst"}
          setup={setup}
          onPlus={onClearChat}
        />

        <section className="session-card">
          <div className="session-head">
            <span className="session-title">Сессии</span>
            <button
              className="session-add"
              onClick={() => onSendMessage?.("Сделай краткий обзор структуры данных и построй дашборд с ключевыми метриками")}
              title="Новый быстрый анализ"
            >
              <Plus size={16} />
            </button>
          </div>

          <div className="session-chips">
            {chips.map((c) => (
              <button
                key={c.id}
                className={`session-chip ${tab === c.id ? "active" : ""}`}
                onClick={() => setTab(c.id)}
              >
                {c.label}
              </button>
            ))}
          </div>

          <div className="session-scroll">
            {tab === "files" && (
              files.length === 0 ? (
                <p className="no-files">Нет загруженных файлов.<br />Перетащите файл в поток анализа.</p>
              ) : (
                <>
                  {files.map((f) => (
                    <div key={f.file_id} className={`session-item ${files.indexOf(f) === 0 ? "active" : ""}`}>
                      <div className="session-item-icon"><FileSpreadsheet size={15} /></div>
                      <div className="session-item-info" onClick={() => onPreviewFile(f)}>
                        <span className="session-item-name">{f.table_name}</span>
                        <span className="session-item-meta">
                          {f.row_count.toLocaleString()} стр · {f.columns.length} кол · {f.file_type.toUpperCase()}
                        </span>
                      </div>
                      <button className="session-item-btn" onClick={() => onPreviewFile(f)} title="Предпросмотр"><Eye size={14} /></button>
                      <button className="session-item-btn" onClick={() => onRemove(f.file_id)} title="Удалить"><Trash2 size={14} /></button>
                    </div>
                  ))}
                  <div className="session-section-title">Колонки</div>
                  <div className="table-list">
                    {files.flatMap((f) =>
                      f.columns.slice(0, 8).map((col, i) => (
                        <div key={`${f.file_id}-${i}`} className="table-item">
                          <code>{col.name}</code>
                          <span className="table-cols">{col.type}</span>
                        </div>
                      ))
                    )}
                  </div>
                </>
              )
            )}

            {tab === "history" && (
              queryHistory.length === 0 ? (
                <p className="no-files">Пока нет запросов</p>
              ) : (
                <>
                  {queryHistory.slice(0, 30).map((h, i) => (
                    <button key={i} className="history-item" onClick={() => onHistorySelect(h.query)}>
                      {h.query}
                    </button>
                  ))}
                  <button className="session-footer-btn ghost" onClick={onHistoryClear}>
                    Очистить историю
                  </button>
                </>
              )
            )}

            {tab === "schema" && files.length > 0 && <SchemaDiagram files={files} />}

            {tab === "databases" && (
              <>
                <div className="session-section-title">
                  Режим: {attachMode}
                </div>
                <div className="session-chips" style={{ marginBottom: 10 }}>
                  {[
                    { id: "auto", label: "auto" },
                    { id: "remote", label: "remote" },
                    { id: "dump", label: "dump" },
                    { id: "federated", label: "federated" },
                  ].map((m) => (
                    <button
                      key={m.id}
                      className={`session-chip ${attachMode === m.id ? "active" : ""}`}
                      onClick={() => setAttachMode(m.id)}
                      title={m.id === "auto" ? "SQL в БД, ML в DuckDB" : m.id === "remote" ? "всё в БД" : m.id === "dump" ? "выгрузить в DuckDB" : "кросс-БД JOIN"}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
                {dbConnections.length === 0 ? (
                  <p className="no-files">Нет подключений</p>
                ) : (
                  dbConnections.map((c) => (
                    <div key={c.id} className="session-item">
                      <div className="session-item-icon"><Database size={15} /></div>
                      <div className="session-item-info">
                        <span className="session-item-name">{c.name}</span>
                        <span className="session-item-meta">{c.db_type}{c.is_public ? " · public" : ""}</span>
                      </div>
                      <button
                        className="session-item-btn"
                        onClick={() => handleAttach(c)}
                        disabled={attachingId !== null}
                        title="Подключить"
                      >
                        {attachingId === c.id ? <Loader2 size={14} className="spin" /> : <Plug size={14} />}
                      </button>
                      <button className="session-item-btn" onClick={() => handleDeleteConn(c)} title="Удалить">
                        <Unplug size={14} />
                      </button>
                    </div>
                  ))
                )}
              </>
            )}

            {tab === "dashboards" && (
              <>
                <div className="session-section-title">Дашборды</div>
                {dashboards.length === 0 ? (
                  <p className="no-files">Нет дашбордов</p>
                ) : (
                  dashboards.map((d) => (
                    <div key={d.id} className="session-item">
                      <div className="session-item-icon"><LayoutDashboard size={15} /></div>
                      <div className="session-item-info">
                        <span className="session-item-name">{d.title}</span>
                        <span className="session-item-meta">
                          {d.tables_count} табл · {d.views} просм.{d.has_password ? " · 🔒" : ""}
                        </span>
                      </div>
                      <a className="session-item-btn" href={`/d/${d.slug}`} target="_blank" rel="noopener" title="Открыть">
                        <ExternalLink size={14} />
                      </a>
                      <button className="session-item-btn" onClick={() => handleDeleteDash(d)} title="Удалить">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))
                )}
              </>
            )}

            {tab === "kb" && <KnowledgeTab />}

            {tab === "logs" && <LogsTab />}
          </div>

          <div className="session-footer">
            {onAdmin && (
              <button className="session-footer-btn accent" onClick={onAdmin}>
                <Shield size={14} /> Админ-панель
              </button>
            )}
            <button className="session-footer-btn" onClick={onOpenSettings}>
              <Search size={14} /> Настройки LLM
            </button>
            <button className="session-footer-btn" onClick={() => setShowBILink(true)}>
              <Link2 size={14} /> BI Link Builder
            </button>
            {hasMessages && onCompare && (
              <button className="session-footer-btn" onClick={onCompare}>
                <GitBranch size={14} /> Сравнить анализы
              </button>
            )}
            {hasMessages && (
              <button className="session-footer-btn" onClick={onExportPDF}>
                <Download size={14} /> Скачать PDF-отчёт
              </button>
            )}
            <button className="session-footer-btn ghost" onClick={onOpenSetup}>
              <Clock size={14} /> Первичная настройка
            </button>
            <button className="session-footer-btn ghost" onClick={onClearChat}>
              <Trash2 size={14} /> Очистить чат
            </button>
            <button className="session-footer-btn ghost" onClick={onLogout}>
              <BookOpen size={14} /> Выйти
            </button>
          </div>
        </section>
      </div>

      {showBILink && <BILinkModal onClose={() => setShowBILink(false)} />}
    </>
  );
}
