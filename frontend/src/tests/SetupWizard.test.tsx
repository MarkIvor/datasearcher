import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SetupWizard } from "../components/Setup/SetupWizard";

const defaultState = {
  completed: false,
  mode: "",
  step: 1,
  steps_total: 4,
  scope: "user" as const,
  is_admin: true,
  llm: { url: "http://llm:11434/v1", model: "qwen2.5:14b", api_key_masked: "sk-***", has_key: true },
  enterprise: {
    read_only: true, pii_masking: true, rate_limit_enabled: true,
    log_enabled: true, default_mode: "auto", auto_translate: true,
  },
  connections_count: 1,
};

const mcpConfig = {
  connections_yaml: "connections:\n  - name: \"pg\"\n    db_type: postgresql\n",
  claude_json: '{\n  "mcpServers": {\n    "datasearcher": { "command": "datasearcher-mcp" }\n  }\n}',
  cursor_json: '{\n  "mcpServers": {\n    "datasearcher": { "command": "datasearcher-mcp" }\n  }\n}',
  http_command: "datasearcher-mcp --transport http --host 0.0.0.0 --port 8000 --auth-token secret123",
  docker_command: "cd mcp && docker compose -f docker-compose.yml up -d",
  env_block: "LLM_BASE_URL=http://llm:11434/v1\nLLM_MODEL=qwen2.5:14b",
  connections: ["pg"],
};

const mocks = vi.hoisted(() => ({
  getSetup: vi.fn(),
  updateSetup: vi.fn(),
  testSetupLLM: vi.fn(),
  generateMcpConfig: vi.fn(),
  listDBConnections: vi.fn().mockResolvedValue([]),
  createDBConnection: vi.fn(),
  uploadFile: vi.fn(),
}));

vi.mock("../api/client", () => mocks);

