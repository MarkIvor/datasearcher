import { useEffect, useCallback } from "react";

export function useKeyboardShortcuts(handlers: {
  onSend?: () => void;
  onClear?: () => void;
  onNewChat?: () => void;
  onExportPDF?: () => void;
  onToggleTheme?: () => void;
  onFocusInput?: () => void;
}) {
  const onKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const mod = e.ctrlKey || e.metaKey;

      if (mod && e.key === "Enter" && handlers.onSend) {
        e.preventDefault();
        handlers.onSend();
      }
      if (mod && e.shiftKey && e.key === "p" && handlers.onExportPDF) {
        e.preventDefault();
        handlers.onExportPDF();
      }
      if (mod && e.key === "d" && handlers.onToggleTheme) {
        e.preventDefault();
        handlers.onToggleTheme();
      }
      if (mod && e.key === "k" && handlers.onFocusInput) {
        e.preventDefault();
        handlers.onFocusInput();
      }
      if (mod && e.shiftKey && e.key === "Delete" && handlers.onClear) {
        e.preventDefault();
        handlers.onClear();
      }
      if (mod && e.shiftKey && e.key === "N" && handlers.onNewChat) {
        e.preventDefault();
        handlers.onNewChat();
      }
    },
    [handlers]
  );

  useEffect(() => {
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onKeyDown]);
}
