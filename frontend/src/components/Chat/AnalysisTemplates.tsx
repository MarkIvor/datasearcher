import { BarChart3, Search, Shield, TrendingUp, Lightbulb, FileText } from "lucide-react";
import { useI18n } from "../../i18n";

interface Props {
  onSelect: (query: string) => void;
}

export function AnalysisTemplates({ onSelect }: Props) {
  const { t } = useI18n();

  const templates = [
    { icon: Lightbulb, title: t("tpl.overview"), desc: t("tpl.overviewDesc"), query: t("chat.query.overview") },
    { icon: BarChart3, title: t("tpl.dashboard"), desc: t("tpl.dashboardDesc"), query: t("chat.query.dashboard") },
    { icon: Shield, title: t("tpl.audit"), desc: t("tpl.auditDesc"), query: t("chat.query.audit") },
    { icon: TrendingUp, title: t("tpl.trend"), desc: t("tpl.trendDesc"), query: t("tpl.query.trend") },
    { icon: Search, title: t("tpl.correlations"), desc: t("tpl.correlationsDesc"), query: t("tpl.query.correlations") },
    { icon: FileText, title: t("tpl.story"), desc: t("tpl.storyDesc"), query: t("tpl.query.story") },
  ];

  return (
    <div className="analysis-templates">
      <div className="at-title">{t("tpl.title")}</div>
      <div className="at-grid">
        {templates.map((tpl) => (
          <button
            key={tpl.title}
            className="at-card"
            onClick={() => onSelect(tpl.query)}
          >
            <div className="at-icon">
              <tpl.icon size={17} />
            </div>
            <div className="at-info">
              <span className="at-name">{tpl.title}</span>
              <span className="at-desc">{tpl.desc}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
