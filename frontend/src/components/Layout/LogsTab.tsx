import { useState, useEffect, useCallback } from "react";
import { ScrollText, AlertTriangle, FileClock } from "lucide-react";
import * as api from "../../api/client";

type LogType = "query" | "error" | "audit";

export function LogsTab() {
  const [logType, setLogType] = useState<LogType>("query");
  const [queryLogs, setQueryLogs] = useState<api.QueryLog[]>([]);
  const [errorLogs, setErrorLogs] = useState<api.ErrorLog[]>([]);
  const [auditLogs, setAuditLogs] = useState<api.AuditLog[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (logType === "query") setQueryLogs(await api.getQueryLogs(50));
      else if (logType === "error") setErrorLogs(await api.getErrorLogs(50));
      else setAuditLogs(await api.getAuditLogs(50));
    } catch {
      /* */
    }
    setLoading(false);
  }, [logType]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  return (
    <div className="sidebar-section">
      <h4 style={{ margin: "0 0 8px" }}><ScrollText size={12} style={{ marginRight: 4, verticalAlign: "middle" }} />Логи</h4>

      <div className="sidebar-tabs" style={{ marginBottom: 8 }}>
        <button className={`sidebar-tab ${logType === "query" ? "active" : ""}`} onClick={() => setLogType("query")}>
          <FileClock size={10} style={{ marginRight: 3 }} />Запросы
        </button>
        <button className={`sidebar-tab ${logType === "error" ? "active" : ""}`} onClick={() => setLogType("error")}>
          <AlertTriangle size={10} style={{ marginRight: 3 }} />Ошибки
        </button>
        <button className={`sidebar-tab ${logType === "audit" ? "active" : ""}`} onClick={() => setLogType("audit")}>
          Аудит
        </button>
      </div>

      {loading ? (
        <p className="no-files">Загрузка…</p>
      ) : logType === "query" ? (
        queryLogs.length === 0 ? <p className="no-files">Лог запросов пуст</p> : (
          <div className="table-list">
            {queryLogs.map((l) => (
              <div key={l.id} className="table-item" style={{ flexDirection: "column", alignItems: "stretch", padding: "6px 8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <code style={{ fontSize: 11 }}>{l.tool}</code>
                  <span style={{ fontSize: 9, opacity: 0.6 }}>{l.success ? "✓" : "✗"} {l.duration_ms}ms</span>
                </div>
                <div style={{ fontSize: 9, opacity: 0.55, marginTop: 2 }}>
                  {l.timestamp.slice(11, 19)} · {l.table_name || "—"}{l.connection ? ` · ${l.connection}` : ""}
                </div>
                {l.error && <div style={{ fontSize: 9, color: "var(--error)", fontWeight: 600, marginTop: 2 }}>{l.error.slice(0, 80)}</div>}
              </div>
            ))}
          </div>
        )
      ) : logType === "error" ? (
        errorLogs.length === 0 ? <p className="no-files">Лог ошибок пуст</p> : (
          <div className="table-list">
            {errorLogs.map((l) => (
              <div key={l.id} className="table-item" style={{ flexDirection: "column", alignItems: "stretch", padding: "6px 8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <code style={{ fontSize: 10, color: "var(--error)", fontWeight: 600 }}>{l.error_type || "error"}</code>
                  <span style={{ fontSize: 9, opacity: 0.6 }}>{l.timestamp.slice(11, 19)}</span>
                </div>
                <div style={{ fontSize: 10, opacity: 0.75, marginTop: 2 }}>{l.message.slice(0, 100)}</div>
                {l.tool && <div style={{ fontSize: 9, opacity: 0.55, marginTop: 2 }}>tool: {l.tool}</div>}
              </div>
            ))}
          </div>
        )
      ) : (
        auditLogs.length === 0 ? <p className="no-files">Лог аудита пуст</p> : (
          <div className="table-list">
            {auditLogs.map((l) => (
              <div key={l.id} className="table-item" style={{ flexDirection: "column", alignItems: "stretch", padding: "6px 8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <code style={{ fontSize: 11 }}>{l.action}</code>
                  <span style={{ fontSize: 9, opacity: 0.6 }}>{l.timestamp.slice(11, 19)}</span>
                </div>
                {l.target && <div style={{ fontSize: 9, opacity: 0.55, marginTop: 2 }}>→ {l.target}</div>}
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}