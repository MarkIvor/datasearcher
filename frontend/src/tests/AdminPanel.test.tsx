import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { AdminPanel } from "../components/Admin/AdminPanel";

vi.mock("../api/client", () => ({
  getAdminUsers: vi.fn().mockResolvedValue([]),
  getAdminSettings: vi.fn().mockResolvedValue({
    allow_registration: "true",
    allow_custom_llm: "true",
    allow_user_db_connections: "true",
  }),
  updateAdminSettings: vi.fn(),
  getEnterpriseSettings: vi.fn(),
  listDBConnections: vi.fn().mockResolvedValue([]),
  attachDBConnection: vi.fn(),
  deleteDBConnection: vi.fn(),
}));

import * as api from "../api/client";

const mockEntSettings = {
  read_only: true,
  pii_masking: true,
  pii_scan_rows: 10,
  rate_limit_enabled: true,
  rate_limit_sql: 60,
  rate_limit_ml: 10,
  default_mode: "auto",
  auto_translate: true,
  query_timeout: 60,
  log_enabled: true,
  blocked_table_patterns: "raw_*,stg_*,tmp_*",
  example_store_enabled: true,
  semantic_search_max_rows: 10000,
  datahub_url: "",
  dbt_manifest_path: "",
};

describe("AdminPanel enterprise tab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getEnterpriseSettings).mockResolvedValue(mockEntSettings);
  });

  it("renders 4 tabs including Безопасность", () => {
    render(<AdminPanel onClose={vi.fn()} />);
    expect(screen.getByText("Пользователи")).toBeInTheDocument();
    expect(screen.getByText("Настройки")).toBeInTheDocument();
    expect(screen.getByText("Базы данных")).toBeInTheDocument();
    expect(screen.getByText("Безопасность")).toBeInTheDocument();
  });

  it("shows enterprise settings on tab click", async () => {
    render(<AdminPanel onClose={vi.fn()} />);
    fireEvent.click(screen.getByText("Безопасность"));
    await waitFor(() => {
      expect(api.getEnterpriseSettings).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(screen.getByText(/Read-only guard/)).toBeInTheDocument();
      expect(screen.getByText(/PII-маскирование/)).toBeInTheDocument();
      expect(screen.getByText(/Rate limiting/)).toBeInTheDocument();
    });
  });

  it("shows all enterprise settings values", async () => {
    render(<AdminPanel onClose={vi.fn()} />);
    fireEvent.click(screen.getByText("Безопасность"));
    await waitFor(() => {
      // "вкл" встречается несколько раз (read_only, pii_masking, rate_limit, etc.)
      const onLabels = screen.getAllByText("вкл");
      expect(onLabels.length).toBeGreaterThanOrEqual(5);
      // 60 встречается для rate_limit_sql и query_timeout
      const sixties = screen.getAllByText("60");
      expect(sixties.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("auto")).toBeInTheDocument(); // default_mode
    });
  });

  it("shows note about env configuration", async () => {
    render(<AdminPanel onClose={vi.fn()} />);
    fireEvent.click(screen.getByText("Безопасность"));
    await waitFor(() => {
      expect(screen.getByText(/переменные окружения/i)).toBeInTheDocument();
    });
  });

  it("shows blocked patterns", async () => {
    render(<AdminPanel onClose={vi.fn()} />);
    fireEvent.click(screen.getByText("Безопасность"));
    await waitFor(() => {
      expect(screen.getByText(/raw_\*,stg_\*,tmp_\*/)).toBeInTheDocument();
    });
  });

  it("shows DataHub URL placeholder when empty", async () => {
    render(<AdminPanel onClose={vi.fn()} />);
    fireEvent.click(screen.getByText("Безопасность"));
    await waitFor(() => {
      // "—" встречается для пустых datahub_url и dbt_manifest_path
      const dashes = screen.getAllByText("—");
      expect(dashes.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("calls onClose when close button clicked", () => {
    const onClose = vi.fn();
    render(<AdminPanel onClose={onClose} />);
    fireEvent.click(document.querySelector(".admin-close")!);
    expect(onClose).toHaveBeenCalled();
  });

  it("handles API error gracefully", async () => {
    vi.mocked(api.getEnterpriseSettings).mockRejectedValue(new Error("Network"));
    render(<AdminPanel onClose={vi.fn()} />);
    fireEvent.click(screen.getByText("Безопасность"));
    await waitFor(() => {
      expect(screen.getByText(/Не удалось загрузить/i)).toBeInTheDocument();
    });
  });

  it("shows DataHub URL when configured", async () => {
    vi.mocked(api.getEnterpriseSettings).mockResolvedValue({
      ...mockEntSettings,
      datahub_url: "https://datahub.company.com",
      dbt_manifest_path: "/path/to/manifest.json",
    });
    render(<AdminPanel onClose={vi.fn()} />);
    fireEvent.click(screen.getByText("Безопасность"));
    await waitFor(() => {
      expect(screen.getByText("https://datahub.company.com")).toBeInTheDocument();
      expect(screen.getByText("/path/to/manifest.json")).toBeInTheDocument();
    });
  });
});