import { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import { Lock, Eye, RefreshCw, ExternalLink, Copy, Check } from "lucide-react";
import * as api from "../api/client";
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area,
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

const COLORS = ["#5b6af0", "#8b5cf6", "#f59e0b", "#10b981", "#ef4444", "#06b6d4", "#ec4899", "#6366f1"];

function formatValue(val: number | null | undefined, fmt?: string, prefix?: string, suffix?: string) {
  if (val == null) return "—";
  let s: string;
  if (fmt === "currency") s = val.toLocaleString("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 });
  else if (fmt === "percent") s = val.toLocaleString("ru-RU", { maximumFractionDigits: 1 }) + "%";
  else s = val.toLocaleString("ru-RU", { maximumFractionDigits: 2 });
  return `${prefix || ""}${s}${suffix || ""}`;
}

export function DashboardPage() {
  const { slug } = useParams<{ slug: string }>();
  const [dash, setDash] = useState<api.DashboardDetail | null>(null);
  const [cards, setCards] = useState<api.DashboardCard[]>([]);
  const [filters, setFilters] = useState<Record<string, unknown>>({});
  const [token, setToken] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!slug) return;
    api.getDashboard(slug).then((d) => {
      setDash(d);
      if (!d.has_password) loadCards(slug, {});
      else setLoading(false);
    }).catch(() => setLoading(false));
  }, [slug]);

  const loadCards = useCallback(async (s: string, f: Record<string, unknown>, t?: string) => {
    setRefreshing(true);
    try {
      const result = await api.queryDashboard(s, f, t || undefined);
      setCards(result.cards);
    } catch { /* */ }
    setLoading(false);
    setRefreshing(false);
  }, []);

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!slug) return;
    try {
      const r = await api.authDashboard(slug, password);
      setToken(r.token);
      loadCards(slug, filters, r.token);
    } catch {
      setPasswordError("Неверный пароль");
    }
  };

  const handleFilterChange = (id: string, value: unknown) => {
    const next = { ...filters, [id]: value };
    setFilters(next);
    if (slug) loadCards(slug, next, token || undefined);
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) return <div className="dash-page"><div className="dash-loader"><RefreshCw className="spin" size={24} /> Загрузка...</div></div>;

  if (dash?.has_password && !token) {
    return (
      <div className="dash-page">
        <div className="dash-lock">
          <Lock size={32} />
          <h2>{dash.title}</h2>
          <p>Этот дашборд защищён паролем</p>
          <form onSubmit={handlePasswordSubmit}>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Введите пароль" autoFocus />
            <button type="submit">Войти</button>
          </form>
          {passwordError && <div className="dash-lock-error">{passwordError}</div>}
        </div>
      </div>
    );
  }

  if (!dash) return <div className="dash-page"><div className="dash-loader">Дашборд не найден</div></div>;

  const selectors = dash.config.selectors || [];
  const kpis = cards.filter((c) => c.type === "kpi");
  const charts = cards.filter((c) => c.type === "chart");
  const tables = cards.filter((c) => c.type === "table");
  const errors = cards.filter((c) => c.type === "error");
  const activeFilters = Object.values(filters).filter((v) => v !== undefined && v !== null && v !== "" && v !== 0).length;

  return (
    <div className="dash-page">
      <div className="dash-header">
        <div className="dash-title-row">
          <h1 className="dash-title">{dash.title}</h1>
          <div className="dash-header-actions">
            {activeFilters > 0 && <span className="dash-filter-badge">{activeFilters} фильтр</span>}
            <span className="dash-views"><Eye size={13} /> {dash.views}</span>
            <button className="dash-icon-btn" onClick={handleCopyLink} title="Скопировать ссылку">
              {copied ? <Check size={14} /> : <Copy size={14} />}
            </button>
            <button className="dash-icon-btn" onClick={() => slug && loadCards(slug, filters, token || undefined)} disabled={refreshing} title="Обновить">
              <RefreshCw size={14} className={refreshing ? "spin" : ""} />
            </button>
          </div>
        </div>
        {dash.description && <p className="dash-desc">{dash.description}</p>}
      </div>

      {selectors.length > 0 && (
        <div className="dash-selectors">
          {selectors.map((sel) => (
            <DashSelector key={sel.id} slug={slug!} selector={sel} value={filters[sel.id]} onChange={(v) => handleFilterChange(sel.id, v)} />
          ))}
        </div>
      )}

      {kpis.length > 0 && (
        <div className="dash-kpi-row">
          {kpis.map((card) => (
            <div key={card.id} className="dash-card dash-card-kpi">
              <div className="dash-kpi-label">{card.title}</div>
              <div className="dash-kpi-value">{formatValue(typeof card.rows?.[0]?.[0] === "number" ? card.rows[0][0] : Number(card.rows?.[0]?.[0]), card.format, card.prefix, card.suffix)}</div>
            </div>
          ))}
        </div>
      )}

      {errors.length > 0 && (
        <div className="dash-errors-row">
          {errors.map((card) => (
            <div key={card.id} className="dash-card dash-card-error">
              <div className="dash-card-error-icon">!</div>
              <div className="dash-card-error-body">
                <div className="dash-card-title">{card.title}</div>
                <div className="dash-card-error-text">{card.error}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {charts.length > 0 && (
        <div className="dash-charts-grid">
          {charts.map((card) => {
            if (!card.rows || !card.columns) return null;
            const data = card.rows.map((row) => {
              const obj: Record<string, unknown> = {};
              card.columns!.forEach((col, i) => { obj[col] = row[i]; });
              return obj;
            });
            return (
              <div key={card.id} className="dash-card dash-card-chart">
                <h3 className="dash-card-title">{card.title}</h3>
                <div className="dash-chart-wrap">
                  <ChartRenderer chartType={card.chart_type || "bar"} data={data} x={card.x || card.columns[0]} y={card.y || card.columns[1]} />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {tables.length > 0 && (
        <div className="dash-tables-section">
          {tables.map((card) => {
            if (!card.rows || !card.columns) return null;
            return (
              <div key={card.id} className="dash-card dash-card-table">
                <h3 className="dash-card-title">{card.title}</h3>
                <div className="dash-table-wrap">
                  <table>
                    <thead><tr>{card.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                    <tbody>{card.rows.slice(0, 30).map((row, i) => (<tr key={i}>{row.map((v, j) => <td key={j}>{v ?? "—"}</td>)}</tr>))}</tbody>
                  </table>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="dash-footer">
        <span>DataSearcher</span>
        <a href="/" className="dash-footer-link">Создать свой дашборд <ExternalLink size={10} /></a>
      </div>
    </div>
  );
}

function DashSelector({ slug, selector, value, onChange }: {
  slug: string;
  selector: { id: string; type: string; column: string; table: string; label: string };
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const [options, setOptions] = useState<string[]>([]);

  useEffect(() => {
    if (selector.type !== "category") return;
    const API_BASE = import.meta.env.VITE_API_URL || "";
    fetch(`${API_BASE}/api/dashboards/${slug}/options?table=${encodeURIComponent(selector.table)}&column=${encodeURIComponent(selector.column)}`)
      .then((r) => r.json())
      .then((d) => { if (d.values) setOptions(d.values); })
      .catch(() => {});
  }, [slug, selector.type, selector.table, selector.column]);

  if (selector.type === "category") {
    return (
      <div className="dash-sel">
        <label className="dash-sel-label">{selector.label}</label>
        <select className="dash-sel-input" value={(value as string) || ""} onChange={(e) => onChange(e.target.value || null)}>
          <option value="">Все</option>
          {options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      </div>
    );
  }

  if (selector.type === "date_range") {
    const v = (value as { from?: string; to?: string }) || {};
    return (
      <div className="dash-sel">
        <label className="dash-sel-label">{selector.label}</label>
        <div className="dash-sel-range">
          <input type="date" className="dash-sel-input" value={v.from || ""} onChange={(e) => onChange({ ...v, from: e.target.value })} />
          <span className="dash-sel-sep">—</span>
          <input type="date" className="dash-sel-input" value={v.to || ""} onChange={(e) => onChange({ ...v, to: e.target.value })} />
        </div>
      </div>
    );
  }

  if (selector.type === "number_range") {
    const v = (value as { min?: number; max?: number }) || {};
    return (
      <div className="dash-sel">
        <label className="dash-sel-label">{selector.label}</label>
        <div className="dash-sel-range">
          <input type="number" className="dash-sel-input dash-sel-num" value={v.min ?? ""} placeholder="от" onChange={(e) => onChange({ ...v, min: e.target.value ? Number(e.target.value) : undefined })} />
          <span className="dash-sel-sep">—</span>
          <input type="number" className="dash-sel-input dash-sel-num" value={v.max ?? ""} placeholder="до" onChange={(e) => onChange({ ...v, max: e.target.value ? Number(e.target.value) : undefined })} />
        </div>
      </div>
    );
  }

  return null;
}

function ChartRenderer({ chartType, data, x, y }: { chartType: string; data: Record<string, unknown>[]; x: string; y: string }) {
  const safeData = data.map((d) => ({ ...d, [y]: Number(d[y]) || 0, [x]: d[x] ?? "" }));
  const axisStyle = { fontSize: 11, fill: "var(--text-muted)" };

  if (chartType === "line") {
    return (
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={safeData} margin={{ top: 4, right: 12, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
          <XAxis dataKey={x} tick={axisStyle} tickLine={false} interval="preserveStartEnd" />
          <YAxis tick={axisStyle} tickLine={false} width={48} />
          <Tooltip /><Legend />
          <Line type="monotone" dataKey={y} stroke="#5b6af0" strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    );
  }
  if (chartType === "bar") {
    return (
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={safeData} margin={{ top: 4, right: 12, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
          <XAxis dataKey={x} tick={axisStyle} tickLine={false} interval={0} angle={-20} textAnchor="end" height={50} />
          <YAxis tick={axisStyle} tickLine={false} width={48} />
          <Tooltip /><Legend />
          <Bar dataKey={y} fill="#5b6af0" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }
  if (chartType === "area") {
    return (
      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={safeData} margin={{ top: 4, right: 12, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
          <XAxis dataKey={x} tick={axisStyle} tickLine={false} />
          <YAxis tick={axisStyle} tickLine={false} width={48} />
          <Tooltip /><Legend />
          <defs><linearGradient id="gradFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#5b6af0" stopOpacity={0.3} /><stop offset="100%" stopColor="#5b6af0" stopOpacity={0.02} /></linearGradient></defs>
          <Area type="monotone" dataKey={y} stroke="#5b6af0" fill="url(#gradFill)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    );
  }
  if (chartType === "pie") {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
          <Pie data={safeData} dataKey={y} nameKey={x} cx="50%" cy="45%" outerRadius={80} innerRadius={40} label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`} labelLine={{ stroke: "var(--text-muted)", strokeWidth: 1 }}>
            {safeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Pie>
          <Tooltip /><Legend wrapperStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    );
  }
  if (chartType === "scatter") {
    return (
      <ResponsiveContainer width="100%" height={260}>
        <ScatterChart margin={{ top: 4, right: 12, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
          <XAxis dataKey={x} tick={axisStyle} name={x} />
          <YAxis dataKey={y} tick={axisStyle} name={y} width={48} />
          <Tooltip cursor={{ strokeDasharray: "3 3" }} />
          <Scatter data={safeData} fill="#5b6af0" r={4} />
        </ScatterChart>
      </ResponsiveContainer>
    );
  }

  return <div className="dash-chart-fallback">Тип графика: {chartType}</div>;
}
