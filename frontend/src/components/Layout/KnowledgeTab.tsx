import { useState, useEffect, useCallback } from "react";
import { Search, BookOpen, Tag, Crown, Upload, Cloud, Loader2, Plus, Trash2 } from "lucide-react";
import * as api from "../../api/client";
import { useI18n } from "../../i18n";

export function KnowledgeTab() {
  const { t } = useI18n();
  const [tables, setTables] = useState<api.KBTableMeta[]>([]);
  const [metrics, setMetrics] = useState<api.KBMetric[]>([]);
  const [searchQ, setSearchQ] = useState("");
  const [results, setResults] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [showMetricForm, setShowMetricForm] = useState(false);
  const [metricForm, setMetricForm] = useState({ name: "", formula: "", description: "", owner: "" });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [tbl, met] = await Promise.all([api.listKBTables(), api.listMetrics()]);
      setTables(tbl);
      setMetrics(met);
    } catch {
      /* */
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const handleSearch = async () => {
    if (!searchQ.trim()) { setResults([]); return; }
    try { setResults(await api.searchKnowledge(searchQ)); } catch { /* */ }
  };

  const handleDbtUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy("dbt");
    try {
      const res = await api.uploadDbtManifest(file);
      alert(t("kb.dbtLoaded", { models: res.models ?? 0, sources: res.sources ?? 0, columns: res.columns ?? 0 }));
      load();
    } catch (err) {
      alert((err as Error).message);
    }
    setBusy(null);
    e.target.value = "";
  };

  const handleDataHub = async () => {
    setBusy("datahub");
    try {
      const res = await api.syncDataHub();
      if (res.error) alert(res.error);
      else alert(t("kb.datahubSynced", { n: res.synced ?? 0 }));
      load();
    } catch (err) {
      alert((err as Error).message);
    }
    setBusy(null);
  };

  const handleSaveMetric = async () => {
    if (!metricForm.name) return;
    try {
      await api.upsertMetric(metricForm);
      setMetricForm({ name: "", formula: "", description: "", owner: "" });
      setShowMetricForm(false);
      load();
    } catch (err) {
      alert((err as Error).message);
    }
  };

  const handleDeleteMetric = async (name: string) => {
    if (!confirm(t("kb.deleteMetric", { name }))) return;
    try { await api.deleteMetric(name); setMetrics((p) => p.filter((m) => m.name !== name)); } catch { /* */ }
  };

  return (
    <div className="sidebar-section">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "0 0 8px" }}>
        <h4 style={{ margin: 0 }}><BookOpen size={12} style={{ marginRight: 4, verticalAlign: "middle" }} />{t("kb.title")}</h4>
        <div style={{ display: "flex", gap: 4 }}>
          <label className="admin-add-btn" style={{ marginBottom: 0, padding: "3px 8px", fontSize: 10, cursor: "pointer" }} title={t("kb.dbtTitle")}>
            {busy === "dbt" ? <Loader2 size={11} className="spin" /> : <Upload size={11} />}
            <input type="file" accept=".json" onChange={handleDbtUpload} style={{ display: "none" }} />
          </label>
          <button className="admin-add-btn" style={{ marginBottom: 0, padding: "3px 8px", fontSize: 10 }} onClick={handleDataHub} title={t("kb.datahubTitle")} disabled={busy !== null}>
            {busy === "datahub" ? <Loader2 size={11} className="spin" /> : <Cloud size={11} />}
          </button>
        </div>
      </div>

      <div style={{ display: "flex", gap: 4, marginBottom: 8 }}>
        <input
          className="kb-search"
          style={{ flex: 1 }}
          placeholder={t("kb.search")}
          value={searchQ}
          onChange={(e) => setSearchQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
        <button className="admin-add-btn" style={{ marginBottom: 0, padding: "4px 8px" }} onClick={handleSearch}>
          <Search size={11} />
        </button>
      </div>

      {results.length > 0 && (
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 10, opacity: 0.7, marginBottom: 4 }}>{t("kb.results")}</div>
          {results.map((r, i) => (
            <div key={i} className="table-item">
              <code>{String(r.name ?? r.table_name ?? r.column_name ?? "")}</code>
              <span className="table-cols">{String(r.type ?? "")}</span>
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <p className="no-files">{t("common.loading")}</p>
      ) : (
        <>
          <div style={{ fontSize: 10, opacity: 0.7, margin: "8px 0 4px" }}>{t("kb.tables", { n: tables.length })}</div>
          <div className="table-list">
            {tables.length === 0 && <p className="no-files">{t("kb.noMetadata")}</p>}
            {tables.map((tbl) => (
              <div key={`${tbl.table_name}-${tbl.connection}`} className="table-item" style={{ flexDirection: "column", alignItems: "stretch", padding: "6px 8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <code style={{ fontWeight: 600 }}>{tbl.table_name}</code>
                  <div style={{ display: "flex", gap: 3 }}>
                    {tbl.is_certified ? <Crown size={10} /> : null}
                    {tbl.layer && <Tag size={10} />}
                  </div>
                </div>
                {tbl.description && <div style={{ fontSize: 10, opacity: 0.75, marginTop: 2 }}>{tbl.description}</div>}
                <div style={{ fontSize: 9, opacity: 0.55, marginTop: 2 }}>
                  {tbl.owner && <span>👤 {tbl.owner} · </span>}
                  {tbl.layer && <span>📁 {tbl.layer} · </span>}
                  <span>{tbl.connection || "—"}</span>
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "12px 0 4px" }}>
            <span style={{ fontSize: 10, opacity: 0.7 }}>{t("kb.metrics", { n: metrics.length })}</span>
            <button className="admin-add-btn" style={{ marginBottom: 0, padding: "2px 6px", fontSize: 10 }} onClick={() => setShowMetricForm((v) => !v)}>
              <Plus size={10} />
            </button>
          </div>

          {showMetricForm && (
            <div style={{ border: "1px dashed var(--border-dashed)", borderRadius: 14, padding: 8, marginBottom: 8 }}>
              <input className="kb-search" style={{ width: "100%", marginBottom: 4 }} placeholder={t("kb.metricName")} value={metricForm.name} onChange={(e) => setMetricForm({ ...metricForm, name: e.target.value })} />
              <input className="kb-search" style={{ width: "100%", marginBottom: 4 }} placeholder={t("kb.metricFormula")} value={metricForm.formula} onChange={(e) => setMetricForm({ ...metricForm, formula: e.target.value })} />
              <input className="kb-search" style={{ width: "100%", marginBottom: 4 }} placeholder={t("kb.metricDesc")} value={metricForm.description} onChange={(e) => setMetricForm({ ...metricForm, description: e.target.value })} />
              <div style={{ display: "flex", gap: 4 }}>
                <button className="admin-add-btn" style={{ marginBottom: 0, padding: "3px 8px", fontSize: 10 }} onClick={handleSaveMetric}>{t("common.save")}</button>
                <button className="session-footer-btn ghost" style={{ padding: "3px 8px", fontSize: 10 }} onClick={() => setShowMetricForm(false)}>{t("common.cancel")}</button>
              </div>
            </div>
          )}

          <div className="table-list">
            {metrics.map((m) => (
              <div key={m.name} className="table-item" style={{ flexDirection: "column", alignItems: "stretch", padding: "6px 8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <code style={{ fontWeight: 600 }}>{m.name}</code>
                  <button className="sidebar-file-remove" style={{ opacity: 0.6 }} onClick={() => handleDeleteMetric(m.name)} title={t("common.delete")}><Trash2 size={11} /></button>
                </div>
                {m.description && <div style={{ fontSize: 10, opacity: 0.75, marginTop: 2 }}>{m.description}</div>}
                {m.formula && <div style={{ fontSize: 9, opacity: 0.55, marginTop: 2, fontFamily: "monospace" }}>{m.formula}</div>}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
