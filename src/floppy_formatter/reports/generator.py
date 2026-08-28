"""
``ReportGenerator`` -- turns a :class:`ReportData` into HTML, and exports it to
HTML / PDF / plain-text files.

PDF and text export use Qt (``QTextDocument`` + ``QPrinter``), matching the
approach already used elsewhere in the GUI. Qt is imported lazily so that
``generate_html()`` works in a headless / test context without it.
"""

from __future__ import annotations

import logging

from . import html as H
from .models import ReportData, ReportType, StatusLevel
from .sections import render_body
from .theme import DARK_THEME, Theme

logger = logging.getLogger(__name__)


class ReportGenerator:
    def __init__(
        self,
        report_type: ReportType,
        data: ReportData,
        theme: Theme = DARK_THEME,
    ) -> None:
        self.report_type = report_type
        self.data = data
        self.theme = theme or DARK_THEME

    # -- rendering -------------------------------------------------------- #

    def generate_html(self) -> str:
        meta = self.data.metadata
        theme = self.theme

        meta_lines = [
            f"Generated: {meta.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        if meta.device_path:
            meta_lines.append(f"Device: {meta.device_path}")
        if meta.geometry:
            meta_lines.append(f"Geometry: {meta.geometry}")

        status = self.data.status or StatusLevel.INFO
        parts = [
            H.title_block(theme, meta.title, meta.subtitle, meta_lines),
            H.status_banner(theme, status.color(theme), self.data.status_message),
            H.summary_grid(theme, self.data.summary_items),
            render_body(self.report_type, self.data, theme),
        ]
        logo = (self.data.raw_data or {}).get("app_logo")
        footer = (
            f'<p style="color:{theme.text_dim};font-size:11px;margin-top:26px">'
            f"Greaseweazle Floppy Disk Restorer</p>"
        )
        body = "\n".join(p for p in parts if p) + "\n" + footer
        return H.page(meta.title, theme, body)

    # -- export ---------------------------------------------------------- #

    def export_html(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.generate_html())

    def export_text(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self._to_plain_text())

    def export_pdf(self, path: str) -> None:
        from PyQt6.QtCore import QMarginsF
        from PyQt6.QtGui import QPageLayout, QPageSize, QTextDocument
        from PyQt6.QtPrintSupport import QPrinter

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageLayout(QPageLayout(
            QPageSize(QPageSize.PageSizeId.A4),
            QPageLayout.Orientation.Portrait,
            QMarginsF(14, 14, 14, 14),
            QPageLayout.Unit.Millimeter,
        ))

        doc = QTextDocument()
        doc.setHtml(self.generate_html())
        doc.print(printer)

    # -- helpers ------------------------------------------------------- #

    def _to_plain_text(self) -> str:
        html = self.generate_html()
        try:
            from PyQt6.QtGui import QTextDocument

            doc = QTextDocument()
            doc.setHtml(html)
            text = doc.toPlainText()
            if text.strip():
                return text
        except Exception as exc:  # pragma: no cover - depends on Qt runtime
            logger.debug("Qt plain-text conversion unavailable: %s", exc)
        return _strip_tags(html)


def _strip_tags(html: str) -> str:
    """Very small HTML -> text fallback for when Qt is not usable."""
    import re

    text = re.sub(r"(?is)<(script|style).*?</\1>", "", html)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|tr|h[1-6]|li)>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    import html as _htmlmod

    text = _htmlmod.unescape(text)
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)
