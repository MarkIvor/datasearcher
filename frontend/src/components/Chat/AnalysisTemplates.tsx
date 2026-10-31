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
  },
  {
    icon: BarChart3,
    title: "Дашборд",
    desc: "Ключевые метрики и графики",
    query: "Построй дашборд с ключевыми метриками и визуализациями",
  },
  {
    icon: Shield,
    title: "Аудит качества",
    desc: "Дубликаты, аномалии, пропуски",
    query: "Проведи аудит качества данных: найди дубликаты, пропуски, аномалии и выбросы",
  },
  {
    icon: TrendingUp,
    title: "Тренды и прогноз",
    desc: "Временные ряды и прогнозирование",
    query: "Проанализируй временные тренды и построй прогноз",
  },
  {
    icon: Search,
    title: "Корреляции",
    desc: "Связи между переменными",
    query: "Найди корреляции и взаимосвязи между переменными",
  },
  {
    icon: FileText,
    title: "История данных",
    desc: "Полный нарратив и инсайты",
    query: "Расскажи историю данных — ключевые находки и инсайты",
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
            <div className="at-icon">
              <t.icon size={17} />
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

