import { useRef, useEffect, useState, type DragEvent } from "react";
import type { ChatMessage } from "../../types";
import { MessageBubble } from "./MessageBubble";
import { ArrowUpRight, Database, Loader2, Plus, Sparkles } from "lucide-react";
import * as api from "../../api/client";

interface Props {
  messages: ChatMessage[];
  onAction?: (action: string) => void;
  onFileUpload?: (file: File) => Promise<unknown>;
  uploading?: boolean;
  hasFiles?: boolean;
  onFilesChanged?: () => void;
}

const QUICK_ACTIONS = [
  { title: "Обзор данных", sub: "структура, типы, пропуски", query: "Сделай краткий обзор структуры данных: типы колонок, пропуски, уникальные значения" },
  { title: "Дашборд", sub: "ключевые метрики и графики", query: "Построй дашборд с ключевыми метриками и визуализациями" },
  { title: "Аудит качества", sub: "дубликаты, аномалии", query: "Проведи аудит качества данных: найди дубликаты, пропуски, аномалии и выбросы" },
  { title: "Инсайты", sub: "топ-5 находок автоматически", query: "Найди топ-5 инсайтов в данных автоматически" },
];

export function ChatStream({ messages, onAction, onFileUpload, uploading, hasFiles, onFilesChanged }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleDrop = async (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && onFileUpload) await onFileUpload(file);
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && onFileUpload) await onFileUpload(file);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div
      className="stream"
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={hasFiles ? undefined : handleDrop}
    >
      {messages.length === 0 && (
        <div className="empty-chat">
          <div className="empty-hero notch-cut">
            <div className="empty-hero-badge">
              <Sparkles size={17} />
            </div>
            <h1 className="empty-hero-title">Анализ данных<br />через диалог</h1>
            <p className="empty-hero-sub">
              Загрузите таблицу или подключитесь к БД — задайте вопрос на русском,
              ИИ сам напишет SQL, построит графики и найдёт инсайты.
            </p>
          </div>

          {!hasFiles && (
            <div className="empty-zones">
              <div
                className={`upload-pill ${dragOver ? "drag-over" : ""}`}
                onClick={() => inputRef.current?.click()}
              >
                <span className="upload-pill-icon">
                  {uploading ? <Loader2 size={16} className="spin" /> : <Plus size={16} strokeWidth={2.5} />}
                </span>
                <span className="upload-pill-text">
                  <span className="upload-pill-title">
                    {uploading ? "Загрузка файла..." : "Перетащите файл или нажмите"}
                  </span>
                  <span className="upload-pill-hint">.xlsx, .csv, .parquet — до 100 МБ</span>
                </span>
                <input
                  ref={inputRef}
                  type="file"
                  accept=".xlsx,.xls,.csv,.parquet"
                  onChange={handleFileSelect}
                  hidden
                />
              </div>

              <DBConnectZone onConnected={onFilesChanged} />

              <div className="qa-grid">
                {QUICK_ACTIONS.map((qa) => (
                  <button key={qa.title} className="qa-card" onClick={() => onAction?.(qa.query)}>
                    <span className="qa-badge"><ArrowUpRight size={14} /></span>
                    <span>
                      <span className="qa-text">{qa.title}</span>
                      <span className="qa-sub">{qa.sub}</span>
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} onAction={onAction} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

function DBConnectZone({ onConnected }: { onConnected?: () => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [dbType, setDbType] = useState("postgresql");
  const [host, setHost] = useState("");
  const [port, setPort] = useState(5432);
  const [database, setDatabase] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const resetForm = () => {
    setName(""); setDbType("postgresql"); setHost(""); setPort(5432);
    setDatabase(""); setUsername(""); setPassword(""); setIsPublic(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const conn = await api.createDBConnection({
        name, db_type: dbType, host, port, database, username, password, is_public: isPublic,
      });
      const r = await api.attachDBConnection(conn.id);
      setOpen(false);
      resetForm();
      if (r.ok) {
        onConnected?.();
      } else alert(r.message || "Не удалось подключить");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Ошибка подключения");
    }
    setSubmitting(false);
  };

  if (!open) {
    return (
      <div className="upload-pill" onClick={() => setOpen(true)}>
        <span className="upload-pill-icon"><Database size={16} /></span>
        <span className="upload-pill-text">
          <span className="upload-pill-title">Подключить базу данных</span>
          <span className="upload-pill-hint">PostgreSQL, MySQL, ClickHouse, SQLite</span>
        </span>
      </div>
    );
  }

  return (
    <form className="db-connect-form" onSubmit={handleSubmit}>
      <div className="db-form-title"><Database size={16} /> Подключение к БД</div>
      <div className="db-form-row">
        <div className="db-form-field">
          <label>Название</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} required placeholder="Моя БД" />
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
        <>
          <div className="db-form-row">
            <div className="db-form-field">
              <label>Хост</label>
              <input type="text" value={host} onChange={(e) => setHost(e.target.value)} placeholder="localhost" />
            </div>
            <div className="db-form-field" style={{ maxWidth: 90 }}>
              <label>Порт</label>
              <input type="number" value={port} onChange={(e) => setPort(Number(e.target.value))} />
            </div>
          </div>
          <div className="db-form-row">
            <div className="db-form-field">
              <label>Пользователь</label>
              <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} />
            </div>
            <div className="db-form-field">
              <label>Пароль</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
          </div>
        </>
      )}
      <div className="db-form-field">
        <label>{dbType === "sqlite" ? "Путь к файлу" : "База данных"}</label>
        <input type="text" value={database} onChange={(e) => setDatabase(e.target.value)} required placeholder={dbType === "sqlite" ? "/path/to/db.sqlite" : "mydb"} />
      </div>
      <label className="db-form-check">
        <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} />
        Публичное (доступно всем)
      </label>
      <div className="db-form-actions">
        <button type="submit" className="db-form-submit" disabled={submitting}>
          {submitting ? "Подключение..." : "Подключить"}
        </button>
        <button type="button" className="db-form-cancel" onClick={() => { setOpen(false); resetForm(); }}>Отмена</button>
      </div>
    </form>
  );
}
