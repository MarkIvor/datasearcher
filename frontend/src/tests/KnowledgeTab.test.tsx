import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { KnowledgeTab } from "../components/Layout/KnowledgeTab";

// Мокаем api-модуль
vi.mock("../api/client", () => ({
  listKBTables: vi.fn(),
  listMetrics: vi.fn(),
  searchKnowledge: vi.fn(),
  uploadDbtManifest: vi.fn(),
  syncDataHub: vi.fn(),
  upsertMetric: vi.fn(),
  deleteMetric: vi.fn(),
}));

import * as api from "../api/client";

const mockTables = [
  { table_name: "users", connection: "pg1", description: "Пользователи", owner: "Ivan", layer: "mart", tags: ["prod"], is_certified: 1, source: "dbt" },
  { table_name: "orders", connection: "pg1", description: "", owner: "", layer: "staging", tags: [], is_certified: 0, source: "schema" },
];

const mockMetrics = [
  { name: "revenue", formula: "SUM(amount)", description: "выручка", owner: "CFO" },
];

describe("KnowledgeTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listKBTables).mockResolvedValue(mockTables);
    vi.mocked(api.listMetrics).mockResolvedValue(mockMetrics);
  });

  it("renders title and loads tables", async () => {
    render(<KnowledgeTab />);
    expect(screen.getByText("База знаний")).toBeInTheDocument();
    await waitFor(() => {
      expect(api.listKBTables).toHaveBeenCalledTimes(1);
      expect(api.listMetrics).toHaveBeenCalledTimes(1);
    });
  });

  it("renders tables after load", async () => {
    render(<KnowledgeTab />);
    await waitFor(() => {
      expect(screen.getByText("users")).toBeInTheDocument();
      expect(screen.getByText("orders")).toBeInTheDocument();
    });
  });

  it("renders metrics after load", async () => {
    render(<KnowledgeTab />);
    await waitFor(() => {
      expect(screen.getByText("revenue")).toBeInTheDocument();
      expect(screen.getByText("SUM(amount)")).toBeInTheDocument();
    });
  });

  it("shows search input", async () => {
    render(<KnowledgeTab />);
    expect(screen.getByPlaceholderText("Поиск по метаданным…")).toBeInTheDocument();
  });

  it("shows dbt upload and datahub sync buttons", async () => {
    render(<KnowledgeTab />);
    expect(screen.getByTitle("Загрузить dbt manifest.json")).toBeInTheDocument();
    expect(screen.getByTitle("Синхронизировать DataHub")).toBeInTheDocument();
  });

  it("renders empty state when no tables", async () => {
    vi.mocked(api.listKBTables).mockResolvedValue([]);
    vi.mocked(api.listMetrics).mockResolvedValue([]);
    render(<KnowledgeTab />);
    await waitFor(() => {
      expect(screen.getByText("Нет метаданных. Загрузите dbt или подключите БД.")).toBeInTheDocument();
    });
  });

  it("shows certified badge icon for certified tables", async () => {
    render(<KnowledgeTab />);
    await waitFor(() => {
      expect(screen.getByText("users")).toBeInTheDocument();
    });
    // Crown иконка — svg с lucide-crown
    const crown = document.querySelector("svg.lucide-crown");
    expect(crown).toBeInTheDocument();
  });

  it("shows metric form toggle button", async () => {
    render(<KnowledgeTab />);
    await waitFor(() => {
      expect(screen.getByText("Метрики (1)")).toBeInTheDocument();
    });
  });

  it("shows owner and layer info for tables", async () => {
    render(<KnowledgeTab />);
    await waitFor(() => {
      expect(screen.getByText(/Ivan/)).toBeInTheDocument();
      expect(screen.getByText(/mart/)).toBeInTheDocument();
    });
  });
});