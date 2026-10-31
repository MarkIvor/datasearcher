import { useState, useEffect, useRef } from "react";
import {
  Monitor, Boxes, Database, ArrowRight, ArrowUpRight, Check, Copy,
  Loader2, Wifi, WifiOff, Shield, Download, Terminal, FileCode2,
} from "lucide-react";
import * as api from "../../api/client";
import type { McpConfig, SetupState } from "../../api/client";

interface Props {
  onComplete: (state: SetupState) => void;
}

const STEP_DEFS = [
  { title: "Тип", desc: "MCP или Interface" },
  { title: "Параметры", desc: "LLM API" },
  { title: "Данные", desc: "Файлы и БД" },
  { title: "Готово", desc: "Проверка и запуск" },
];

export function SetupWizard({ onComplete }: Props) {
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
        setTestError(r.error || "Не удалось подключиться");
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
              <div className="setup-side-sub">Первичная настройка</div>
            </div>
          </div>

          <div className="setup-steps">
            {STEP_DEFS.map((s, i) => {
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
              <span>{finished ? "Готово" : `Step ${step} of 4`}</span>
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
                  {step === 1 && "Как вы будете использовать DataSearcher?"}
                  {step === 2 && "Параметры ИИ"}
                  {step === 3 && "Данные для анализа"}
                  {step === 4 && "Проверьте и запустите"}
                </h1>
                <p className="setup-main-sub">
                  {step === 1 && "Выберите тип подключения. Позже его можно изменить в настройках."}
                  {step === 2 && "LLM нужен для генерации SQL и интерпретации вопросов на русском."}
                  {step === 3 && "Загрузите файл или подключите базу данных — можно пропустить и сделать позже."}
                  {step === 4 && "Параметры безопасности читаются из env-конфигурации сервера."}
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
                        <span className="type-card-title">Interface</span>
                        <span className="type-card-desc">Веб-приложение с чатом, графиками и дашбордами. Доступно сразу после настройки.</span>
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
                        <span className="type-card-title">MCP</span>
                        <span className="type-card-desc">Сервер для Claude Desktop, Cursor и VS Code. На финальном шаге мы сгенерируем готовые конфиги.</span>
                      </span>
                      <span className="type-radio" />
                    </button>
                  </>
                )}

                {step === 2 && (
                  <>
                    <div className="setup-field">
                      <label>LLM BASE URL</label>
                      <input
                        className="setup-input"
                        value={llm.url}
                        onChange={(e) => setLlm({ ...llm, url: e.target.value })}
                        placeholder="http://localhost:11434/v1"
                      />
                    </div>
                    <div className="setup-field-row">
                      <div className="setup-field">
                        <label>МОДЕЛЬ</label>
                        <input
                          className="setup-input"
                          value={llm.model}
                          onChange={(e) => setLlm({ ...llm, model: e.target.value })}
                          placeholder="qwen2.5:14b"
                        />
                      </div>
                      <div className="setup-field">
                        <label>API KEY (НЕОБЯЗАТЕЛЬНО)</label>
                        <input
                          className="setup-input"
                          type="password"
                          value={llm.key}
                          onChange={(e) => setLlm({ ...llm, key: e.target.value })}
                          placeholder={state?.llm?.has_key ? "•••• сохранён" : "sk-..."}
                        />
                      </div>
                    </div>

                    <div className="setup-test-row">
                      <button className="setup-next" style={{ marginTop: 0 }} onClick={handleTestLLM} disabled={!llm.url || testStatus === "testing"}>
                        {testStatus === "testing" ? <Loader2 size={14} className="spin" /> : testStatus === "ok" ? <Wifi size={14} /> : testStatus === "fail" ? <WifiOff size={14} /> : <Wifi size={14} />}
                        Проверить
                      </button>
                      {testStatus === "ok" && <span className="test-status ok">Подключено</span>}
                      {testStatus === "fail" && <span className="test-status fail">{testError || "Ошибка"}</span>}
                    </div>
                    <span className="setup-hint">
                      OpenAI-совместимый API: Ollama, vLLM, OpenAI, agentplatform. Проверка не обязательна — можно продолжить и настроить позже.
                    </span>
                  </>
                )}

                {step === 3 && <DataStep />}

                {step === 4 && (
                  <>
                    <div className="setup-scope-row">
                      <span className="setup-scope-title">Сводка</span>
                    </div>
                    <div className="summary-kv" style={{ background: "var(--surface-idle)", borderRadius: 16, padding: 14 }}>
                      <div className="summary-kv-row" style={{ fontSize: 13 }}>
                        <span style={{ color: "var(--text-muted-light)", fontWeight: 500 }}>Тип</span>
                        <span style={{ fontWeight: 600 }}>{mode === "mcp" ? "MCP" : "Interface"}</span>
                      </div>
                      <div className="summary-kv-row" style={{ fontSize: 13 }}>
                        <span style={{ color: "var(--text-muted-light)", fontWeight: 500 }}>LLM</span>
                        <span style={{ fontWeight: 600 }}>{llm.model || llm.url || "—"}</span>
                      </div>
                    </div>

                    <div className="setup-scope-row">
                      <span className="setup-scope-title">Кому применить настройки</span>
                      {state?.is_admin ? (
                        <>
                          <button
                            className={`toggle-pill ${(state.scope ?? "user") === "global" ? "selected" : ""}`}
                            onClick={() => persist({ scope: "global" })}
                          >
                            <span>Для всех пользователей</span>
                            <span className="toggle-check">{(state.scope ?? "user") === "global" && <Check size={13} strokeWidth={3} />}</span>
                          </button>
                          <button
                            className={`toggle-pill ${state.scope !== "global" ? "selected" : ""}`}
                            onClick={() => persist({ scope: "user" })}
                          >
                            <span>Только для меня</span>
                            <span className="toggle-check">{state.scope !== "global" && <Check size={13} strokeWidth={3} />}</span>
                          </button>
                        </>
                      ) : (
                        <span className="setup-hint">Настройки будут применены к вашему аккаунту.</span>
                      )}
                    </div>

                    <div className="sec-chips">
                      {state?.enterprise && (
                        <>
                          <span className={`sec-chip ${state.enterprise.read_only ? "on" : ""}`}>
                            <span className="chip-dot" /> read-only guard
                          </span>
                          <span className={`sec-chip ${state.enterprise.pii_masking ? "on" : ""}`}>
                            <span className="chip-dot" /> PII-маскирование
                          </span>
                          <span className={`sec-chip ${state.enterprise.log_enabled ? "on" : ""}`}>
                            <span className="chip-dot" /> аудит-логи
                          </span>
                          <span className={`sec-chip ${state.enterprise.rate_limit_enabled ? "on" : ""}`}>
                            <span className="chip-dot" /> rate limit
                          </span>
                        </>
                      )}
                    </div>
                    <span className="setup-hint">
                      <Shield size={11} style={{ verticalAlign: "-1px", marginRight: 4 }} />
                      Enterprise-тумблеры управляются переменными окружения (.env) и перечитываются при рестарте сервера.
                    </span>
                  </>
                )}
              </div>

              <div className="setup-nav">
                <button className="setup-back" onClick={() => goto(Math.max(1, step - 1))} style={{ visibility: step === 1 ? "hidden" : "visible" }}>
                  Назад
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
                    Далее <ArrowRight size={15} />
                  </button>
                ) : (
                  <button className="setup-next" onClick={handleFinish} disabled={saving || !mode}>
                    {saving ? <Loader2 size={14} className="spin" /> : <Check size={15} />}
                    {mode === "mcp" ? "Сгенерировать конфиг" : "Confirm"}
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
      setMsg(`Файл «${file.name}» загружен`);
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Ошибка загрузки");
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
      setMsg(`Подключение «${name}» создано`);
      setName(""); setHost(""); setDatabase(""); setUsername(""); setPassword("");
      loadConns();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Ошибка подключения");
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
          <span className="upload-pill-title">Загрузить файл</span>
          <span className="upload-pill-hint">.xlsx, .csv, .parquet — до 100 МБ</span>
        </span>
        <input ref={fileRef} type="file" accept=".xlsx,.xls,.csv,.parquet" onChange={handleFile} hidden />
      </div>

      <form className="db-connect-form" onSubmit={handleAddConn}>
        <div className="db-form-title"><Database size={15} /> Подключение к БД</div>
        <div className="db-form-row">
          <div className="db-form-field">
            <label>Название</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="Моя БД" />
          </div>
          <div className="db-form-field" style={{ maxWidth: 140 }}>
            <label>Тип</label>
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
              <label>Хост</label>
              <input value={host} onChange={(e) => setHost(e.target.value)} placeholder="localhost" />
            </div>
            <div className="db-form-field" style={{ maxWidth: 90 }}>
              <label>Порт</label>
              <input type="number" value={port} onChange={(e) => setPort(Number(e.target.value))} />
            </div>
          </div>
        )}
        {dbType !== "sqlite" && (
          <div className="db-form-row">
            <div className="db-form-field">
              <label>Пользователь</label>
              <input value={username} onChange={(e) => setUsername(e.target.value)} />
            </div>
            <div className="db-form-field">
              <label>Пароль</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
          </div>
        )}
        <div className="db-form-field">
          <label>{dbType === "sqlite" ? "Путь к файлу" : "База данных"}</label>
          <input value={database} onChange={(e) => setDatabase(e.target.value)} required placeholder={dbType === "sqlite" ? "/path/to/db.sqlite" : "mydb"} />
        </div>
        <button className="db-form-submit" type="submit" disabled={submitting}>
          {submitting ? "Создание..." : "Создать подключение"}
        </button>
      </form>

      {connections.length > 0 && (
        <>
          <span className="setup-hint">Созданные подключения:</span>
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
            {copied ? <Check size={12} /> : <Copy size={12} />} {copied ? "Скопировано" : "Копировать"}
          </button>
          <button className="config-btn" onClick={download}>
            <Download size={12} /> Скачать
          </button>
        </span>
      </div>
      <pre className="config-code">{content}</pre>
    </div>
  );
}

