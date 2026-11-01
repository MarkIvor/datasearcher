import { useState, useCallback, useRef, useEffect } from "react";
import { useChat } from "./hooks/useChat";
import { useFiles } from "./hooks/useFiles";
import { useNotification } from "./hooks/useNotification";
import { useKeyboardShortcuts } from "./hooks/useKeyboardShortcuts";
import { useQueryHistory } from "./hooks/useQueryHistory";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { LeftColumn } from "./components/Bento/LeftColumn";
import { RightColumn } from "./components/Bento/RightColumn";
import { ChatStream } from "./components/Chat/ChatStream";
import { ChatInputBar, type MessageInputHandle } from "./components/Chat/ChatInputBar";
import { ComparisonView } from "./components/Chat/ComparisonView";
import { FileUpload } from "./components/Files/FileUpload";
import { StatusBar } from "./components/Layout/StatusBar";
import { AdminPanel } from "./components/Admin/AdminPanel";
import { SettingsModal } from "./components/Layout/SettingsModal";
import { FilePreviewModal } from "./components/Layout/FilePreviewModal";
import { SetupWizard } from "./components/Setup/SetupWizard";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import * as api from "./api/client";
import type { SetupState } from "./api/client";
import type { ChatMessage, FileInfo } from "./types/index";
import { useI18n } from "./i18n";

const API_BASE = import.meta.env.VITE_API_URL || "";

function AppInner() {
  const { t } = useI18n();
  const { user, loading: authLoading, logout } = useAuth();
  const [authPage, setAuthPage] = useState<"login" | "register">("login");
  const [adminOpen, setAdminOpen] = useState(false);

  const [setup, setSetup] = useState<SetupState | null>(null);
  const [setupChecked, setSetupChecked] = useState(false);
  const [showWizard, setShowWizard] = useState(false);

  useEffect(() => {
    if (!user) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSetup(null);
      setSetupChecked(false);
      return;
    }
    api.getSetup()
      .then((s) => {
        setSetup(s);
        setShowWizard(!s.completed);
      })
      .catch(() => {})
      .finally(() => setSetupChecked(true));
  }, [user]);

  if (authLoading) {
    return (
      <div className="auth-shell">
        <div style={{ color: "var(--text-muted-light)", fontSize: 13, fontWeight: 600 }}>
          {t("common.loading")}
        </div>
      </div>
    );
  }

  if (!user) {
    return authPage === "login"
      ? <LoginPage onSwitch={() => setAuthPage("register")} />
      : <RegisterPage onSwitch={() => setAuthPage("login")} />;
  }

  if (!setupChecked) {
    return (
      <div className="auth-shell">
        <div style={{ color: "var(--text-muted-light)", fontSize: 13, fontWeight: 600 }}>
          {t("common.loading")}
        </div>
      </div>
    );
  }

  if (showWizard) {
    return (
      <SetupWizard
        onComplete={(s) => {
          setSetup(s);
          setShowWizard(false);
        }}
      />
    );
  }

  return (
    <MainApp
      key="main"
      onLogout={logout}
      onAdmin={() => setAdminOpen(true)}
      adminOpen={adminOpen}
      onCloseAdmin={() => setAdminOpen(false)}
      setup={setup}
      onOpenSetup={() => setShowWizard(true)}
    />
  );
}

interface MainAppProps {
  onLogout: () => void;
  onAdmin: () => void;
  adminOpen: boolean;
  onCloseAdmin: () => void;
  setup: SetupState | null;
  onOpenSetup: () => void;
}

