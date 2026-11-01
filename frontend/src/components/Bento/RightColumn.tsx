import { useState } from "react";
import { ArrowUpRight, Check } from "lucide-react";
import type { FileInfo } from "../../types";
import type { SetupState } from "../../api/client";
import { useI18n } from "../../i18n";

interface Props {
  files: FileInfo[];
  setup: SetupState | null;
  isStreaming: boolean;
  onAction: (query: string) => void;
}

export function RightColumn({ files, setup, isStreaming, onAction }: Props) {
  const { t, fmt } = useI18n();
  const [selected, setSelected] = useState<string>("overview");

  const templates = [
    { id: "overview", label: t("right.template.overview"), query: t("chat.query.overview") },
    { id: "dashboard", label: t("right.template.dashboard"), query: t("chat.query.dashboard") },
    { id: "audit", label: t("right.template.audit"), query: t("chat.query.audit") },
    { id: "insights", label: t("right.template.insights"), query: t("chat.query.insights") },
  ];
  const active = templates.find((tpl) => tpl.id === selected) ?? templates[0];

  const totalRows = files.reduce((sum, f) => sum + f.row_count, 0);
  const totalCols = files.reduce((sum, f) => sum + f.columns.length, 0);
  const modeLabel = setup?.mode === "mcp" ? t("right.modeMcp") : setup?.mode === "interface" ? t("right.modeInterface") : "—";
  const llmModel = setup?.llm?.model || t("right.notSet");

  return (
    <div className="bento-col bento-right">
      <section className="summary-card">
        <div className="summary-head">
          <span className="summary-title">{t("right.summary")}</span>
          <span className={`summary-status-pill ${files.length > 0 ? "active" : ""}`}>
            <span className="pill-dot" />
            {files.length > 0 ? t("right.active") : t("right.draft")}
          </span>
        </div>

        <div className="summary-kv">
          <div className="summary-kv-row">
            <span className="summary-key">{t("right.type")}</span>
            <span className="summary-value">{modeLabel}</span>
          </div>
          <div className="summary-kv-row">
            <span className="summary-key">{t("right.llm")}</span>
            <span className="summary-value">{llmModel}</span>
          </div>
          <div className="summary-kv-row">
            <span className="summary-key">{t("right.tables")}</span>
            <span className="summary-value">{files.length}</span>
          </div>
          <div className="summary-kv-row">
            <span className="summary-key">{t("right.stream")}</span>
            <span className="summary-value">{isStreaming ? t("right.streamActive") : t("right.streamIdle")}</span>
          </div>
        </div>

        <hr className="summary-divider" />
        <div className="summary-metric-label">{t("right.rowsMetric")}</div>
        <div className="summary-metric-value">{fmt(totalRows)}</div>
      </section>

      <div className="info-pills">
        <div className="info-pill">
          <span className="info-pill-value">{fmt(totalCols)}</span>
          <span className="info-pill-label">{t("right.colsPill")}</span>
        </div>
        <div className="info-pill">
          <span className="info-pill-value">{setup?.connections_count ?? 0}</span>
          <span className="info-pill-label">{t("right.connsPill")}</span>
        </div>
      </div>

      <section className="action-card">
        <div className="action-head">
          <span className="action-title">{t("right.action")}</span>
        </div>

        {templates.map((tpl) => (
          <button
            key={tpl.id}
            className={`toggle-pill ${selected === tpl.id ? "selected" : ""}`}
            onClick={() => setSelected(tpl.id)}
            disabled={isStreaming}
          >
            <span>{tpl.label}</span>
            <span className="toggle-check">
              {selected === tpl.id && <Check size={13} strokeWidth={3} />}
            </span>
          </button>
        ))}

        <div className="sec-chips">
          {setup?.enterprise && (
            <>
              <span className={`sec-chip ${setup.enterprise.read_only ? "on" : ""}`}>
                <span className="chip-dot" /> {t("right.sec.readonly")}
              </span>
              <span className={`sec-chip ${setup.enterprise.pii_masking ? "on" : ""}`}>
                <span className="chip-dot" /> {t("right.sec.pii")}
              </span>
              <span className={`sec-chip ${setup.enterprise.log_enabled ? "on" : ""}`}>
                <span className="chip-dot" /> {t("right.sec.logs")}
              </span>
              <span className={`sec-chip ${setup.enterprise.rate_limit_enabled ? "on" : ""}`}>
                <span className="chip-dot" /> {t("right.sec.ratelimit")}
              </span>
            </>
          )}
        </div>

        <button
          className="cta-btn"
          onClick={() => onAction(active.query)}
          disabled={files.length === 0 || isStreaming}
          title={files.length === 0 ? t("right.cta.hint") : t("right.cta.run")}
        >
          <span>{files.length === 0 ? t("right.cta.noData") : t("right.cta.run")}</span>
          <span className="cta-badge"><ArrowUpRight size={15} /></span>
        </button>
      </section>
    </div>
  );
}
