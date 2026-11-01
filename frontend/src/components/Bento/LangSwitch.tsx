import { Languages } from "lucide-react";
import { useI18n } from "../../i18n";

interface Props {
  variant?: "round" | "pill";
}

export function LangSwitch({ variant = "round" }: Props) {
  const { lang, toggleLang, t } = useI18n();

  if (variant === "pill") {
    return (
      <button className="session-chip" onClick={toggleLang} title={t("common.langTitle")}>
        <Languages size={12} style={{ marginRight: 4, verticalAlign: "-2px" }} />
        {lang === "ru" ? "RU" : "EN"}
      </button>
    );
  }

  return (
    <button className="icon-round" onClick={toggleLang} title={t("common.langTitle")}>
      <span style={{ fontSize: 11, fontWeight: 700 }}>{lang === "ru" ? "RU" : "EN"}</span>
    </button>
  );
}