function MainApp({ onLogout, onAdmin, adminOpen, onCloseAdmin, setup, onOpenSetup }: MainAppProps) {
  const { t } = useI18n();
  const { notify, playSound } = useNotification();
  const { history, add: addHistory, clear: clearHistory } = useQueryHistory();
  const inputHandleRef = useRef<MessageInputHandle>(null);
  const attachInputRef = useRef<HTMLInputElement>(null);
  const sendMessageRef = useRef<(msg: string) => void>(() => {});
  const { user } = useAuth();

  const handleFirstFile = useCallback(
    () => {
      setTimeout(() => sendMessageRef.current(t("chat.autoMessage")), 300);
    },
    [t]
  );
  const { files, uploading, addFile, removeFile, refresh: refreshFiles } = useFiles(handleFirstFile);
  const columnHints = files.flatMap((f) => f.columns);
  const { messages, isStreaming, sendMessage, clearMessages, abort } = useChat(columnHints);

  useEffect(() => {
    sendMessageRef.current = sendMessage;
  }, [sendMessage]);

  const [settingsOpen, setSettingsOpen] = useState(false);
  const [previewFile, setPreviewFile] = useState<FileInfo | null>(null);
  const [comparison, setComparison] = useState<{ left: ChatMessage[]; right: ChatMessage[] } | null>(null);

  const prevStreamingRef = useRef(isStreaming);
  useEffect(() => {
    if (prevStreamingRef.current && !isStreaming && messages.length > 0) {
      playSound();
      const last = messages[messages.length - 1];
      if (last?.role === "assistant") {
        notify("DataSearcher", t("notify.done"));
      }
    }
    prevStreamingRef.current = isStreaming;
  }, [isStreaming, messages, playSound, notify]);

  const handleSend = useCallback((content: string) => { addHistory(content); sendMessage(content); }, [sendMessage, addHistory]);
  const handleFileUpload = async (file: File) => { const info = await addFile(file); return info; };
  const handleQuickAction = useCallback((action: string) => { addHistory(action); sendMessage(action); }, [sendMessage, addHistory]);
  const handleExportPDF = useCallback(async () => {
    try {
      const charts: { title: string; png_base64: string }[] = [];
      const chartElements = document.querySelectorAll(".chart-block");
      for (const el of chartElements) {
        const titleEl = el.querySelector(".chart-title");
        const title = titleEl?.textContent || t("chart.chart");
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
  const handleAttach = useCallback(() => { attachInputRef.current?.click(); }, []);
  const handleAttachFile = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) await addFile(file);
    if (attachInputRef.current) attachInputRef.current.value = "";
  }, [addFile]);

  useKeyboardShortcuts({
    onExportPDF: handleExportPDF,
    onClear: handleClearChat,
    onFocusInput: () => inputHandleRef.current?.focus(),
  });

  return (
    <div className="app-shell">
      <div className="bento-grid">
        <LeftColumn
          files={files}
          onRemove={removeFile}
          onClearChat={handleClearChat}
          onOpenSettings={() => setSettingsOpen(true)}
          onPreviewFile={(f) => setPreviewFile(f)}
          onExportPDF={handleExportPDF}
          hasMessages={messages.length > 0}
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
          setup={setup}
          onOpenSetup={onOpenSetup}
        />

        <section className="bento-col">
          <div className="bento-canvas">
            <header className="canvas-header">
              <span className="canvas-title">{t("chat.canvasTitle")}</span>
              <span className="canvas-status">
                <span className={`live-dot ${isStreaming ? "" : "idle"}`} />
                {isStreaming ? t("chat.statusStreaming") : files.length > 0 ? t("chat.statusTables", { n: files.length }) : t("chat.statusWaiting")}
              </span>
            </header>

            {files.length > 0 && (
              <div className="file-upload-panel">
                <FileUpload files={files} uploading={uploading} onUpload={handleFileUpload} onRemove={removeFile} />
              </div>
            )}

            <ChatStream
              messages={messages}
              onAction={handleQuickAction}
              onFileUpload={handleFileUpload}
              uploading={uploading}
              hasFiles={files.length > 0}
              onFilesChanged={refreshFiles}
            />

            <ChatInputBar
              ref={inputHandleRef}
              onSend={handleSend}
              isStreaming={isStreaming}
              onStop={abort}
              onAttach={handleAttach}
            />

            <StatusBar files={files} />
          </div>
        </section>

        <RightColumn
          files={files}
          setup={setup}
          isStreaming={isStreaming}
          onAction={handleQuickAction}
        />
      </div>

      <input ref={attachInputRef} type="file" accept=".xlsx,.xls,.csv,.parquet" onChange={handleAttachFile} hidden />

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
