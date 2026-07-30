import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Sidebar } from "../components/Layout/Sidebar";

vi.mock("../api/client", () => ({
  listDBConnections: vi.fn().mockResolvedValue([]),
  listDashboards: vi.fn().mockResolvedValue([]),
  attachDBConnection: vi.fn(),
  deleteDBConnection: vi.fn(),
  deleteDashboard: vi.fn(),
  listConnectionModes: vi.fn().mockResolvedValue({ modes: ["auto", "remote", "dump", "federated"], db_types: ["postgresql"] }),
}));

import * as api from "../api/client";
import type { FileInfo } from "../types";

const baseProps = {
  files: [] as FileInfo[],
  onRemove: vi.fn(),
  onClearChat: vi.fn(),
  onOpenSettings: vi.fn(),
  onPreviewFile: vi.fn(),
  onExportPDF: vi.fn(),
  hasMessages: false,
  dark: false,
  onToggleTheme: vi.fn(),
  queryHistory: [],
  onHistorySelect: vi.fn(),
  onHistoryClear: vi.fn(),
  onLogout: vi.fn(),
  userName: "test-user",
};

describe("Sidebar new tabs", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all 7 tab buttons", () => {
    render(<Sidebar {...baseProps} />);
    expect(screen.getByText("Файлы")).toBeInTheDocument();
    expect(screen.getByText("История")).toBeInTheDocument();
    expect(screen.getByText("БД")).toBeInTheDocument();
    expect(screen.getByText("Дашборды")).toBeInTheDocument();
    expect(screen.getByText("База")).toBeInTheDocument();
    expect(screen.getByText("Логи")).toBeInTheDocument();
  });

  it("renders BI Link Builder button in footer", () => {
    render(<Sidebar {...baseProps} />);
    expect(screen.getByText("BI Link Builder")).toBeInTheDocument();
  });

  it("opens BI Link modal on button click", () => {
    render(<Sidebar {...baseProps} />);
    // кнопка в футере
    const footerBtn = document.querySelector(".sidebar-footer .export-pdf-btn")!;
    fireEvent.click(footerBtn);
    // модалка открылась — есть input с placeholder
    expect(screen.getByPlaceholderText("https://superset.company.com")).toBeInTheDocument();
  });

  it("switches to Knowledge tab on click", async () => {
    render(<Sidebar {...baseProps} />);
    // клик по вкладке "База"
    const tabs = screen.getAllByText("База");
    fireEvent.click(tabs[0]);
    await waitFor(() => {
      expect(screen.getByText("База знаний")).toBeInTheDocument();
    });
  });

  it("switches to Logs tab on click", async () => {
    render(<Sidebar {...baseProps} />);
    // "Логи" встречается дважды: вкладка + заголовок внутри вкладки после клика.
    // Кликнем по первой (вкладке)
    const logsTabs = screen.getAllByText("Логи");
    fireEvent.click(logsTabs[0]);
    await waitFor(() => {
      expect(screen.getByText("Запросы")).toBeInTheDocument();
      expect(screen.getByText("Ошибки")).toBeInTheDocument();
      expect(screen.getByText("Аудит")).toBeInTheDocument();
    });
  });

  it("switches to Databases tab and shows mode selector", async () => {
    render(<Sidebar {...baseProps} />);
    fireEvent.click(screen.getByText("БД"));
    await waitFor(() => {
      expect(screen.getByText("Режим:")).toBeInTheDocument();
      // 4 опции режима
      const select = document.querySelector("select")!;
      expect(select).toBeInTheDocument();
    });
  });

  it("shows brand name and user", () => {
    render(<Sidebar {...baseProps} />);
    expect(screen.getByText("DataSearcher")).toBeInTheDocument();
    expect(screen.getByText("test-user")).toBeInTheDocument();
  });

  it("shows theme toggle button", () => {
    render(<Sidebar {...baseProps} />);
    expect(baseProps.onToggleTheme).toHaveBeenCalledTimes(0);
    const themeBtn = document.querySelector(".theme-toggle")!;
    fireEvent.click(themeBtn);
    expect(baseProps.onToggleTheme).toHaveBeenCalledTimes(1);
  });
});