function FinishScreen({ mode, mcpConfig, onEnter }: { mode: "interface" | "mcp" | null; mcpConfig: McpConfig | null; onEnter: () => void }) {
  if (mode === "mcp") {
    return (
      <>
        <div className="setup-main-head">
          <h1 className="setup-main-title">Конфигурации MCP готовы</h1>
          <p className="setup-main-sub">
            {mcpConfig
              ? `Сгенерировано из ваших подключений (${mcpConfig.connections.length}). Скопируйте конфиги и подключите DataSearcher к своему ИИ-клиенту.`
              : "Сохраните параметры — конфиг можно сгенерировать позже из вкладки «БД»."}
          </p>
        </div>

        <div className="setup-body">
          {mcpConfig ? (
            <>
              <div className="config-warn">
                <Shield size={14} />
                Конфиг содержит пароли подключений — храните файл в безопасном месте.
              </div>
              <div className="mcp-config-list">
                {mcpConfig.connections_yaml && (
                  <ConfigBlock title="connections.yaml" icon={<FileCode2 size={14} />} content={mcpConfig.connections_yaml} filename="connections.yaml" />
                )}
                <ConfigBlock title="Claude Desktop — claude_desktop_config.json" icon={<Terminal size={14} />} content={mcpConfig.claude_json} filename="claude_datasearcher.json" />
                <ConfigBlock title="Cursor — .cursor/mcp.json" icon={<Terminal size={14} />} content={mcpConfig.cursor_json} filename="cursor_mcp.json" />
                <ConfigBlock title="HTTP-запуск" icon={<Terminal size={14} />} content={mcpConfig.http_command} filename="datasearcher_http.txt" />
                {mcpConfig.env_block && (
                  <ConfigBlock title=".env (LLM)" icon={<FileCode2 size={14} />} content={mcpConfig.env_block} filename="datasearcher_mcp.env" />
                )}
              </div>
            </>
          ) : (
            <span className="setup-hint">
              Подключения не найдены. Добавьте их во вкладке «БД» и повторите генерацию через «Первичная настройка» в левой колонке.
            </span>
          )}

          <button className="cta-btn" onClick={onEnter}>
            <span>Перейти в DataSearcher</span>
            <span className="cta-badge"><ArrowUpRight size={15} /></span>
          </button>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="setup-main-head">
        <h1 className="setup-main-title">Всё готово</h1>
        <p className="setup-main-sub">Настройка сохранена. Загрузите данные и задайте первый вопрос.</p>
      </div>
      <div className="setup-body">
        <button className="cta-btn" onClick={onEnter}>
          <span>Начать анализ</span>
          <span className="cta-badge"><ArrowUpRight size={15} /></span>
        </button>
      </div>
    </>
  );
}
