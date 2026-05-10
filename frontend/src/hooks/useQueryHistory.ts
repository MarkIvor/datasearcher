import { useState, useCallback, useEffect } from "react";

interface HistoryEntry {
  query: string;
  timestamp: number;
}

const MAX_HISTORY = 50;
const STORAGE_KEY = "ds-query-history";

export function useQueryHistory() {
  const [history, setHistory] = useState<HistoryEntry[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  }, [history]);

  const add = useCallback((query: string) => {
    const trimmed = query.trim();
    if (!trimmed) return;
    setHistory((prev) => {
      const filtered = prev.filter((h) => h.query !== trimmed);
      return [{ query: trimmed, timestamp: Date.now() }, ...filtered].slice(0, MAX_HISTORY);
    });
  }, []);

  const clear = useCallback(() => setHistory([]), []);

  return { history, add, clear };
}
