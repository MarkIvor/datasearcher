import type { ChatMessage, MessageBlock } from "../types/index";
import { fetchChatStream } from "../api/client";
import { useState, useRef, useCallback } from "react";

let msgId = 0;
function nextId() {
  return `msg-${++msgId}`;
}

interface ToolCallEntry {
  name: string;
  args: Record<string, unknown>;
  status: "running" | "completed";
}

export function useChat(columnHints?: { name: string; type: string }[]) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const sessionIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const toolsRef = useRef<ToolCallEntry[]>([]);
  const hasChartRef = useRef(false);

  const setSessionId = useCallback((id: string) => {
    sessionIdRef.current = id;
  }, []);

  const abort = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setMessages((prev) =>
      prev.map((m) =>
        m.isStreaming
          ? { ...m, isStreaming: false, isStopped: true }
          : m
      )
    );
    setIsStreaming(false);
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      const userMsg: ChatMessage = {
        id: nextId(),
        role: "user",
        blocks: [{ type: "text", content }],
      };

      const assistantMsg: ChatMessage = {
        id: nextId(),
        role: "assistant",
        blocks: [],
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);
      toolsRef.current = [];
      hasChartRef.current = false;

      const controller = new AbortController();
      abortRef.current = controller;

      const updateAssistant = (updater: (m: ChatMessage) => ChatMessage) => {
        setMessages((prev) =>
          prev.map((m) => m.id === assistantMsg.id ? updater(m) : m)
        );
      };

      const appendText = (text: string) => {
        updateAssistant((m) => {
          const lastBlock = m.blocks[m.blocks.length - 1];
          if (lastBlock && lastBlock.type === "text") {
            const newBlocks = [...m.blocks];
            newBlocks[newBlocks.length - 1] = { ...lastBlock, content: lastBlock.content + text };
            return { ...m, blocks: newBlocks };
          }
          return { ...m, blocks: [...m.blocks, { type: "text", content: text }] };
        });
      };

      const syncProgressBlock = () => {
        const tools = toolsRef.current;
        if (tools.length === 0) return;

        const toolSummary = tools.map((t) => ({
          name: t.name,
          status: t.status,
        }));

        updateAssistant((m) => {
          const withoutProgress = m.blocks.filter((b) => b.type !== "progress");
          const hasText = withoutProgress.some(
            (b) => b.type === "text" && b.content.trim()
          );
          const insertIdx = hasText
            ? withoutProgress.findIndex(
                (b) => b.type === "text" && b.content.trim()
              ) + 1
            : withoutProgress.length;

          const newBlocks: MessageBlock[] = [...withoutProgress];
          newBlocks.splice(insertIdx, 0, {
            type: "progress" as const,
            tools: toolSummary,
            isStreaming: m.isStreaming,
          });
          return { ...m, blocks: newBlocks };
        });
      };

      try {
        for await (const event of fetchChatStream(
          content,
          sessionIdRef.current || undefined,
          controller.signal
        )) {
          switch (event.type) {
            case "token":
              appendText(event.content);
              break;

            case "step":
              break;

            case "tool_call": {
              toolsRef.current.forEach((t) => { t.status = "completed"; });
              toolsRef.current.push({
                name: event.name,
                args: event.args,
                status: "running",
              });
              syncProgressBlock();
              break;
            }

            case "tool_result": {
              const running = toolsRef.current.find(
                (t) => t.name === event.name && t.status === "running"
              );
              if (running) running.status = "completed";
              syncProgressBlock();
              break;
            }

            case "chart": {
              hasChartRef.current = true;
              toolsRef.current.forEach((t) => { t.status = "completed"; });
              syncProgressBlock();
              updateAssistant((m) => ({
                ...m,
                blocks: [...m.blocks, { type: "chart", spec: event.spec }],
              }));
              break;
            }

            case "dashboard": {
              toolsRef.current.forEach((t) => { t.status = "completed"; });
              syncProgressBlock();
              updateAssistant((m) => ({
                ...m,
                blocks: [...m.blocks, { type: "dashboard", slug: event.slug, title: event.title, url: event.url, has_password: event.has_password }],
              }));
              break;
            }

            case "export":
              appendText(
                `\n\n📥 [Скачать ${event.filename}](${window.location.origin}/api/chat/export/${event.export_id}) (${event.rows} строк)`
              );
              break;

            case "error":
              appendText(`\n\nОшибка: ${event.error}`);
              updateAssistant((m) => ({ ...m, isStreaming: false }));
              break;

            case "done":
              if (event.session_id) {
                sessionIdRef.current = event.session_id;
              }
              updateAssistant((m) => {
                const cleanedBlocks = m.blocks.filter(
                  (b) => b.type !== "progress"
                );
                const hasUsefulContent =
                  cleanedBlocks.some(
                    (b) => b.type === "text" && b.content.trim()
                  ) || cleanedBlocks.some((b) => b.type === "chart");
                const quickActions = hasUsefulContent
                  ? generateQuickActions(cleanedBlocks, columnHints)
                  : undefined;
                return {
                  ...m,
                  blocks: cleanedBlocks,
                  isStreaming: false,
                  quickActions,
                };
              });
              break;
          }
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }
        appendText(`\n\nОшибка подключения: ${err}`);
        updateAssistant((m) => ({ ...m, isStreaming: false }));
      } finally {
        abortRef.current = null;
        setIsStreaming(false);
      }
    },
    []
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    sessionIdRef.current = null;
  }, []);

  return { messages, isStreaming, sendMessage, clearMessages, setSessionId, abort };
}

export function generateQuickActions(blocks: MessageBlock[], columnHints?: { name: string; type: string }[]): string[] {
  const actions: string[] = [];
  const allText = blocks
    .filter((b): b is Extract<typeof b, { type: "text" }> => b.type === "text")
    .map((b) => b.content)
    .join(" ")
    .toLowerCase();
  const hasChart = blocks.some((b) => b.type === "chart");

  const hasDateCol = columnHints?.some((c) => /date|time|timestamp|datetime/i.test(c.type));
  const hasCatCol = columnHints?.some((c) => /varchar|text|char|enum|string/i.test(c.type));
  const hasNumCol = columnHints?.some((c) => /int|float|double|decimal|numeric|real/i.test(c.type));

  if (hasDateCol) {
    actions.push("📈 Показать тренд");
    actions.push("🔮 Спрогнозировать на 3 месяца");
  }
  if (hasNumCol) {
    actions.push("📊 Визуализировать графиком");
    actions.push("🔗 Найти корреляции");
  }
  if (hasCatCol) {
    actions.push("⊞ Кросс-табуляция");
    actions.push("🎯 Кластеризация");
  }
  if (/аномал|выброс|outlier/i.test(allText)) {
    actions.push("🧪 Статистический тест");
  }
  if (actions.length === 0) {
    actions.push("✨ Авто-инсайты");
    actions.push("✅ Качество данных");
  }
  if (!hasChart && !actions.some((a) => a.includes("Визуализи"))) {
    actions.push("📊 Визуализировать");
  }
  actions.push("📖 История данных");
  actions.push("📋 Создай публичный дашборд через create_public_dashboard");
  return actions.slice(0, 6);
}