describe("SetupWizard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getSetup.mockResolvedValue({ ...defaultState });
    mocks.updateSetup.mockImplementation(async (patch: Record<string, unknown>) => ({
      ...defaultState,
      ...patch,
      llm: defaultState.llm,
    }));
  });

  it("renders step 1 with two type cards", async () => {
    render(<SetupWizard onComplete={vi.fn()} />);
    await waitFor(() => expect(mocks.getSetup).toHaveBeenCalled());
    expect(screen.getByText("Как вы будете использовать DataSearcher?")).toBeInTheDocument();
    expect(screen.getByText("Interface")).toBeInTheDocument();
    expect(screen.getByText("MCP")).toBeInTheDocument();
    expect(screen.getByText("Step 1 of 4")).toBeInTheDocument();
  });

  it("Next is disabled until a type is selected", async () => {
    render(<SetupWizard onComplete={vi.fn()} />);
    await waitFor(() => expect(mocks.getSetup).toHaveBeenCalled());
    const nextBtn = screen.getByText("Далее").closest("button")!;
    expect(nextBtn.disabled).toBe(true);
  });

  it("selecting Interface and going next shows LLM params step", async () => {
    render(<SetupWizard onComplete={vi.fn()} />);
    await waitFor(() => expect(mocks.getSetup).toHaveBeenCalled());
    fireEvent.click(screen.getByText("Interface"));
    expect(mocks.updateSetup).toHaveBeenCalledWith(expect.objectContaining({ mode: "interface" }));
    fireEvent.click(screen.getByText("Далее"));
    await waitFor(() => {
      expect(screen.getByText("Параметры ИИ")).toBeInTheDocument();
      expect(screen.getByText("Проверить")).toBeInTheDocument();
    });
  });

  it("step 2 test LLM shows success status", async () => {
    mocks.testSetupLLM.mockResolvedValue({ connected: true, models: ["qwen2.5:14b"] });
    render(<SetupWizard onComplete={vi.fn()} />);
    await waitFor(() => expect(mocks.getSetup).toHaveBeenCalled());
    fireEvent.click(screen.getByText("Interface"));
    fireEvent.click(screen.getByText("Далее"));
    await waitFor(() => expect(screen.getByText("Проверить")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Проверить"));
    await waitFor(() => expect(screen.getByText("Подключено")).toBeInTheDocument());
  });

  it("step 2 test LLM shows failure status", async () => {
    mocks.testSetupLLM.mockResolvedValue({ connected: false, error: "HTTP 500" });
    render(<SetupWizard onComplete={vi.fn()} />);
    await waitFor(() => expect(mocks.getSetup).toHaveBeenCalled());
    fireEvent.click(screen.getByText("Interface"));
    fireEvent.click(screen.getByText("Далее"));
    await waitFor(() => expect(screen.getByText("Проверить")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Проверить"));
    await waitFor(() => expect(screen.getByText("HTTP 500")).toBeInTheDocument());
  });

  it("can navigate to step 3 (data) and step 4 (scope)", async () => {
    render(<SetupWizard onComplete={vi.fn()} />);
    await waitFor(() => expect(mocks.getSetup).toHaveBeenCalled());
    fireEvent.click(screen.getByText("Interface"));
    fireEvent.click(screen.getByText("Далее"));
    fireEvent.click(screen.getByText("Далее"));
    await waitFor(() => expect(screen.getByText("Данные для анализа")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Далее"));
    await waitFor(() => expect(screen.getByText("Кому применить настройки")).toBeInTheDocument());
    expect(screen.getByText("Для всех пользователей")).toBeInTheDocument();
    expect(screen.getByText("Только для меня")).toBeInTheDocument();
  });

  it("interface finish calls onComplete", async () => {
    const onComplete = vi.fn();
    render(<SetupWizard onComplete={onComplete} />);
    await waitFor(() => expect(mocks.getSetup).toHaveBeenCalled());
    fireEvent.click(screen.getByText("Interface"));
    fireEvent.click(screen.getByText("Далее"));
    fireEvent.click(screen.getByText("Далее"));
    fireEvent.click(screen.getByText("Далее"));
    await waitFor(() => expect(screen.getByText("Confirm")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Confirm"));
    await waitFor(() => expect(screen.getByText("Всё готово")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Начать анализ"));
    expect(onComplete).toHaveBeenCalled();
  });

  it("mcp finish shows generated configs", async () => {
    mocks.generateMcpConfig.mockResolvedValue(mcpConfig);
    render(<SetupWizard onComplete={vi.fn()} />);
    await waitFor(() => expect(mocks.getSetup).toHaveBeenCalled());
    fireEvent.click(screen.getByText("MCP"));
    fireEvent.click(screen.getByText("Далее"));
    fireEvent.click(screen.getByText("Далее"));
    fireEvent.click(screen.getByText("Далее"));
    await waitFor(() => expect(screen.getByText("Сгенерировать конфиг")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Сгенерировать конфиг"));
    await waitFor(() => {
      expect(mocks.generateMcpConfig).toHaveBeenCalled();
      expect(screen.getByText("Конфигурации MCP готовы")).toBeInTheDocument();
      expect(screen.getByText("connections.yaml")).toBeInTheDocument();
      expect(screen.getByText("Claude Desktop — claude_desktop_config.json")).toBeInTheDocument();
      expect(screen.getByText("Cursor — .cursor/mcp.json")).toBeInTheDocument();
    });
  });

  it("mcp finish without connections shows fallback hint", async () => {
    mocks.generateMcpConfig.mockRejectedValue(new Error("Нет подключений"));
    render(<SetupWizard onComplete={vi.fn()} />);
    await waitFor(() => expect(mocks.getSetup).toHaveBeenCalled());
    fireEvent.click(screen.getByText("MCP"));
    fireEvent.click(screen.getByText("Далее"));
    fireEvent.click(screen.getByText("Далее"));
    fireEvent.click(screen.getByText("Далее"));
    await waitFor(() => expect(screen.getByText("Сгенерировать конфиг")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Сгенерировать конфиг"));
    await waitFor(() => expect(screen.getByText(/Подключения не найдены/i)).toBeInTheDocument());
  });

  it("shows 4 step rows in side panel", async () => {
    render(<SetupWizard onComplete={vi.fn()} />);
    await waitFor(() => expect(mocks.getSetup).toHaveBeenCalled());
    expect(screen.getByText("Тип")).toBeInTheDocument();
    expect(screen.getByText("Параметры")).toBeInTheDocument();
    expect(screen.getByText("Данные")).toBeInTheDocument();
    expect(screen.getByText("Готово")).toBeInTheDocument();
  });
});
