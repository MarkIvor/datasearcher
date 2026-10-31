import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { LogsTab } from "../components/Layout/LogsTab";

vi.mock("../api/client", () => ({
  getQueryLogs: vi.fn(),
  getErrorLogs: vi.fn(),
  getAuditLogs: vi.fn(),
}));

import * as api from "../api/client";

const mockQueryLogs = [
  { id: 1, timestamp: "2024-01-01T12:00:00", tool: "sql_query", sql: "SELECT 1", table_name: "t", connection: "pg", rows_returned: 5, duration_ms: 12, success: 1, error: "", user: "" },
  { id: 2, timestamp: "2024-01-01T12:01:00", tool: "profile_data", sql: "", table_name: "t", connection: "", rows_returned: 0, duration_ms: 100, success: 0, error: "timeout", user: "" },
];

const mockErrorLogs = [
  { id: 1, timestamp: "2024-01-01T12:00:00", error_type: "SQL", message: "syntax error near FROM", sql: "SELECT", connection: "pg", stack: "", tool: "sql_query" },
];

const mockAuditLogs = [
  { id: 1, timestamp: "2024-01-01T12:00:00", action: "attach_database", target: "pg1", details: "{}" },
];

describe("LogsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getQueryLogs).mockResolvedValue(mockQueryLogs);
    vi.mocked(api.getErrorLogs).mockResolvedValue(mockErrorLogs);
    vi.mocked(api.getAuditLogs).mockResolvedValue(mockAuditLogs);
  });

  it("renders title and three tabs", () => {
    render(<LogsTab />);
    expect(screen.getByText("Логи")).toBeInTheDocument();
    expect(screen.getByText("Запросы")).toBeInTheDocument();
    expect(screen.getByText("Ошибки")).toBeInTheDocument();
    expect(screen.getByText("Аудит")).toBeInTheDocument();
  });

  it("loads query logs on mount", async () => {
    render(<LogsTab />);
    await waitFor(() => {
      expect(api.getQueryLogs).toHaveBeenCalledWith(50);
    });
    await waitFor(() => {
      expect(screen.getByText("sql_query")).toBeInTheDocument();
      expect(screen.getByText("profile_data")).toBeInTheDocument();
    });
  });

  it("shows duration and status for query logs", async () => {
    render(<LogsTab />);
    await waitFor(() => {
      expect(screen.getByText(/12ms/)).toBeInTheDocument();
      expect(screen.getByText(/100ms/)).toBeInTheDocument();
    });
  });

  it("shows error message in failed query log", async () => {
    render(<LogsTab />);
    await waitFor(() => {
      expect(screen.getByText(/timeout/)).toBeInTheDocument();
    });
  });

  it("switches to error logs tab", async () => {
    render(<LogsTab />);
    await waitFor(() => expect(api.getQueryLogs).toHaveBeenCalled());

    // Клик на Ошибки
    const errorTab = screen.getByText("Ошибки").closest("button")!;
    errorTab.click();

    await waitFor(() => {
      expect(api.getErrorLogs).toHaveBeenCalledWith(50);
      expect(screen.getByText("syntax error near FROM")).toBeInTheDocument();
    });
  });

  it("switches to audit logs tab", async () => {
    render(<LogsTab />);
    await waitFor(() => expect(api.getQueryLogs).toHaveBeenCalled());

    const auditTab = screen.getByText("Аудит").closest("button")!;
    auditTab.click();

    await waitFor(() => {
      expect(api.getAuditLogs).toHaveBeenCalledWith(50);
      expect(screen.getByText("attach_database")).toBeInTheDocument();
    });
  });

  it("shows empty state for query logs", async () => {
    vi.mocked(api.getQueryLogs).mockResolvedValue([]);
    render(<LogsTab />);
    await waitFor(() => {
      expect(screen.getByText("Лог запросов пуст")).toBeInTheDocument();
    });
  });

  it("shows empty state for error logs", async () => {
    vi.mocked(api.getErrorLogs).mockResolvedValue([]);
    render(<LogsTab />);
    const errorTab = screen.getByText("Ошибки").closest("button")!;
    errorTab.click();
    await waitFor(() => {
      expect(screen.getByText("Лог ошибок пуст")).toBeInTheDocument();
    });
  });
});