import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { LeftColumn } from "../components/Bento/LeftColumn";

vi.mock("../api/client", () => ({
  listDBConnections: vi.fn().mockResolvedValue([]),
  listDashboards: vi.fn().mockResolvedValue([]),
  attachDBConnection: vi.fn(),
  deleteDBConnection: vi.fn(),
  deleteDashboard: vi.fn(),
  listConnectionModes: vi.fn().mockResolvedValue({ modes: ["auto", "remote", "dump", "federated"], db_types: ["postgresql"] }),
  getSetup: vi.fn().mockResolvedValue({
    completed: true,
    mode: "interface",
    step: 4,
    steps_total: 4,
    scope: "user",
    is_admin: true,
    llm: { url: "", model: "", api_key_masked: "", has_key: false },
    enterprise: {
      read_only: true, pii_masking: true, rate_limit_enabled: true,
      log_enabled: true, default_mode: "auto", auto_translate: true,
    },
    connections_count: 0,
  }),
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

describe("LeftColumn (Bento session list)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders session chips", () => {
    render(<LeftColumn {...baseProps} />);
    expect(screen.getByText("Файлы")).toBeInTheDocument();
    expect(screen.getByText("История")).toBeInTheDocument();
    expect(screen.getByText("БД")).toBeInTheDocument();
    expect(screen.getByText("Дашборды")).toBeInTheDocument();
    expect(screen.getByText("База")).toBeInTheDocument();
    expect(screen.getByText("Логи")).toBeInTheDocument();
  });

  it("renders profile card with brand and user", () => {
    render(<LeftColumn {...baseProps} />);
    expect(screen.getByText("DataSearcher")).toBeInTheDocument();
    expect(screen.getByTitle("test-user")).toBeInTheDocument();
    expect(screen.getByText("Настройка завершена")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("renders BI Link Builder button in footer", () => {
    render(<LeftColumn {...baseProps} />);
    expect(screen.getByText("BI Link Builder")).toBeInTheDocument();
  });

  it("opens BI Link modal on button click", () => {
    render(<LeftColumn {...baseProps} />);
    fireEvent.click(screen.getByText("BI Link Builder"));
    expect(screen.getByPlaceholderText("https://superset.company.com")).toBeInTheDocument();
  });

  it("switches to Knowledge tab on click", async () => {
    render(<LeftColumn {...baseProps} />);
    fireEvent.click(screen.getByText("База"));
    await waitFor(() => {
      expect(screen.getByText("База знаний")).toBeInTheDocument();
    });
  });

  it("switches to Logs tab on click", async () => {
    render(<LeftColumn {...baseProps} />);
    fireEvent.click(screen.getByText("Логи"));
    await waitFor(() => {
      expect(screen.getByText("Запросы")).toBeInTheDocument();
      expect(screen.getByText("Ошибки")).toBeInTheDocument();
      expect(screen.getByText("Аудит")).toBeInTheDocument();
    });
  });

  it("switches to Databases tab and shows mode chips", async () => {
    render(<LeftColumn {...baseProps} />);
    fireEvent.click(screen.getByText("БД"));
    await waitFor(() => {
      expect(screen.getByText("Режим: auto")).toBeInTheDocument();
      expect(screen.getByText("remote")).toBeInTheDocument();
      expect(screen.getByText("federated")).toBeInTheDocument();
    });
  });

  it("shows empty files hint when no files", () => {
    render(<LeftColumn {...baseProps} />);
    expect(screen.getByText(/Нет загруженных файлов/i)).toBeInTheDocument();
  });

  it("shows active file item when files exist", () => {
    const files: FileInfo[] = [{
      file_id: "f1",
      table_name: "sales",
      file_type: "csv",
      row_count: 120,
      columns: [{ name: "amount", type: "DOUBLE" }],
    }];
    render(<LeftColumn {...baseProps} files={files} />);
    expect(screen.getByText("sales")).toBeInTheDocument();
    expect(screen.getByText("Схема")).toBeInTheDocument();
  });

  it("admin panel button hidden for non-admin", () => {
    render(<LeftColumn {...baseProps} userRole="analyst" />);
    expect(screen.queryByText("Админ-панель")).not.toBeInTheDocument();
  });
});
