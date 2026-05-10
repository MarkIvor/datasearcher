import { useState } from "react";
import { X, LayoutDashboard, Loader2, Lock, Check, Copy } from "lucide-react";
import * as api from "../../api/client";

interface Props {
  onClose: () => void;
}

export default function DashboardCreateModal({ onClose }: Props) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [password, setPassword] = useState("");
  const [creating, setCreating] = useState(false);
  const [result, setResult] = useState<{ slug: string; url: string; title: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError("");
    try {
      const r = await api.generateDashboard(title, description, password);
      setResult({ slug: r.slug, url: r.url, title: r.title });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка создания");
    }
    setCreating(false);
  };

  const copyUrl = () => {
    if (!result) return;
    const url = window.location.origin + "/d/" + result.slug;
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (result) {
    return (
      <div className="dash-create-overlay" onClick={onClose}>
        <div className="dash-create-modal" onClick={(e) => e.stopPropagation()}>
          <div className="dash-create-success">
            <Check size={48} />
            <h2>Дашборд создан!</h2>
            <p className="dash-create-title">{result.title}</p>
            <div className="dash-create-url-row">
              <input readOnly value={window.location.origin + "/d/" + result.slug} className="dash-create-url" />
              <button className="dash-create-copy" onClick={copyUrl}>
                {copied ? <Check size={14} /> : <Copy size={14} />}
              </button>
            </div>
            <a href={`/d/${result.slug}`} target="_blank" rel="noopener" className="dash-create-open">
              Открыть дашборд →
            </a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="dash-create-overlay" onClick={onClose}>
      <div className="dash-create-modal" onClick={(e) => e.stopPropagation()}>
        <div className="dash-create-header">
          <div className="dash-create-title-row">
            <LayoutDashboard size={20} />
            <h2>Создать публичный дашборд</h2>
          </div>
          <button className="admin-close" onClick={onClose}><X size={18} /></button>
        </div>

        <form className="dash-create-body" onSubmit={handleCreate}>
          <p className="dash-create-hint">
            ИИ проанализирует ваши данные и автоматически создаст интерактивный дашборд
            с KPI-карточками, графиками и селекторами фильтров.
          </p>
          <div className="admin-field">
            <label>Название</label>
            <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Продажи Q1 2026" />
          </div>
          <div className="admin-field">
            <label>Описание</label>
            <input type="text" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Дашборд по продажам" />
          </div>
          <div className="admin-field">
            <label><Lock size={12} style={{ verticalAlign: "middle", marginRight: 4 }} />Пароль (необязательно)</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Оставьте пустым для публичного доступа" />
          </div>
          {error && <div className="dash-create-error">{error}</div>}
          <div className="admin-form-actions">
            <button type="submit" className="admin-submit-btn" disabled={creating}>
              {creating ? <><Loader2 size={14} className="spin" /> Генерация...</> : "Создать дашборд"}
            </button>
            <button type="button" className="admin-cancel-btn" onClick={onClose}>Отмена</button>
          </div>
        </form>
      </div>
    </div>
  );
}
