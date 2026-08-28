"""
HTML building blocks for reports.

Everything here is constrained to the subset of HTML/CSS that Qt's rich-text
engine understands, because the same markup is shown in a ``QTextBrowser`` on
the report screen and rendered to PDF via ``QTextDocument`` + ``QPrinter``:

* layout with ``<table>`` only -- no flexbox, no grid
* inline ``style="..."`` and ``<font color>``; a single ``<style>`` block is
  used only for coarse element defaults that Qt honours
* images as ``data:`` URIs
* one self-contained file
"""

from __future__ import annotations

import html as _html
from typing import Iterable, Sequence

from .theme import Theme


def escape(value: object) -> str:
    """HTML-escape any value (stringifying first)."""
    return _html.escape("" if value is None else str(value))


def page(title: str, theme: Theme, body: str) -> str:
    """Wrap ``body`` in a full self-contained HTML document."""
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{escape(title)}</title>
<style>
  body {{ background-color: {theme.background}; color: {theme.text};
          font-family: {theme.font_family}; font-size: 13px; }}
  h1 {{ color: {theme.success}; font-size: 22px;
        border-bottom: 2px solid {theme.border}; padding-bottom: 6px; }}
  h2 {{ color: {theme.primary}; font-size: 16px; margin-top: 22px; }}
  a  {{ color: {theme.primary}; }}
  td, th {{ padding: 6px 10px; }}
  th {{ background-color: {theme.table_header}; color: {theme.text_bright};
        text-align: left; }}
</style>
</head>
<body>
{body}
</body>
</html>"""


def heading(text: str, level: int = 2) -> str:
    return f"<h{level}>{escape(text)}</h{level}>"


def paragraph(text: str, *, dim: bool = False, theme: Theme | None = None) -> str:
    if dim and theme is not None:
        return f'<p style="color:{theme.text_dim}">{escape(text)}</p>'
    return f"<p>{escape(text)}</p>"


def title_block(theme: Theme, title: str, subtitle: str,
                meta_lines: Sequence[str]) -> str:
    parts = [f"<h1>{escape(title)}</h1>"]
    if subtitle:
        parts.append(
            f'<p style="color:{theme.text_dim};margin-top:-4px">'
            f"{escape(subtitle)}</p>"
        )
    rows = "".join(
        f'<tr><td style="color:{theme.text_dim}">{escape(line)}</td></tr>'
        for line in meta_lines if line
    )
    if rows:
        parts.append(f'<table cellspacing="0" cellpadding="0">{rows}</table>')
    return "\n".join(parts)


def status_banner(theme: Theme, color: str, message: str) -> str:
    if not message:
        return ""
    return (
        f'<table width="100%" cellspacing="0" cellpadding="0" '
        f'style="margin:14px 0"><tr>'
        f'<td style="background-color:{theme.surface};'
        f'border-left:4px solid {color};padding:10px 14px;'
        f'color:{theme.text_bright}">{escape(message)}</td>'
        f"</tr></table>"
    )


def summary_grid(theme: Theme, items: Iterable, columns: int = 4) -> str:
    """Render SummaryItem-likes as a fixed-column grid of cards (via a table)."""
    items = list(items)
    if not items:
        return ""

    cells = []
    for it in items:
        label = escape(getattr(it, "label", ""))
        value = escape(getattr(it, "value", ""))
        status = getattr(it, "status", None)
        color = status.color(theme) if status is not None else theme.text_bright
        cells.append(
            f'<td width="{100 // columns}%" '
            f'style="background-color:{theme.surface};padding:12px;'
            f'border:1px solid {theme.border}">'
            f'<div style="font-size:20px;font-weight:bold;color:{color}">{value}</div>'
            f'<div style="font-size:11px;color:{theme.text_dim}">{label}</div>'
            f"</td>"
        )

    rows = []
    for i in range(0, len(cells), columns):
        row = cells[i:i + columns]
        rows.append("<tr>" + "".join(row) + "</tr>")

    return (
        f'<table width="100%" cellspacing="6" cellpadding="0" '
        f'style="margin:10px 0">{"".join(rows)}</table>'
    )


def table(theme: Theme, headers: Sequence[str],
          rows: Sequence[Sequence[object]]) -> str:
    """A plain bordered data table with zebra striping."""
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body_rows = []
    for idx, row in enumerate(rows):
        bg = theme.table_row_alt if idx % 2 else theme.background
        cells = "".join(
            f'<td style="border-bottom:1px solid {theme.border}">{escape(c)}</td>'
            for c in row
        )
        body_rows.append(f'<tr style="background-color:{bg}">{cells}</tr>')
    return (
        f'<table width="100%" cellspacing="0" cellpadding="0" '
        f'style="margin:10px 0"><tr>{head}</tr>{"".join(body_rows)}</table>'
    )


def image(data_uri: str, *, max_width: int = 760) -> str:
    if not data_uri:
        return ""
    return (
        f'<p><img src="{escape(data_uri)}" width="{max_width}" '
        f'style="max-width:{max_width}px"></p>'
    )


def key_values(theme: Theme, pairs: Iterable) -> str:
    """Two-column label/value table for a section's details."""
    rows = []
    for key, value in pairs:
        rows.append(
            f'<tr><td style="color:{theme.text_dim};width:220px">{escape(key)}</td>'
            f"<td>{escape(value)}</td></tr>"
        )
    if not rows:
        return ""
    return (
        f'<table cellspacing="0" cellpadding="0" style="margin:8px 0">'
        f'{"".join(rows)}</table>'
    )
