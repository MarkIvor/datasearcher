import { useState, useRef, useEffect, useImperativeHandle, forwardRef, type KeyboardEvent } from "react";
import { Send, Square } from "lucide-react";

interface Props {
  onSend: (message: string) => void;
  isStreaming: boolean;
  disabled?: boolean;
  onStop?: () => void;
}

export interface MessageInputHandle {
  focus: () => void;
}

export const MessageInput = forwardRef<MessageInputHandle, Props>(
  function MessageInput({ onSend, isStreaming, disabled, onStop }, ref) {
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
      <div className="message-input">
        <div className="message-input-inner">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              disabled
                ? "Загрузите файл для начала анализа..."
                : "Опишите, что нужно проанализировать..."
            }
            rows={1}
            disabled={disabled}
          />
          <button
            className="send-btn"
            onClick={isStreaming ? onStop : handleSend}
            disabled={!isStreaming && (!text.trim() || disabled)}
          >
            {isStreaming ? <Square size={18} /> : <Send size={18} />}
          </button>
        </div>
      </div>
    );
  }
);
