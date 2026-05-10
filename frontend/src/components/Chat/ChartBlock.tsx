import { useRef, useCallback } from "react";
import { toPng } from "html-to-image";
import type { ChartSpec } from "../../types";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  ScatterChart, Scatter, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { Download } from "lucide-react";

const CHART_COLORS = ["#5b6af0", "#8b5cf6", "#f59e0b", "#10b981", "#ef4444", "#06b6d4", "#ec4899", "#6366f1"];

interface Props {
  spec: ChartSpec;
  compact?: boolean;
}

function formatNumber(value: number): string {
  if (Math.abs(value) >= 1_000_000) return (value / 1_000_000).toFixed(1) + "M";
  if (Math.abs(value) >= 1_000) return (value / 1_000).toFixed(1) + "K";
  return value.toFixed(value % 1 === 0 ? 0 : 1);
}

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; color: string }>; label?: string }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "white", border: "1px solid #e5e6ea", borderRadius: 10,
      padding: "10px 14px", boxShadow: "0 4px 16px rgba(0,0,0,0.08)", fontSize: 12,
    }}>
      {label !== undefined && <div style={{ fontWeight: 600, marginBottom: 4, color: "#111318" }}>{String(label)}</div>}
      {payload.map((p, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 2 }}>
          <span style={{ width: 8, height: 8, borderRadius: 2, background: p.color, display: "inline-block" }} />
          <span style={{ color: "#55585e" }}>{p.name}:</span>
          <span style={{ fontWeight: 600, color: "#111318" }}>{typeof p.value === "number" ? formatNumber(p.value) : String(p.value)}</span>
        </div>
      ))}
    </div>
  );
};

export function ChartBlock({ spec, compact }: Props) {
  const { type, title, data, xKey, yKeys, horizontal, isForecast } = spec;
  const height = compact ? 200 : 300;
  const chartRef = useRef<HTMLDivElement>(null);

  const handleExportPNG = useCallback(async () => {
    if (!chartRef.current) return;
    try {
      const dataUrl = await toPng(chartRef.current, { backgroundColor: "#ffffff", pixelRatio: 2 });
      const link = document.createElement("a");
      link.download = `${title || "chart"}.png`;
      link.href = dataUrl;
      link.click();
    } catch {
      // ignore
    }
  }, [title]);

  const tickStyle = { fontSize: 11, fill: "#93969c" };
  const gridStyle = { strokeDasharray: "3 3", stroke: "#eff0f2" };

  const renderChart = () => {
    switch (type) {
      case "bar":
        return horizontal ? (
          <ResponsiveContainer width="100%" height={height}>
            <BarChart data={data} layout="vertical" margin={{ left: 70, right: 20, top: 5, bottom: 5 }}>
              <CartesianGrid {...gridStyle} />
              <XAxis type="number" tick={tickStyle} tickFormatter={formatNumber} />
              <YAxis dataKey={xKey} type="category" tick={tickStyle} width={60} />
              <Tooltip content={<CustomTooltip />} />
              {yKeys.map((key, i) => (
                <Bar key={key} dataKey={key} fill={CHART_COLORS[i % CHART_COLORS.length]} radius={[0, 6, 6, 0]} animationDuration={800} animationBegin={i * 100} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <ResponsiveContainer width="100%" height={height}>
            <BarChart data={data} margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
              <CartesianGrid {...gridStyle} />
              <XAxis dataKey={xKey} tick={tickStyle} />
              <YAxis tick={tickStyle} tickFormatter={formatNumber} />
              <Tooltip content={<CustomTooltip />} />
              {yKeys.map((key, i) => (
                <Bar key={key} dataKey={key} fill={CHART_COLORS[i % CHART_COLORS.length]} radius={[6, 6, 0, 0]} animationDuration={800} animationBegin={i * 100} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        );

      case "line":
        return (
          <ResponsiveContainer width="100%" height={height}>
            <LineChart data={data} margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
              <CartesianGrid {...gridStyle} />
              <XAxis dataKey={xKey} tick={tickStyle} />
              <YAxis tick={tickStyle} tickFormatter={formatNumber} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11, paddingTop: 6 }} />
              {yKeys.map((key, i) => (
                <Line key={key} type="monotone" dataKey={key} stroke={CHART_COLORS[i % CHART_COLORS.length]} strokeWidth={2.5} dot={data.length < 30 ? { r: 3, strokeWidth: 0, fill: CHART_COLORS[i % CHART_COLORS.length] } : false} activeDot={{ r: 5, strokeWidth: 2, stroke: "white" }} animationDuration={1000} animationBegin={i * 200} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        );

      case "pie":
        return (
          <ResponsiveContainer width="100%" height={height}>
            <PieChart>
              <Pie data={data} dataKey={yKeys[0]} nameKey={xKey} cx="50%" cy="50%" outerRadius={height / 2.6} innerRadius={height / 6} paddingAngle={2} label={({ name, percent }: { name?: string; percent?: number }) => `${name || ""} ${((percent || 0) * 100).toFixed(0)}%`} labelLine={false} animationDuration={900} animationBegin={0}>
                {data.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} stroke="white" strokeWidth={2} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        );

      case "scatter":
        return (
          <ResponsiveContainer width="100%" height={height}>
            <ScatterChart margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
              <CartesianGrid {...gridStyle} />
              <XAxis dataKey={xKey} tick={tickStyle} name={xKey} type="number" />
              <YAxis dataKey={yKeys[0]} tick={tickStyle} name={yKeys[0]} type="number" />
              <Tooltip content={<CustomTooltip />} />
              <Scatter data={data} fill={CHART_COLORS[0]} animationDuration={800} />
            </ScatterChart>
          </ResponsiveContainer>
        );

      case "area":
        return (
          <ResponsiveContainer width="100%" height={height}>
            <AreaChart data={data} margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
              <CartesianGrid {...gridStyle} />
              <XAxis dataKey={xKey} tick={tickStyle} />
              <YAxis tick={tickStyle} tickFormatter={formatNumber} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11, paddingTop: 6 }} />
              {yKeys.map((key, i) => (
                <Area key={key} type="monotone" dataKey={key} stroke={CHART_COLORS[i % CHART_COLORS.length]} fill={CHART_COLORS[i % CHART_COLORS.length]} fillOpacity={i === 0 ? 0.12 : 0.06} strokeWidth={2.5} strokeDasharray={i > 0 && isForecast ? "5 5" : undefined} animationDuration={1200} animationBegin={i * 200} />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        );

      case "histogram":
        return (
          <ResponsiveContainer width="100%" height={height}>
            <BarChart data={data} margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
              <CartesianGrid {...gridStyle} />
              <XAxis dataKey={xKey} tick={tickStyle} />
              <YAxis tick={tickStyle} tickFormatter={formatNumber} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey={yKeys[0]} fill={CHART_COLORS[0]} radius={[4, 4, 0, 0]} animationDuration={800} />
            </BarChart>
          </ResponsiveContainer>
        );

      default:
        return <div>Неподдерживаемый тип графика: {type}</div>;
    }
  };

  return (
    <div className="chart-block">
      <div className="chart-header-row">
        {title && <div className="chart-title">{title}</div>}
        <button className="chart-png-btn" onClick={handleExportPNG} title="Сохранить PNG">
          <Download size={14} />
        </button>
      </div>
      <div ref={chartRef}>
        {renderChart()}
      </div>
    </div>
  );
}
