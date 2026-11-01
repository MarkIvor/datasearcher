import "@testing-library/jest-dom/vitest";
import { vi, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Тесты написаны против русской локали (jsdom navigator.language = en-US)
localStorage.setItem("ds-lang", "ru");

// Автоматический unmount после каждого теста
afterEach(() => {
  cleanup();
  localStorage.setItem("ds-lang", "ru");
});

// Мок для html-to-image (используется в ChartBlock/App, но не в наших тестах)
vi.mock("html-to-image", () => ({
  toPng: vi.fn().mockResolvedValue("data:image/png;base64,mock"),
}));

// Мок для fetch по умолчанию (для API-модуля)
globalThis.fetch = globalThis.fetch || vi.fn();