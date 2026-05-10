import { useRef, useEffect, useState, type DragEvent } from "react";
import type { ChatMessage } from "../../types";
import { MessageBubble } from "./MessageBubble";
import { AnalysisTemplates } from "./AnalysisTemplates";
import { Upload, Database } from "lucide-react";
import * as api from "../../api/client";

interface Props {
  messages: ChatMessage[];
  onAction?: (action: string) => void;
  onFileUpload?: (file: File) => Promise<unknown>;
  uploading?: boolean;
  hasFiles?: boolean;
  onFilesChanged?: () => void;
}

export function MessageList({ messages, onAction, onFileUpload, uploading, hasFiles, onFilesChanged }: Props) {
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
      className="message-list"
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={hasFiles ? undefined : handleDrop}
    >
      {messages.length === 0 && (
        <div className="empty-chat">
          <div className="empty-chat-icon">
            <svg width="32" height="32" viewBox="0 0 20 20" fill="none">
              <rect x="2" y="2" width="7" height="7" rx="1.5" fill="white" />
              <rect x="11" y="2" width="7" height="7" rx="1.5" fill="white" opacity="0.6" />
              <rect x="2" y="11" width="7" height="7" rx="1.5" fill="white" opacity="0.6" />
              <rect x="11" y="11" width="7" height="7" rx="1.5" fill="white" opacity="0.3" />
            </svg>
          </div>
          <h2>DataSearcher</h2>
          <p>Загрузите файл и задайте вопрос — ИИ проанализирует данные, построит графики и найдёт инсайты</p>

          {!hasFiles && (
            <div className="empty-zones">
              <div
                className={`empty-drop-zone ${dragOver ? "drag-over" : ""}`}
                onClick={() => inputRef.current?.click()}
              >
                {uploading ? (
                  <span className="empty-drop-uploading">Загрузка...</span>
                ) : (
                  <>
                    <Upload size={24} strokeWidth={1.5} />
                    <span>Перетащите файл или нажмите</span>
                    <span className="empty-drop-hint">.xlsx, .csv — до 100 МБ</span>
                  </>
                )}
                <input
                  ref={inputRef}
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  onChange={handleFileSelect}
                  hidden
                />
              </div>
              <DBConnectZone onConnected={onFilesChanged} />
            </div>
          )}

          {hasFiles && (
            <AnalysisTemplates onSelect={(q) => onAction?.(q)} />
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
      <div className="empty-drop-zone db-zone" onClick={() => setOpen(true)}>
        <Database size={24} strokeWidth={1.5} />
        <span>Подключить базу данных</span>
        <span className="empty-drop-hint">PostgreSQL, MySQL, ClickHouse, SQLite</span>
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
        <div className="db-form-field" style={{ width: 130 }}>
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
            <div className="db-form-field" style={{ width: 80 }}>
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
