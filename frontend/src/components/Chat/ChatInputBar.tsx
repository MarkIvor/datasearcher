import { useState, useRef, useEffect, useImperativeHandle, forwardRef, type KeyboardEvent } from "react";
import { ArrowUp, Paperclip, Square } from "lucide-react";

interface Props {
  onSend: (message: string) => void;
  isStreaming: boolean;
  disabled?: boolean;
  onStop?: () => void;
  onAttach?: () => void;
}

export interface MessageInputHandle {
  focus: () => void;
}

export const ChatInputBar = forwardRef<MessageInputHandle, Props>(
  function ChatInputBar({ onSend, isStreaming, disabled, onStop, onAttach }, ref) {
    const [text, setText] = useState("");
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    useImperativeHandle(ref, () => ({
      focus: () => textareaRef.current?.focus(),
    }));

    useEffect(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
        textareaRef.current.style.height =
          Math.min(textareaRef.current.scrollHeight, 160) + "px";
      }
    }, [text]);

    const handleSend = () => {
      const trimmed = text.trim();
      if (!trimmed || isStreaming) return;
      onSend(trimmed);
      setText("");
      if (textareaRef.current) textareaRef.current.style.height = "auto";
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    };

    return (
      <div className="input-bar">
        <div className="input-bar-row">
          <div className="input-pill">
            <button className="input-plus-btn" onClick={onAttach} title="Загрузить файл" disabled={disabled}>
              <Paperclip size={15} />
            </button>
            <textarea
              ref={textareaRef}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                disabled
                  ? "Загрузите файл или пройдите настройку для начала анализа..."
                  : "Опишите, что нужно проанализировать..."
              }
              rows={1}
              disabled={disabled}
            />
          </div>
          <button
            className="send-btn"
            onClick={isStreaming ? onStop : handleSend}
            disabled={!isStreaming && (!text.trim() || disabled)}
            title={isStreaming ? "Остановить" : "Отправить"}
          >
            {isStreaming ? <Square size={16} /> : <ArrowUp size={18} strokeWidth={2.5} />}
          </button>
        </div>
      </div>
    );
  }
);
