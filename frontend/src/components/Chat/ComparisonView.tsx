import { useState } from "react";
import { X, Columns2 } from "lucide-react";
import type { ChatMessage } from "../../types";
import { MessageBubble } from "./MessageBubble";

interface Props {
  left: ChatMessage[];
  right: ChatMessage[];
  onClose: () => void;
  onAction?: (action: string) => void;
}

export function ComparisonView({ left, right, onClose, onAction }: Props) {
  const [activeTab, setActiveTab] = useState<"left" | "right">("left");

  return (
    <div className="comparison-view">
      <div className="comparison-header">
        <div className="comparison-tabs">
          <button
            className={`comparison-tab ${activeTab === "left" ? "active" : ""}`}
            onClick={() => setActiveTab("left")}
          >
            <Columns2 size={13} /> Анализ A
          </button>
          <button
            className={`comparison-tab ${activeTab === "right" ? "active" : ""}`}
            onClick={() => setActiveTab("right")}
          >
            <Columns2 size={13} /> Анализ B
          </button>
        </div>
        <button className="comparison-close" onClick={onClose}>
          <X size={16} />
        </button>
      </div>
      <div className="comparison-body">
        <div className={`comparison-panel ${activeTab === "left" ? "visible" : ""}`}>
          {left.map((msg) => (
            <MessageBubble key={msg.id} message={msg} onAction={onAction} />
          ))}
        </div>
        <div className={`comparison-panel ${activeTab === "right" ? "visible" : ""}`}>
          {right.map((msg) => (
            <MessageBubble key={msg.id} message={msg} onAction={onAction} />
          ))}
        </div>
      </div>
    </div>
  );
}
