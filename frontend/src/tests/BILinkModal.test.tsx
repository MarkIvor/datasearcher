import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BILinkModal } from "../components/Layout/BILinkModal";

vi.mock("../api/client", () => ({
  buildBILink: vi.fn(),
}));

import * as api from "../api/client";

describe("BILinkModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders title and close button", () => {
    render(<BILinkModal onClose={vi.fn()} />);
    expect(screen.getByText("BI Link Builder")).toBeInTheDocument();
    expect(document.querySelector(".modal-close")).toBeInTheDocument();
  });

  it("renders all BI tool options", () => {
    render(<BILinkModal onClose={vi.fn()} />);
    expect(screen.getByText("Apache Superset")).toBeInTheDocument();
    expect(screen.getByText("Grafana")).toBeInTheDocument();
    expect(screen.getByText("Yandex Datalens")).toBeInTheDocument();
    expect(screen.getByText("Tableau")).toBeInTheDocument();
    expect(screen.getByText("Power BI")).toBeInTheDocument();
  });

  it("shows error when base_url empty", async () => {
    const user = userEvent.setup();
    render(<BILinkModal onClose={vi.fn()} />);
    await user.click(screen.getByText("Сгенерировать ссылку"));
    expect(screen.getByText("Укажите базовый URL")).toBeInTheDocument();
    expect(api.buildBILink).not.toHaveBeenCalled();
  });

  it("shows error for invalid JSON params", async () => {
    render(<BILinkModal onClose={vi.fn()} />);
    const urlInput = screen.getByPlaceholderText("https://superset.company.com");
    fireEvent.change(urlInput, { target: { value: "https://x.com" } });
    const textarea = screen.getByDisplayValue(/region/);
    fireEvent.change(textarea, { target: { value: "not-json{" } });
    fireEvent.click(screen.getByText("Сгенерировать ссылку"));
    expect(screen.getByText("params должен быть валидным JSON")).toBeInTheDocument();
    expect(api.buildBILink).not.toHaveBeenCalled();
  });

  it("calls buildBILink and shows URL on success", async () => {
    vi.mocked(api.buildBILink).mockResolvedValue({
      url: "https://superset.x.com/superset/dashboard/5/?fltr_col=region&fltr_val=Москва",
    });
    const user = userEvent.setup();
    render(<BILinkModal onClose={vi.fn()} />);
    await user.type(screen.getByPlaceholderText("https://superset.company.com"), "https://superset.x.com");
    await user.type(screen.getByPlaceholderText("5"), "5");
    await user.click(screen.getByText("Сгенерировать ссылку"));
    await waitFor(() => {
      expect(api.buildBILink).toHaveBeenCalledWith(expect.objectContaining({
        tool: "superset",
        base_url: "https://superset.x.com",
        dashboard_id: "5",
      }));
      expect(screen.getByText(/superset\.x\.com/)).toBeInTheDocument();
    });
  });

  it("shows time range fields only for grafana", async () => {
    const user = userEvent.setup();
    render(<BILinkModal onClose={vi.fn()} />);
    expect(screen.queryByPlaceholderText("2024-01-01")).not.toBeInTheDocument();
    const select = screen.getByRole("combobox");
    await user.selectOptions(select, "grafana");
    expect(screen.getByPlaceholderText("2024-01-01")).toBeInTheDocument();
  });

  it("calls onClose when overlay clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<BILinkModal onClose={onClose} />);
    await user.click(document.querySelector(".modal-overlay")!);
    expect(onClose).toHaveBeenCalled();
  });

  it("shows copy button after URL generated", async () => {
    vi.mocked(api.buildBILink).mockResolvedValue({ url: "https://x.com/d/1" });
    const user = userEvent.setup();
    render(<BILinkModal onClose={vi.fn()} />);
    await user.type(screen.getByPlaceholderText("https://superset.company.com"), "https://x.com");
    await user.click(screen.getByText("Сгенерировать ссылку"));
    await waitFor(() => {
      expect(screen.getByText("https://x.com/d/1")).toBeInTheDocument();
    });
  });
});