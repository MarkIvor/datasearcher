from __future__ import annotations

import io
import re
import base64
from datetime import datetime

from fpdf import FPDF


class _ReportPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font(self._fn, "", 8)
            self.set_text_color(147, 150, 156)
            self.cell(w=0, h=8, text="DataSearcher Report", align="R", new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font(self._fn, "", 8)
        self.set_text_color(147, 150, 156)
        self.cell(w=0, h=10, text=f"Page {self.page_no()}", align="C")


def _find_ttf_font() -> tuple[str | None, str | None]:
    import os
    search_dirs = []
    if os.name == "nt":
        search_dirs.append(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
    else:
        search_dirs.extend([
            "/usr/share/fonts/truetype/dejavu",
            "/usr/share/fonts/truetype/liberation",
            "/usr/share/fonts/TTF",
            "/usr/local/share/fonts",
        ])
        home = os.path.expanduser("~")
        search_dirs.extend([
            os.path.join(home, ".fonts"),
            os.path.join(home, ".local/share/fonts"),
        ])

    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for root, dirs, files in os.walk(d):
            regular = bold = None
            for f in files:
                fl = f.lower()
                if not fl.endswith(".ttf"):
                    continue
                if "dejavusans" in fl or "liberationsans" in fl or "arial" in fl:
                    if "bold" in fl or "bd" in fl:
                        if not bold:
                            bold = os.path.join(root, f)
                    else:
                        if not regular:
                            regular = os.path.join(root, f)
            if regular:
                return regular, bold
    return None, None


def generate_report_pdf(
    chat_history: list[dict],
    charts: list[dict] | None = None,
    title: str = "DataSearcher Report",
) -> bytes:
    pdf = _ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)

    ttf_regular, ttf_bold = _find_ttf_font()
    if ttf_regular:
        pdf.add_font("CustomFont", "", ttf_regular)
        pdf.add_font("CustomFont", "B", ttf_bold or ttf_regular)
        fn = "CustomFont"
    else:
        fn = "Helvetica"
    pdf._fn = fn

    # ── Title page ─────────────────────────────
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font(fn, "B", 28)
    pdf.set_text_color(91, 106, 240)
    pdf.cell(w=0, h=16, text=title, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_font(fn, "", 12)
    pdf.set_text_color(147, 150, 156)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    pdf.cell(w=0, h=8, text=f"Сгенерировано: {now}", align="C", new_x="LMARGIN", new_y="NEXT")

    if chat_history:
        first_user = next((m for m in chat_history if m.get("role") == "user"), None)
        if first_user and first_user.get("content"):
            pdf.ln(4)
            pdf.set_font(fn, "", 10)
            pdf.set_text_color(147, 150, 156)
            q = first_user["content"][:80]
            pdf.cell(w=0, h=6, text=f"Запрос: {q}...", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(16)
    pdf.set_draw_color(91, 106, 240)
    pdf.set_line_width(0.5)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())

    # ── Charts section ─────────────────────────
    if charts:
        pdf.add_page()
        pdf.set_font(fn, "B", 16)
        pdf.set_text_color(17, 19, 24)
        pdf.cell(w=0, h=10, text="Графики", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

        for i, chart in enumerate(charts):
            chart_title = chart.get("title", f"График {i+1}")
            png_b64 = chart.get("png_base64", "")

            if not png_b64:
                continue

            pdf.set_font(fn, "B", 11)
            pdf.set_text_color(91, 106, 240)
            pdf.cell(w=0, h=7, text=chart_title, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

            try:
                img_data = base64.b64decode(png_b64)
                img_stream = io.BytesIO(img_data)

                if pdf.get_y() > 160:
                    pdf.add_page()

                w = min(170, pdf.epw)
                pdf.image(img_stream, x=15, w=w)
                pdf.ln(8)
            except Exception:
                pdf.set_font(fn, "", 10)
                pdf.set_text_color(147, 150, 156)
                pdf.cell(w=0, h=6, text="[Ошибка рендеринга графика]", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(4)

    # ── Text content ───────────────────────────
    if chat_history:
        pdf.add_page()
        pdf.set_font(fn, "B", 16)
        pdf.set_text_color(17, 19, 24)
        pdf.cell(w=0, h=10, text="Анализ", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

        for msg in chat_history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if not content:
                continue
            content = _clean_content(content)
            if not content.strip():
                continue

            if role == "user":
                pdf.set_font(fn, "B", 10)
                pdf.set_text_color(91, 106, 240)
                pdf.cell(w=0, h=6, text=f"Вопрос: {content[:120]}", new_x="LMARGIN", new_y="NEXT")
                pdf.ln(4)
            elif role == "assistant":
                pdf.set_font(fn, "", 10)
                pdf.set_text_color(17, 19, 24)
                _write_sections(pdf, fn, content)
                pdf.ln(6)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


def _write_sections(pdf: FPDF, fn: str, text: str):
    lines = text.split("\n")
    for line in lines:
        stripped = line.strip()
        if not stripped:
            pdf.ln(3)
            continue

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped.lstrip("#").strip()
            title = re.sub(r"\*+", "", title)
            if level == 1:
                pdf.set_font(fn, "B", 14)
            elif level == 2:
                pdf.set_font(fn, "B", 12)
            else:
                pdf.set_font(fn, "B", 11)
            pdf.set_text_color(17, 19, 24)
            if pdf.get_y() > 250:
                pdf.add_page()
            pdf.multi_cell(w=0, h=7, text=title, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        elif stripped.startswith("- ") or stripped.startswith("* "):
            pdf.set_font(fn, "", 10)
            pdf.set_text_color(55, 58, 62)
            bullet_text = "  " + stripped[2:]
            bullet_text = re.sub(r"\*+", "", bullet_text)
            pdf.multi_cell(w=0, h=5, text=bullet_text, new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font(fn, "", 10)
            pdf.set_text_color(17, 19, 24)
            clean_line = re.sub(r"\*+", "", stripped)
            if pdf.get_y() > 270:
                pdf.add_page()
            try:
                pdf.multi_cell(w=0, h=5, text=clean_line, new_x="LMARGIN", new_y="NEXT")
            except Exception:
                safe = clean_line.encode("latin-1", errors="replace").decode("latin-1")
                pdf.multi_cell(w=0, h=5, text=safe, new_x="LMARGIN", new_y="NEXT")


def _clean_content(text: str) -> str:
    text = re.sub(r"```[\w]*\n?", "", text)
    text = re.sub(r"```", "", text)
    text = re.sub(r"__CHART_DATA__.*?__END_CHART_DATA__", "", text, flags=re.DOTALL)
    text = re.sub(r"__CLASSIFY_TASK__.*?__END_CLASSIFY_TASK__", "", text, flags=re.DOTALL)
    text = re.sub(r"__GENERATE_SQL_TASK__.*?__END_GENERATE_SQL_TASK__", "", text, flags=re.DOTALL)
    text = re.sub(r"__EXPORT_DATA__.*?__END_EXPORT_DATA__", "", text, flags=re.DOTALL)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = text.strip()
    return text
