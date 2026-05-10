import { useState, useEffect } from "react";
import { X, Wifi, WifiOff, Loader2 } from "lucide-react";
import {
  getLLMSettings,
  updateLLMSettings,
  testLLMConnection,
} from "../../api/client";
import type { ConnectionTestResult } from "../../types";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function SettingsModal({ open, onClose }: Props) {
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [connectionStatus, setConnectionStatus] = useState<
    "idle" | "testing" | "connected" | "disconnected"
  >("idle");
  const [connectionError, setConnectionError] = useState("");
  const [saving, setSaving] = useState(false);
  const [availableModels, setAvailableModels] = useState<string[]>([]);

  useEffect(() => {
    if (open) {
      getLLMSettings()
        .then((s) => {
          setBaseUrl(s.llm_base_url);
          setApiKey(s.llm_api_key);
          setModel(s.llm_model);
        })
        .catch(() => {});
      setConnectionStatus("idle");
      setConnectionError("");
    }
  }, [open]);

  if (!open) return null;

  const handleTest = async () => {
    setConnectionStatus("testing");
    setConnectionError("");
    try {
      await updateLLMSettings({
        llm_base_url: baseUrl,
        llm_api_key: apiKey,
        llm_model: model,
      });
      const result: ConnectionTestResult = await testLLMConnection();
      if (result.connected) {
        setConnectionStatus("connected");
        if (result.models) {
          setAvailableModels(result.models);
        }
      } else {
        setConnectionStatus("disconnected");
        setConnectionError(result.error || "Не удалось подключиться");
      }
    } catch (e) {
      setConnectionStatus("disconnected");
      setConnectionError(String(e));
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateLLMSettings({
        llm_base_url: baseUrl,
        llm_api_key: apiKey,
        llm_model: model,
      });
      onClose();
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Подключение LLM</h2>
          <button className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          <div className="form-group">
            <label>Base URL</label>
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="http://localhost:11434/v1"
            />
            <span className="input-hint">
              OpenAI-совместимый API (Ollama, vLLM, OpenAI и др.)
            </span>
          </div>

          <div className="form-group">
            <label>API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-... (оставьте пустым для локальных моделей)"
            />
            <span className="input-hint">
              Необязательно для локальных моделей (Ollama, LM Studio)
            </span>
          </div>

          <div className="form-group">
            <label>Модель</label>
            {availableModels.length > 0 ? (
              <>
                <input
                  type="text"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="qwen2.5:14b"
                  list="model-list"
                />
                <datalist id="model-list">
                  {availableModels.map((m) => (
                    <option key={m} value={m} />
                  ))}
                </datalist>
              </>
            ) : (
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="qwen2.5:14b"
              />
            )}
            <span className="input-hint">
              Имя модели, распознаваемое вашим LLM-провайдером
            </span>
          </div>

          {connectionStatus !== "idle" && (
            <div
              className={`connection-status ${
                connectionStatus === "connected"
                  ? "connected"
                  : connectionStatus === "disconnected"
                  ? "disconnected"
                  : "testing"
              }`}
            >
              {connectionStatus === "testing" && (
                <>
                  <Loader2 size={16} className="spin" />
                  Проверка подключения...
                </>
              )}
              {connectionStatus === "connected" && (
                <>
                  <Wifi size={16} />
                  Подключено{" "}
                  {availableModels.length > 0 &&
                    `(${availableModels.length} моделей)`}
                </>
              )}
              {connectionStatus === "disconnected" && (
                <>
                  <WifiOff size={16} />
                  {connectionError || "Не удалось подключиться"}
                </>
              )}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={handleTest}>
            Проверить
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? "Сохранение..." : "Сохранить"}
          </button>
        </div>
      </div>
    </div>
  );
}
