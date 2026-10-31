import { useState } from "react";
import { X, Link2, Copy, Check } from "lucide-react";
import * as api from "../../api/client";

interface Props {
  onClose: () => void;
}

const BI_TOOLS = [
  { value: "superset", label: "Apache Superset" },
  { value: "grafana", label: "Grafana" },
  { value: "datalens", label: "Yandex Datalens" },
  { value: "tableau", label: "Tableau" },
  { value: "powerbi", label: "Power BI" },
];

export function BILinkModal({ onClose }: Props) {
  const [tool, setTool] = useState("superset");
  const [baseUrl, setBaseUrl] = useState("");
  const [dashboardId, setDashboardId] = useState("");
  const [paramsText, setParamsText] = useState('{\n  "region": "Москва"\n}');
  const [timeFrom, setTimeFrom] = useState("");
  const [timeTo, setTimeTo] = useState("");
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleBuild = async () => {
    setError("");
    setUrl("");
    if (!baseUrl) {
      setError("Укажите базовый URL");
      return;
    }
    let params: Record<string, string> | undefined;
    if (paramsText.trim()) {
      try {
        params = JSON.parse(paramsText);
      } catch {
        setError("params должен быть валидным JSON");
        return;
      }
    }
    setLoading(true);
    try {
      const res = await api.buildBILink({
        tool, base_url: baseUrl, dashboard_id: dashboardId,
        params, time_from: timeFrom, time_to: timeTo,
      });
      setUrl(res.url);
    } catch (err) {
      setError((err as Error).message);
    }
    setLoading(false);
  };

  const copyUrl = () => {
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const showTime = tool === "grafana";

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{ maxWidth: 520 }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3><Link2 size={16} style={{ marginRight: 6, verticalAlign: "middle" }} />BI Link Builder</h3>
          <button className="modal-close" onClick={onClose}><X size={18} /></button>
        </div>
        <div className="modal-body">
          <div className="form-group">
            <label>BI-инструмент</label>
            <select value={tool} onChange={(e) => setTool(e.target.value)} className="form-input">
              {BI_TOOLS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Базовый URL</label>
            <input className="form-input" placeholder="https://superset.company.com" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
          </div>
          <div className="form-group">
            <label>ID дашборда / чарта</label>
            <input className="form-input" placeholder="5" value={dashboardId} onChange={(e) => setDashboardId(e.target.value)} />
          </div>
          {showTime && (
            <div style={{ display: "flex", gap: 8 }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label>С (для Grafana)</label>
                <input className="form-input" placeholder="2024-01-01" value={timeFrom} onChange={(e) => setTimeFrom(e.target.value)} />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label>По</label>
                <input className="form-input" placeholder="2024-02-01" value={timeTo} onChange={(e) => setTimeTo(e.target.value)} />
              </div>
            </div>
          )}
          <div className="form-group">
            <label>Фильтры (JSON)</label>
            <textarea className="form-input" rows={4} style={{ fontFamily: "monospace", fontSize: 12 }} value={paramsText} onChange={(e) => setParamsText(e.target.value)} />
          </div>

          {error && <div className="error-msg" style={{ color: "var(--error)", fontSize: 12, fontWeight: 500, marginBottom: 8 }}>{error}</div>}

          {url && (
            <div style={{ border: "1px dashed var(--border-dashed)", borderRadius: 14, padding: 8, marginBottom: 8, background: "var(--surface-idle)" }}>
              <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>Сгенерированная ссылка:</div>
              <div style={{ display: "flex", gap: 6, alignItems: "flex-start" }}>
                <code style={{ fontSize: 11, wordBreak: "break-all", flex: 1 }}>{url}</code>
                <button className="admin-add-btn" style={{ marginBottom: 0, padding: "4px 8px", flexShrink: 0 }} onClick={copyUrl}>
                  {copied ? <Check size={12} /> : <Copy size={12} />}
                </button>
              </div>
            </div>
          )}

          <button className="btn-primary" style={{ width: "100%" }} onClick={handleBuild} disabled={loading}>
            {loading ? "Генерация…" : "Сгенерировать ссылку"}
          </button>
        </div>
      </div>
    </div>
  );
}