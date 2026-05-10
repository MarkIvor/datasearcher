import { useState, useCallback, useRef, useEffect } from "react";
import { useChat } from "./hooks/useChat";
import { useFiles } from "./hooks/useFiles";
import { useTheme } from "./hooks/useTheme";
import { useNotification } from "./hooks/useNotification";
import { useKeyboardShortcuts } from "./hooks/useKeyboardShortcuts";
import { useQueryHistory } from "./hooks/useQueryHistory";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { Sidebar } from "./components/Layout/Sidebar";
import { SettingsModal } from "./components/Layout/SettingsModal";
import { FilePreviewModal } from "./components/Layout/FilePreviewModal";
import { MessageInput, type MessageInputHandle } from "./components/Chat/MessageInput";
import { MessageList } from "./components/Chat/MessageList";
import { ComparisonView } from "./components/Chat/ComparisonView";
import { FileUpload } from "./components/Files/FileUpload";
import { StatusBar } from "./components/Layout/StatusBar";
import { AdminPanel } from "./components/Admin/AdminPanel";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import type { ChatMessage, FileInfo } from "./types/index";

const API_BASE = import.meta.env.VITE_API_URL || "";

function AppInner() {
  const { user, loading: authLoading, logout } = useAuth();
  const [authPage, setAuthPage] = useState<"login" | "register">("login");
  const [adminOpen, setAdminOpen] = useState(false);

  if (authLoading) {
    return <div className="auth-page"><div style={{ color: "var(--text-muted)", fontSize: 13 }}>Загрузка...</div></div>;
  }

  if (!user) {
    return authPage === "login"
      ? <LoginPage onSwitch={() => setAuthPage("register")} />
      : <RegisterPage onSwitch={() => setAuthPage("login")} />;
  }

  return <MainApp onLogout={logout} onAdmin={() => setAdminOpen(true)} adminOpen={adminOpen} onCloseAdmin={() => setAdminOpen(false)} />;
}

function MainApp({ onLogout, onAdmin, adminOpen, onCloseAdmin }: {
  onLogout: () => void;
  onAdmin: () => void;
  adminOpen: boolean;
  onCloseAdmin: () => void;
}) {
  const { dark, toggle: toggleTheme } = useTheme();
  const { requestPermission, notify, playSound } = useNotification();
  const { history, add: addHistory, clear: clearHistory } = useQueryHistory();
  const inputHandleRef = useRef<MessageInputHandle>(null);
  const sendMessageRef = useRef<(msg: string) => void>(() => {});
  const { user } = useAuth();

  const handleFirstFile = useCallback(
    (_info: FileInfo) => {
      setTimeout(() => sendMessageRef.current("Сделай краткий обзор структуры данных и построй дашборд с ключевыми метриками"), 300);
    },
    []
  );
  const { files, uploading, addFile, removeFile, refresh: refreshFiles } = useFiles(handleFirstFile);
  const columnHints = files.flatMap((f) => f.columns);
  const { messages, isStreaming, sendMessage, clearMessages, abort } = useChat(columnHints);
  sendMessageRef.current = sendMessage;

  const [settingsOpen, setSettingsOpen] = useState(false);
  const [previewFile, setPreviewFile] = useState<FileInfo | null>(null);
  const [comparison, setComparison] = useState<{ left: ChatMessage[]; right: ChatMessage[] } | null>(null);

  const prevStreamingRef = useRef(isStreaming);
  useEffect(() => {
    if (prevStreamingRef.current && !isStreaming && messages.length > 0) {
      playSound();
      const last = messages[messages.length - 1];
      if (last?.role === "assistant") {
        notify("DataSearcher", "Анализ завершён");
      }
    }
    prevStreamingRef.current = isStreaming;
  }, [isStreaming, messages, playSound, notify]);

  useEffect(() => { requestPermission(); }, [requestPermission]);

  const handleSend = useCallback((content: string) => { addHistory(content); sendMessage(content); }, [sendMessage, addHistory]);
  const handleFileUpload = async (file: File) => { const info = await addFile(file); return info; };
  const handleQuickAction = useCallback((action: string) => { addHistory(action); sendMessage(action); }, [sendMessage, addHistory]);
  const handleExportPDF = useCallback(async () => {
    try {
      const charts: { title: string; png_base64: string }[] = [];
      const chartElements = document.querySelectorAll(".chart-block");
      for (const el of chartElements) {
        const titleEl = el.querySelector(".chart-title");
        const title = titleEl?.textContent || "График";
        try {
          const { toPng } = await import("html-to-image");
          const dataUrl = await toPng(el as HTMLElement, { backgroundColor: "#ffffff", pixelRatio: 2 });
          const base64 = dataUrl.split(",")[1];
          if (base64) charts.push({ title, png_base64: base64 });
        } catch { /* skip chart */ }
      }
      const blob = await import("./api/client").then((m) => m.exportPDF(charts));
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "datasearcher_report.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      window.open(`${API_BASE}/api/chat/export-pdf`, "_blank");
    }
  }, []);
  const handleClearChat = useCallback(() => { clearMessages(); }, [clearMessages]);
  const handleHistorySelect = useCallback((query: string) => { addHistory(query); sendMessage(query); }, [sendMessage, addHistory]);
  const handleCompare = useCallback(() => {
    const mid = Math.ceil(messages.length / 2);
    setComparison({ left: messages.slice(0, mid), right: messages.slice(mid) });
  }, [messages]);

  useKeyboardShortcuts({
    onToggleTheme: toggleTheme,
    onExportPDF: handleExportPDF,
    onClear: handleClearChat,
    onFocusInput: () => inputHandleRef.current?.focus(),
  });

  return (
    <div className="app">
      <Sidebar
        files={files}
        onRemove={removeFile}
        onClearChat={handleClearChat}
        onOpenSettings={() => setSettingsOpen(true)}
        onPreviewFile={(f) => setPreviewFile(f)}
        onExportPDF={handleExportPDF}
        hasMessages={messages.length > 0}
        dark={dark}
        onToggleTheme={toggleTheme}
        queryHistory={history}
        onHistorySelect={handleHistorySelect}
        onHistoryClear={clearHistory}
        onCompare={messages.length >= 4 ? handleCompare : undefined}
        onLogout={onLogout}
        onAdmin={user?.role === "admin" ? onAdmin : undefined}
        userName={user?.display_name || user?.email || ""}
        userRole={user?.role}
        onSendMessage={handleSend}
        onFilesChanged={refreshFiles}
      />
      <main className="main">
        {files.length > 0 && (
          <div className="main-header">
            <FileUpload files={files} uploading={uploading} onUpload={handleFileUpload} onRemove={removeFile} />
          </div>
        )}
        <MessageList messages={messages} onAction={handleQuickAction} onFileUpload={handleFileUpload} uploading={uploading} hasFiles={files.length > 0} onFilesChanged={refreshFiles} />
        <MessageInput ref={inputHandleRef} onSend={handleSend} isStreaming={isStreaming} disabled={files.length === 0} onStop={abort} />
        <StatusBar files={files} />
      </main>
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      {previewFile && <FilePreviewModal file={previewFile} onClose={() => setPreviewFile(null)} />}
      {comparison && <ComparisonView left={comparison.left} right={comparison.right} onClose={() => setComparison(null)} onAction={handleQuickAction} />}
      {adminOpen && <AdminPanel onClose={onCloseAdmin} />}
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  );
}
