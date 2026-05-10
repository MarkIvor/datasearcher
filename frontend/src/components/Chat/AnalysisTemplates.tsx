import { BarChart3, Search, Shield, TrendingUp, Lightbulb, FileText } from "lucide-react";

interface Props {
  onSelect: (query: string) => void;
}

const TEMPLATES = [
  {
    icon: Lightbulb,
    title: "Обзор данных",
    desc: "Структура, типы, пропуски, топ-значения",
    query: "Сделай краткий обзор структуры данных: типы колонок, пропуски, уникальные значения",
    color: "#5b6af0",
  },
  {
    icon: BarChart3,
    title: "Дашборд",
    desc: "Ключевые метрики и графики",
    query: "Построй дашборд с ключевыми метриками и визуализациями",
    color: "#8b5cf6",
  },
  {
    icon: Shield,
    title: "Аудит качества",
    desc: "Дубликаты, аномалии, пропуски",
    query: "Проведи аудит качества данных: найди дубликаты, пропуски, аномалии и выбросы",
    color: "#ef4444",
  },
  {
    icon: TrendingUp,
    title: "Тренды и прогноз",
    desc: "Временные ряды и прогнозирование",
    query: "Проанализируй временные тренды и построй прогноз",
    color: "#10b981",
  },
  {
    icon: Search,
    title: "Корреляции",
    desc: "Связи между переменными",
    query: "Найди корреляции и взаимосвязи между переменными",
    color: "#f59e0b",
  },
  {
    icon: FileText,
    title: "История данных",
    desc: "Полный нарратив и инсайты",
    query: "Расскажи историю данных — ключевые находки и инсайты",
    color: "#06b6d4",
  },
];

export function AnalysisTemplates({ onSelect }: Props) {
  return (
    <div className="analysis-templates">
      <div className="at-title">Шаблоны анализа</div>
      <div className="at-grid">
        {TEMPLATES.map((t) => (
          <button
            key={t.title}
            className="at-card"
            onClick={() => onSelect(t.query)}
          >
            <div className="at-icon" style={{ background: t.color + "14", color: t.color }}>
              <t.icon size={18} />
            </div>
            <div className="at-info">
              <span className="at-name">{t.title}</span>
              <span className="at-desc">{t.desc}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
