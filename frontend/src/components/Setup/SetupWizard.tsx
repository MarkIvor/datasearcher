import { useState, useEffect, useRef } from "react";
import {
  Monitor, Boxes, Database, ArrowRight, ArrowUpRight, Check, Copy,
  Loader2, Wifi, WifiOff, Shield, Download, Terminal, FileCode2, Languages,
} from "lucide-react";
import * as api from "../../api/client";
import type { McpConfig, SetupState } from "../../api/client";
import { useI18n } from "../../i18n";

interface Props {
  onComplete: (state: SetupState) => void;
}

export function SetupWizard({ onComplete }: Props) {
  const { t, lang, setLang } = useI18n();
  const [state, setState] = useState<SetupState | null>(null);
  const [step, setStep] = useState(1);
  const [mode, setMode] = useState<"interface" | "mcp" | null>(null);
  const [llm, setLlm] = useState({ url: "", model: "", key: "" });
  const [testStatus, setTestStatus] = useState<"idle" | "testing" | "ok" | "fail">("idle");
  const [testError, setTestError] = useState("");
  const [saving, setSaving] = useState(false);
  const [mcpConfig, setMcpConfig] = useState<McpConfig | null>(null);
  const [finished, setFinished] = useState(false);

  useEffect(() => {
    api.getSetup().then((s) => {
      setState(s);
      if (s.mode === "interface" || s.mode === "mcp") setMode(s.mode);
      if (s.llm) {
        setLlm({ url: s.llm.url || "", model: s.llm.model || "", key: "" });
      }
    }).catch(() => {});
  }, []);

  const persist = async (patch: Parameters<typeof api.updateSetup>[0]) => {
    try {
      const s = await api.updateSetup(patch);
      setState(s);
      return s;
    } catch {
      return state;
    }
  };

  const goto = (n: number) => {
    setStep(n);
    persist({ step: n });
  };

  const handleTestLLM = async () => {
    setTestStatus("testing");
    setTestError("");
    try {
      const r = await api.testSetupLLM({ url: llm.url || undefined, key: llm.key || undefined });
      if (r.connected) {
        setTestStatus("ok");
      } else {
        setTestStatus("fail");
        setTestError(r.error || t("modal.testStatus.fail"));
      }
    } catch (e) {
      setTestStatus("fail");
      setTestError(String(e));
    }
  };

  const handleFinish = async () => {
    setSaving(true);
    try {
      await persist({
        llm_url: llm.url || undefined,
        llm_model: llm.model || undefined,
        llm_api_key: llm.key || undefined,
        completed: true,
      });
      if (mode === "mcp") {
        try {
          const cfg = await api.generateMcpConfig();
          setMcpConfig(cfg);
        } catch {
          setMcpConfig(null);
        }
      }
      setFinished(true);
    } finally {
      setSaving(false);
    }
  };

  const handleEnterApp = () => {
    if (state) onComplete(state);
  };

  const pct = Math.round((step / 4) * 100);

  const stepDefs = [
    { title: t("setup.step1"), desc: t("setup.step1desc") },
    { title: t("setup.step2"), desc: t("setup.step2desc") },
    { title: t("setup.step3"), desc: t("setup.step3desc") },
    { title: t("setup.step4"), desc: t("setup.step4desc") },
  ];

  return (
    <div className="setup-shell">
      <div className="setup-grid">
        <aside className="setup-side">
          <div className="setup-side-brand">
            <div className="setup-side-logo">
              <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                <rect x="2" y="2" width="7" height="7" rx="1.5" fill="currentColor" />
                <rect x="11" y="2" width="7" height="7" rx="1.5" fill="currentColor" opacity="0.6" />
                <rect x="2" y="11" width="7" height="7" rx="1.5" fill="currentColor" opacity="0.6" />
                <rect x="11" y="11" width="7" height="7" rx="1.5" fill="currentColor" opacity="0.3" />
              </svg>
            </div>
            <div>
              <div className="setup-side-name">DataSearcher</div>
              <div className="setup-side-sub">{t("setup.sideSub")}</div>
            </div>
            <button className="icon-round" style={{ marginLeft: "auto", width: 28, height: 28 }} onClick={() => setLang(lang === "ru" ? "en" : "ru")} title={t("common.langTitle")}>
              <Languages size={13} />
            </button>
          </div>

          <div className="setup-steps">
            {stepDefs.map((s, i) => {
              const n = i + 1;
              const done = finished || n < step;
              const current = !finished && n === step;
              return (
                <div key={s.title} className={`setup-step-row ${done ? "done" : ""} ${current ? "current" : ""}`}>
                  <span className="setup-step-num">{done ? <Check size={12} strokeWidth={3} /> : n}</span>
                  <span className="setup-step-labels">
                    <span className="setup-step-title">{s.title}</span>
                    <span className="setup-step-desc">{s.desc}</span>
                  </span>
                </div>
              );
            })}
          </div>

          <div className="setup-side-progress">
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${finished ? 100 : pct}%` }} />
            </div>
            <div className="progress-caption">
              <span>{finished ? t("setup.done") : t("setup.step", { n: step, total: 4 })}</span>
              <span>{finished ? 100 : pct}%</span>
            </div>
          </div>
        </aside>

        <main className="setup-main">
          {finished ? (
            <FinishScreen
              mode={mode}
              mcpConfig={mcpConfig}
              onEnter={handleEnterApp}
            />
          ) : (
            <>
              <div className="setup-main-head">
                <h1 className="setup-main-title">
                  {step === 1 && t("setup.step1Title")}
                  {step === 2 && t("setup.step2Title")}
                  {step === 3 && t("setup.step3Title")}
                  {step === 4 && t("setup.step4Title")}
                </h1>
                <p className="setup-main-sub">
                  {step === 1 && t("setup.step1Sub")}
                  {step === 2 && t("setup.step2Sub")}
                  {step === 3 && t("setup.step3Sub")}
                  {step === 4 && t("setup.step4Sub")}
                </p>
              </div>

              <div className="setup-body">
                {step === 1 && (
                  <>
                    <button
                      type="button"
                      className={`type-card ${mode === "interface" ? "selected" : ""}`}
                      onClick={() => { setMode("interface"); persist({ mode: "interface" }); }}
                    >
                      <span className="type-card-icon"><Monitor size={20} /></span>
                      <span className="type-card-info">
                        <span className="type-card-title">{t("setup.typeInterface")}</span>
                        <span className="type-card-desc">{t("setup.typeInterfaceDesc")}</span>
                      </span>
                      <span className="type-radio" />
                    </button>

                    <button
                      type="button"
                      className={`type-card ${mode === "mcp" ? "selected" : ""}`}
                      onClick={() => { setMode("mcp"); persist({ mode: "mcp" }); }}
                    >
                      <span className="type-card-icon"><Boxes size={20} /></span>
                      <span className="type-card-info">
                        <span className="type-card-title">{t("setup.typeMcp")}</span>
                        <span className="type-card-desc">{t("setup.typeMcpDesc")}</span>
                      </span>
                      <span className="type-radio" />
                    </button>
                  </>
                )}

                {step === 2 && (
                  <>
                    <div className="setup-field">
                      <label>{t("setup.baseUrl")}</label>
                      <input
                        className="setup-input"
                        value={llm.url}
                        onChange={(e) => setLlm({ ...llm, url: e.target.value })}
                        placeholder={t("setup.baseUrlPlaceholder")}
                      />
                    </div>
                    <div className="setup-field-row">
                      <div className="setup-field">
                        <label>{t("setup.model")}</label>
                        <input
                          className="setup-input"
                          value={llm.model}
                          onChange={(e) => setLlm({ ...llm, model: e.target.value })}
                          placeholder={t("setup.modelPlaceholder")}
                        />
                      </div>
                      <div className="setup-field">
                        <label>{t("setup.apiKey")}</label>
                        <input
                          className="setup-input"
                          type="password"
                          value={llm.key}
                          onChange={(e) => setLlm({ ...llm, key: e.target.value })}
                          placeholder={state?.llm?.has_key ? t("setup.apiKeySaved") : t("setup.apiKeyPlaceholder")}
                        />
                      </div>
                    </div>

                    <div className="setup-test-row">
                      <button className="setup-next" style={{ marginTop: 0 }} onClick={handleTestLLM} disabled={!llm.url || testStatus === "testing"}>
                        {testStatus === "testing" ? <Loader2 size={14} className="spin" /> : testStatus === "ok" ? <Wifi size={14} /> : testStatus === "fail" ? <WifiOff size={14} /> : <Wifi size={14} />}
                        {t("setup.test")}
                      </button>
                      {testStatus === "ok" && <span className="test-status ok">{t("setup.testConnected")}</span>}
                      {testStatus === "fail" && <span className="test-status fail">{testError || t("modal.testStatus.fail")}</span>}
                    </div>
                    <span className="setup-hint">{t("setup.testHint")}</span>
                  </>
                )}

                {step === 3 && <DataStep />}

                {step === 4 && (
                  <>
                    <div className="setup-scope-row">
                      <span className="setup-scope-title">{t("setup.summary")}</span>
                    </div>
                    <div className="summary-kv" style={{ background: "var(--surface-idle)", borderRadius: 16, padding: 14 }}>
                      <div className="summary-kv-row" style={{ fontSize: 13 }}>
                        <span style={{ color: "var(--text-muted-light)", fontWeight: 500 }}>{t("setup.summaryType")}</span>
                        <span style={{ fontWeight: 600 }}>{mode === "mcp" ? "MCP" : "Interface"}</span>
                      </div>
                      <div className="summary-kv-row" style={{ fontSize: 13 }}>
                        <span style={{ color: "var(--text-muted-light)", fontWeight: 500 }}>{t("setup.summaryLlm")}</span>
                        <span style={{ fontWeight: 600 }}>{llm.model || llm.url || "—"}</span>
                      </div>
                    </div>

                    <div className="setup-scope-row">
                      <span className="setup-scope-title">{t("setup.scopeTitle")}</span>
                      {state?.is_admin ? (
                        <>
                          <button
                            className={`toggle-pill ${(state.scope ?? "user") === "global" ? "selected" : ""}`}
                            onClick={() => persist({ scope: "global" })}
                          >
                            <span>{t("setup.scopeAll")}</span>
                            <span className="toggle-check">{(state.scope ?? "user") === "global" && <Check size={13} strokeWidth={3} />}</span>
                          </button>
                          <button
                            className={`toggle-pill ${state.scope !== "global" ? "selected" : ""}`}
                            onClick={() => persist({ scope: "user" })}
                          >
                            <span>{t("setup.scopeMe")}</span>
                            <span className="toggle-check">{state.scope !== "global" && <Check size={13} strokeWidth={3} />}</span>
                          </button>
                        </>
                      ) : (
                        <span className="setup-hint">{t("setup.scopeHint")}</span>
                      )}
                    </div>

                    <div className="sec-chips">
                      {state?.enterprise && (
                        <>
                          <span className={`sec-chip ${state.enterprise.read_only ? "on" : ""}`}>
                            <span className="chip-dot" /> {t("right.sec.readonly")}
                          </span>
                          <span className={`sec-chip ${state.enterprise.pii_masking ? "on" : ""}`}>
                            <span className="chip-dot" /> {t("right.sec.pii")}
                          </span>
                          <span className={`sec-chip ${state.enterprise.log_enabled ? "on" : ""}`}>
                            <span className="chip-dot" /> {t("right.sec.logs")}
                          </span>
                          <span className={`sec-chip ${state.enterprise.rate_limit_enabled ? "on" : ""}`}>
                            <span className="chip-dot" /> {t("right.sec.ratelimit")}
                          </span>
                        </>
                      )}
                    </div>
                    <span className="setup-hint">
                      <Shield size={11} style={{ verticalAlign: "-1px", marginRight: 4 }} />
                      {t("setup.entHint")}
                    </span>
                  </>
                )}
              </div>

              <div className="setup-nav">
                <button className="setup-back" onClick={() => goto(Math.max(1, step - 1))} style={{ visibility: step === 1 ? "hidden" : "visible" }}>
                  {t("common.back")}
                </button>
                {step < 4 ? (
                  <button
                    className="setup-next"
                    onClick={() => {
                      if (step === 2 && (llm.url || llm.model)) {
                        persist({ llm_url: llm.url, llm_model: llm.model, llm_api_key: llm.key });
                      }
                      goto(step + 1);
                    }}
                    disabled={step === 1 && !mode}
                  >
                    {t("common.next")} <ArrowRight size={15} />
                  </button>
                ) : (
                  <button className="setup-next" onClick={handleFinish} disabled={saving || !mode}>
                    {saving ? <Loader2 size={14} className="spin" /> : <Check size={15} />}
                    {mode === "mcp" ? t("setup.generate") : t("common.confirm")}
                  </button>
                )}
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

/* ── Step 3: данные ─────────────────────────── */

function DataStep() {
  const { t } = useI18n();
  const [connections, setConnections] = useState<api.DBConnectionInfo[]>([]);
  const [name, setName] = useState("");
  const [dbType, setDbType] = useState("postgresql");
  const [host, setHost] = useState("");
  const [port, setPort] = useState(5432);
  const [database, setDatabase] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const loadConns = async () => {
    try { setConnections(await api.listDBConnections()); } catch { /* */ }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadConns();
  }, []);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSubmitting(true);
    setMsg("");
    try {
      await api.uploadFile(file);
      setMsg(t("setup.uploaded", { name: file.name }));
    } catch (err) {
      setMsg(err instanceof Error ? err.message : t("common.error"));
    }
    setSubmitting(false);
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleAddConn = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setMsg("");
    try {
      await api.createDBConnection({ name, db_type: dbType, host, port, database, username, password });
      setMsg(t("setup.connCreated", { name }));
      setName(""); setHost(""); setDatabase(""); setUsername(""); setPassword("");
      loadConns();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : t("chat.dbForm.error"));
    }
    setSubmitting(false);
  };

  return (
    <>
      <div className="upload-pill" onClick={() => fileRef.current?.click()}>
        <span className="upload-pill-icon">
          {submitting ? <Loader2 size={16} className="spin" /> : <Database size={16} />}
        </span>
        <span className="upload-pill-text">
          <span className="upload-pill-title">{t("setup.upload")}</span>
          <span className="upload-pill-hint">{t("chat.uploadHint")}</span>
        </span>
        <input ref={fileRef} type="file" accept=".xlsx,.xls,.csv,.parquet" onChange={handleFile} hidden />
      </div>

      <form className="db-connect-form" onSubmit={handleAddConn}>
        <div className="db-form-title"><Database size={15} /> {t("setup.dbForm.title")}</div>
        <div className="db-form-row">
          <div className="db-form-field">
            <label>{t("chat.dbForm.name")}</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required placeholder={t("chat.dbForm.namePlaceholder")} />
          </div>
          <div className="db-form-field" style={{ maxWidth: 140 }}>
            <label>{t("chat.dbForm.type")}</label>
            <select value={dbType} onChange={(e) => {
              setDbType(e.target.value);
              setPort(e.target.value === "mysql" ? 3306 : e.target.value === "clickhouse" ? 8123 : 5432);
            }}>
              <option value="postgresql">PostgreSQL</option>
              <option value="mysql">MySQL</option>
              <option value="clickhouse">ClickHouse</option>
              <option value="sqlite">SQLite</option>
            </select>
          </div>
        </div>
        {dbType !== "sqlite" && (
          <div className="db-form-row">
            <div className="db-form-field">
              <label>{t("chat.dbForm.host")}</label>
              <input value={host} onChange={(e) => setHost(e.target.value)} placeholder="localhost" />
            </div>
            <div className="db-form-field" style={{ maxWidth: 90 }}>
              <label>{t("chat.dbForm.port")}</label>
              <input type="number" value={port} onChange={(e) => setPort(Number(e.target.value))} />
            </div>
          </div>
        )}
        {dbType !== "sqlite" && (
          <div className="db-form-row">
            <div className="db-form-field">
              <label>{t("chat.dbForm.user")}</label>
              <input value={username} onChange={(e) => setUsername(e.target.value)} />
            </div>
            <div className="db-form-field">
              <label>{t("chat.dbForm.password")}</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
          </div>
        )}
        <div className="db-form-field">
          <label>{dbType === "sqlite" ? t("chat.dbForm.sqlitePath") : t("chat.dbForm.database")}</label>
          <input value={database} onChange={(e) => setDatabase(e.target.value)} required placeholder={dbType === "sqlite" ? t("chat.dbForm.sqlitePlaceholder") : t("chat.dbForm.databasePlaceholder")} />
        </div>
        <button className="db-form-submit" type="submit" disabled={submitting}>
          {submitting ? t("setup.dbForm.creating") : t("setup.dbForm.create")}
        </button>
      </form>

      {connections.length > 0 && (
        <>
          <span className="setup-hint">{t("setup.createdConns")}</span>
          <div className="sec-chips">
            {connections.map((c) => (
              <span key={c.id} className="sec-chip on">
                <span className="chip-dot" /> {c.name} · {c.db_type}
              </span>
            ))}
          </div>
        </>
      )}

      {msg && <span className="setup-hint" style={{ fontWeight: 600 }}>{msg}</span>}
    </>
  );
}

/* ── Finish screen (+ MCP configs) ──────────── */

function ConfigBlock({ title, icon, content, filename }: { title: string; icon: React.ReactNode; content: string; filename: string }) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };

  const download = () => {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const link = document.createElement("a");
    link.download = filename;
    link.href = URL.createObjectURL(blob);
    link.click();
    URL.revokeObjectURL(link.href);
  };

  return (
    <div className="config-block">
      <div className="config-head">
        <span className="config-title">{icon} {title}</span>
        <span className="config-actions">
          <button className={`config-btn ${copied ? "copied" : ""}`} onClick={copy}>
            {copied ? <Check size={12} /> : <Copy size={12} />} {copied ? t("common.copied") : t("common.copy")}
          </button>
          <button className="config-btn" onClick={download}>
            <Download size={12} /> {t("common.download")}
          </button>
        </span>
      </div>
      <pre className="config-code">{content}</pre>
    </div>
  );
}

function FinishScreen({ mode, mcpConfig, onEnter }: { mode: "interface" | "mcp" | null; mcpConfig: McpConfig | null; onEnter: () => void }) {
  const { t } = useI18n();

  if (mode === "mcp") {
    return (
      <>
        <div className="setup-main-head">
          <h1 className="setup-main-title">{t("setup.mcpReadyTitle")}</h1>
          <p className="setup-main-sub">
            {mcpConfig
              ? t("setup.mcpReadySub", { n: mcpConfig.connections.length })
              : t("setup.mcpNoConns")}
          </p>
        </div>

        <div className="setup-body">
          {mcpConfig ? (
            <>
              <div className="config-warn">
                <Shield size={14} />
                {t("setup.configWarn")}
              </div>
              <div className="mcp-config-list">
                {mcpConfig.connections_yaml && (
                  <ConfigBlock title={t("setup.block.yaml")} icon={<FileCode2 size={14} />} content={mcpConfig.connections_yaml} filename="connections.yaml" />
                )}
                <ConfigBlock title={t("setup.block.claude")} icon={<Terminal size={14} />} content={mcpConfig.claude_json} filename="claude_datasearcher.json" />
                <ConfigBlock title={t("setup.block.cursor")} icon={<Terminal size={14} />} content={mcpConfig.cursor_json} filename="cursor_mcp.json" />
                <ConfigBlock title={t("setup.block.http")} icon={<Terminal size={14} />} content={mcpConfig.http_command} filename="datasearcher_http.txt" />
                {mcpConfig.env_block && (
                  <ConfigBlock title={t("setup.block.env")} icon={<FileCode2 size={14} />} content={mcpConfig.env_block} filename="datasearcher_mcp.env" />
                )}
              </div>
            </>
          ) : (
            <span className="setup-hint">{t("setup.mcpNoConnsHint")}</span>
          )}

          <button className="cta-btn" onClick={onEnter}>
            <span>{t("setup.enterApp")}</span>
            <span className="cta-badge"><ArrowUpRight size={15} /></span>
          </button>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="setup-main-head">
        <h1 className="setup-main-title">{t("setup.finishTitle")}</h1>
        <p className="setup-main-sub">{t("setup.finishSub")}</p>
      </div>
      <div className="setup-body">
        <button className="cta-btn" onClick={onEnter}>
          <span>{t("setup.startAnalysis")}</span>
          <span className="cta-badge"><ArrowUpRight size={15} /></span>
        </button>
      </div>
    </>
  );
}
