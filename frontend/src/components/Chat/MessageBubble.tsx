import type { ChatMessage } from "../../types";
import { MessageBlocks } from "./MessageBlocks";

interface Props {
  message: ChatMessage;
  onAction?: (action: string) => void;
}

export function MessageBubble({ message, onAction }: Props) {
  const isUser = message.role === "user";

  if (isUser) {
    const textContent = message.blocks
      .filter((b): b is Extract<typeof b, { type: "text" }> => b.type === "text")
      .map((b) => b.content)
      .join("");
    return (
      <div className="message user">
        <div className="message-avatar">Вы</div>
        <div className="message-body">
          <div className="message-content"><span>{textContent}</span></div>
        </div>
      </div>
    );
  }

  return (
    <div className="message assistant">
      <div className="message-avatar">DS</div>
      <div className="message-body">
        <MessageBlocks
          message={message.blocks}
          isUser={false}
          isStreaming={message.isStreaming}
          isStopped={message.isStopped}
        />
        {message.quickActions && message.quickActions.length > 0 && !message.isStreaming && onAction && (
          <div className="quick-actions">
            {message.quickActions.map((action, i) => (
              <button key={i} className="quick-action-btn" onClick={() => onAction(action)}>
                {action}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
