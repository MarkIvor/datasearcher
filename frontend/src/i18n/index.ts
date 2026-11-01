import { useCallback, useSyncExternalStore } from "react";
import { translate, type Lang, type Translate } from "./dict";

export { translate };

export type { Lang, Translate };

const LANG_KEY = "ds-lang";

function detectLang(): Lang {
  try {
    const saved = localStorage.getItem(LANG_KEY);
    if (saved === "ru" || saved === "en") return saved;
  } catch {
    /* jsdom / privacy mode */
  }
  try {
    const nav = navigator.language || (navigator.languages && navigator.languages[0]) || "";
    return nav.toLowerCase().startsWith("ru") ? "ru" : "en";
  } catch {
    return "en";
  }
}

let currentLang: Lang = detectLang();
const listeners = new Set<() => void>();

function emit() {
  for (const fn of listeners) fn();
}

export function setLang(lang: Lang): void {
  if (lang === currentLang) return;
  currentLang = lang;
  try {
    localStorage.setItem(LANG_KEY, lang);
    document.documentElement.setAttribute("lang", lang);
  } catch {
    /* ignore */
  }
  emit();
}

export function toggleLang(): void {
  setLang(currentLang === "ru" ? "en" : "ru");
}

export function getLang(): Lang {
  return currentLang;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useI18n(): {
  lang: Lang;
  setLang: (l: Lang) => void;
  toggleLang: () => void;
  t: Translate;
  fmt: (n: number) => string;
} {
  const lang = useSyncExternalStore(subscribe, getLang, () => currentLang);
  const t = useCallback<Translate>(
    (key, params) => translate(lang, key, params),
    [lang]
  );
  const fmt = useCallback(
    (n: number) => n.toLocaleString(lang === "ru" ? "ru-RU" : "en-US"),
    [lang]
  );
  return { lang, setLang, toggleLang, t, fmt };
}
