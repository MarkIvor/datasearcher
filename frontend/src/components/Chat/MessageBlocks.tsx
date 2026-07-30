import { useMemo } from "react";
import type { MessageBlock } from "../../types";
import { ChartBlock } from "./ChartBlock";
import { AnalysisProgress } from "./AnalysisProgress";
import { InteractiveTable } from "./InteractiveTable";
import { ErrorBoundary } from "../ErrorBoundary";
import { parseMarkdownTables } from "../../utils/parseTables";
import { LayoutDashboard, ExternalLink, Lock, Copy, Check } from "lucide-react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useState } from "react";

interface Props {
  message: MessageBlock[];
  isUser: boolean;
  isStreaming?: boolean;
  isStopped?: boolean;
}

function SmartContent({ content }: { content: string }) {
  const segments = useMemo(() => parseMarkdownTables(content), [content]);

  if (segments.length === 1 && segments[0].type === "markdown") {
    return (
      <div className="message-content">
        <Markdown remarkPlugins={[remarkGfm]}>{content}</Markdown>
      </div>
    );
  }

  return (
    <div className="message-content">
      {segments.map((seg, i) =>
        seg.type === "table" && seg.headers && seg.rows ? (
          <ErrorBoundary key={`tbl-${i}`}>
            <InteractiveTable headers={seg.headers} rows={seg.rows} />
          </ErrorBoundary>
        ) : seg.content ? (
          <Markdown key={`md-${i}`} remarkPlugins={[remarkGfm]}>{seg.content}</Markdown>
        ) : null
      )}
    </div>
  );
}

function DashboardCardBlock({ slug, title, url, hasPassword }: { slug: string; title: string; url: string; hasPassword: boolean }) {
  const [copied, setCopied] = useState(false);
  const dashUrl = url || `${window.location.origin}/d/${slug}`;

  const handleCopy = () => {
    navigator.clipboard.writeText(dashUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="dash-chat-card">
      <div className="dash-chat-card-icon"><LayoutDashboard size={20} /></div>
      <div className="dash-chat-card-info">
        <div className="dash-chat-card-title">{title}</div>
        <div className="dash-chat-card-meta">
          {hasPassword && <><Lock size={11} /> Защищён паролем ·</>}
          Публичная ссылка
        </div>
      </div>
      <div className="dash-chat-card-url">
        <code>{dashUrl}</code>
        <button className="dash-chat-copy" onClick={handleCopy}>
          {copied ? <Check size={12} /> : <Copy size={12} />}
        </button>
      </div>
      <a href={`/d/${slug}`} target="_blank" rel="noopener" className="dash-chat-open">
        Открыть <ExternalLink size={12} />
      </a>
    </div>
  );
}

function ThinkingDots() {
  return (
    <div className="thinking-dots">
      <span />
      <span />
      <span />
    </div>
  );
}

export function MessageBlocks({ message: blocks, isUser, isStreaming, isStopped }: Props) {
  const hasContent = blocks.some((b) => b.type === "text" && b.content.trim());
  const isEmpty = blocks.length === 0;

  return (
    <>
      {isEmpty && isStreaming && <ThinkingDots />}
      {blocks.map((block, i) => {
        if (block.type === "text" && block.content) {
          if (isUser) {
            return (
              <div key={`t-${i}`} className="message-content">
                <span>{block.content}</span>
              </div>
            );
          }
          return <SmartContent key={`t-${i}`} content={block.content} />;
        }
        if (block.type === "chart") {
          return (
            <ErrorBoundary key={`ch-${i}`}>
              <ChartBlock spec={block.spec} />
            </ErrorBoundary>
          );
        }
        if (block.type === "dashboard") {
          return <DashboardCardBlock key={`dash-${i}`} slug={block.slug} title={block.title} url={block.url} hasPassword={block.has_password} />;
        }
        if (block.type === "progress") {
          return <AnalysisProgress key={`p-${i}`} tools={block.tools} />;
        }
        return null;
      })}
      {isStreaming && hasContent && <span className="cursor">|</span>}
      {isStopped && <div className="stopped-label">Остановлено</div>}
    </>
  );
}
