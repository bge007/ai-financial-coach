"""Render consolidated report data to PDF bytes."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from fpdf.fonts import FontFace


def _ascii_safe(text: str) -> str:
    """Helvetica-safe text (replace rupee and smart quotes)."""
    return (
        (text or "")
        .replace("\u20b9", "Rs.")
        .replace("\u2014", "-")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .encode("latin-1", errors="replace")
        .decode("latin-1")
    )


def _truncate(text: str, limit: int = 80) -> str:
    raw = _ascii_safe(" ".join((text or "").split()))
    return raw if len(raw) <= limit else raw[: limit - 1] + "..."


def _column_widths(n_cols: int, headers: list[str]) -> tuple[float, ...]:
    """Return mm widths that sum to epw (~190 on A4)."""
    if n_cols == 2 and headers and headers[0] in {"#", "No.", "No"}:
        return (12.0, 178.0)
    if n_cols == 2:
        return (58.0, 132.0)
    if n_cols == 5:
        return (24.0, 78.0, 14.0, 32.0, 42.0)
    if n_cols == 4:
        return (52.0, 38.0, 34.0, 66.0)
    share = 190.0 / max(n_cols, 1)
    return tuple(share for _ in range(n_cols))


class _ReportPDF(FPDF):
    _HEADING_STYLE = FontFace(
        family="Helvetica",
        emphasis="",
        size_pt=8,
        color=255,
        fill_color=(10, 46, 92),
    )

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0,
            10,
            _ascii_safe(
                "Informational only - not SEBI-registered investment advice. MoneyMitra."
            ),
            align="C",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

    def write_paragraph(self, text: str, *, line_height: float = 5.5) -> None:
        self.set_x(self.l_margin)
        self.multi_cell(self.epw, line_height, _truncate(text, 420))

    def ensure_space(self, height: float) -> None:
        if self.get_y() + height > self.h - self.b_margin:
            self.add_page()

    def write_subheading(self, text: str) -> None:
        self.ensure_space(10)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(10, 46, 92)
        self.write_paragraph(text, line_height=5)
        self.ln(2)

    def write_metrics(self, metrics: list[dict[str, str]]) -> None:
        if not metrics:
            return
        self.write_subheading("Key metrics")
        self.ensure_space(16)
        self.set_font("Helvetica", "", 8)
        col_w = self.epw / 3
        widths = (col_w, col_w, col_w)
        with self.table(
            width=self.epw,
            col_widths=widths,
            first_row_as_headings=False,
            line_height=5,
        ) as table:
            for i in range(0, len(metrics), 3):
                chunk = metrics[i : i + 3]
                row = table.row()
                for item in chunk:
                    label = _truncate(item.get("label", ""), 28)
                    value = _truncate(item.get("value", ""), 24)
                    row.cell(f"{label}\n{value}")
                for _ in range(3 - len(chunk)):
                    row.cell("")
        self.ln(3)

    def write_table(
        self,
        title: str,
        headers: list[str],
        rows: list[list[str]],
        *,
        col_widths: tuple[float, ...] | None = None,
    ) -> None:
        if not headers or not rows:
            return
        self.write_subheading(title)
        n_cols = len(headers)
        widths = col_widths or _column_widths(n_cols, headers)
        if len(widths) != n_cols:
            widths = _column_widths(n_cols, headers)
        scale = self.epw / sum(widths)
        widths = tuple(w * scale for w in widths)

        self.set_font("Helvetica", "", 7)
        with self.table(
            width=self.epw,
            col_widths=widths,
            headings_style=self._HEADING_STYLE,
            line_height=4.8,
        ) as table:
            header_row = table.row()
            for h in headers:
                header_row.cell(_truncate(h, 24))
            for row in rows:
                data_row = table.row()
                cells = list(row) + [""] * (n_cols - len(row))
                limits = (12, 52, 10, 18, 22, 28)
                for idx, cell in enumerate(cells[:n_cols]):
                    limit = limits[idx] if idx < len(limits) else 32
                    data_row.cell(_truncate(str(cell), limit))
        self.ln(3)

    def write_chart(self, title: str, png_bytes: bytes) -> None:
        if not png_bytes:
            return
        self.write_subheading(title)
        max_w = self.epw
        max_h = 72.0
        self.ensure_space(max_h + 10)
        x = self.l_margin
        y = self.get_y()
        try:
            self.image(BytesIO(png_bytes), x=x, y=y, w=max_w, h=max_h)
        except Exception:
            self.write_paragraph("Chart could not be rendered.")
            return
        self.set_y(y + max_h + 8)


def build_consolidated_pdf(report: dict[str, Any]) -> bytes:
    pdf = _ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(10, 46, 92)
    pdf.cell(0, 10, "MoneyMitra", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(
        0,
        8,
        "Consolidated Financial Analysis Report",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(
        0,
        6,
        _ascii_safe(f"Prepared for: {report.get('user_name', '')}"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.cell(
        0,
        6,
        _ascii_safe(f"Email: {report.get('user_email', '')}"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    gen = (report.get("generated_at") or "")[:19].replace("T", " UTC ")
    pdf.cell(
        0,
        6,
        _ascii_safe(f"Generated: {gen}"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(4)

    for idx, section in enumerate(report.get("sections") or [], start=1):
        title = section.get("title") or f"Section {idx}"
        pdf.ensure_space(28)

        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(10, 46, 92)
        pdf.cell(
            0,
            8,
            _ascii_safe(f"{idx}. {title}"),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.ln(1)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 30, 30)
        for line in section.get("summary_lines") or []:
            pdf.write_paragraph(line)
            pdf.ln(1)

        pdf.write_metrics(section.get("metrics") or [])

        for chart in section.get("charts") or []:
            pdf.write_chart(chart.get("title", "Chart"), chart.get("png") or b"")

        for table in section.get("tables") or []:
            pdf.write_table(
                table.get("title", "Details"),
                table.get("headers") or [],
                table.get("rows") or [],
                col_widths=tuple(table["col_widths"])
                if table.get("col_widths")
                else None,
            )

        bullets = section.get("bullets") or []
        if bullets:
            pdf.write_subheading("Recommendations")
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(80, 80, 80)
            for bullet in bullets:
                pdf.write_paragraph(f"- {bullet}", line_height=5)
            pdf.ln(2)

        pdf.ln(2)
        pdf.set_draw_color(220, 220, 220)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(5)

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()
