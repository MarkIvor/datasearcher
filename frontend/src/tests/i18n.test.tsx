import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { act } from "react";
import { LeftColumn } from "../components/Bento/LeftColumn";
import { ProfileCard } from "../components/Bento/ProfileCard";
import { setLang } from "../i18n";

vi.mock("../api/client", () => ({
  listDBConnections: vi.fn().mockResolvedValue([]),
  listDashboards: vi.fn().mockResolvedValue([]),
  attachDBConnection: vi.fn(),
  deleteDBConnection: vi.fn(),
  deleteDashboard: vi.fn(),
}));

import type { FileInfo } from "../types";

const sampleSetup = {
  completed: true,
  mode: "interface",
  step: 4,
  steps_total: 4,
  scope: "user" as const,
  is_admin: true,
  llm: { url: "", model: "", api_key_masked: "", has_key: false },
  enterprise: {
    read_only: true, pii_masking: true, rate_limit_enabled: true,
    log_enabled: true, default_mode: "auto", auto_translate: true,
  },
  connections_count: 0,
};

const baseProps = {
  files: [] as FileInfo[],
  onRemove: vi.fn(),
  onClearChat: vi.fn(),
  onOpenSettings: vi.fn(),
  onPreviewFile: vi.fn(),
  onExportPDF: vi.fn(),
  hasMessages: false,
  queryHistory: [],
  onHistorySelect: vi.fn(),
  onHistoryClear: vi.fn(),
  onLogout: vi.fn(),
  userName: "test-user",
  userRole: "analyst",
  onSendMessage: vi.fn(),
  onFilesChanged: vi.fn(),
  setup: sampleSetup,
  onOpenSetup: vi.fn(),
};

describe("i18n language switching", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setLang("ru");
  });

  it("renders Russian by default", () => {
    render(<LeftColumn {...baseProps} />);
    expect(screen.getByText("Файлы")).toBeInTheDocument();
    expect(screen.getByText("История")).toBeInTheDocument();
    expect(screen.getByText("Сессии")).toBeInTheDocument();
  });

  it("renders English after switching language", () => {
    act(() => setLang("en"));
    render(<LeftColumn {...baseProps} />);
    expect(screen.getByText("Files")).toBeInTheDocument();
    expect(screen.getByText("History")).toBeInTheDocument();
    expect(screen.getByText("Sessions")).toBeInTheDocument();
  });

  it("profile card shows localized setup progress (en)", () => {
    const incomplete = { ...sampleSetup, completed: false, step: 2, steps_total: 4 };
    act(() => setLang("en"));
    render(<ProfileCard userName="John" role="admin" setup={incomplete} />);
    expect(screen.getByText("Step 2 of 4")).toBeInTheDocument();
  });

  it("profile card shows localized setup progress (ru)", () => {
    const incomplete = { ...sampleSetup, completed: false, step: 2, steps_total: 4 };
    act(() => setLang("ru"));
    render(<ProfileCard userName="Иван" role="admin" setup={incomplete} />);
    expect(screen.getByText("Step 2 of 4")).toBeInTheDocument();
  });

  it("toggle language re-renders chips", () => {
    act(() => setLang("ru"));
    render(<LeftColumn {...baseProps} />);
    expect(screen.getByText("Файлы")).toBeInTheDocument();
    act(() => setLang("en"));
    expect(screen.getByText("Files")).toBeInTheDocument();
  });
});
