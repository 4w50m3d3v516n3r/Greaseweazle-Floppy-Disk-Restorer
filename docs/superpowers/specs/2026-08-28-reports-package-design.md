# `floppy_formatter.reports` package — design

## Problem

`src/floppy_formatter/reports/` is imported by `gui/main_window.py` (report
export, batch-verify export) and `gui/screens/report_screen.py` (on-screen
reports) but does not exist in the repo. `.gitignore` contains a blanket
`reports/` rule (intended for *output* files) that silently excluded the
first-party package, so it was never committed. `report_screen.py` guards the
import (`REPORTS_AVAILABLE`) and has inline fallbacks; `main_window.py` does
not, so "Export Report" raises `ModuleNotFoundError`.

## Goal

Reconstruct the package to satisfy the existing call sites, with no changes to
their logic. Restore HTML / PDF / plain-text report export for scan, format,
recovery, analysis and batch-verify operations, plus the dict-based
`generate_*_report` helpers used by the report screen.

## Public API (fixed by call sites)

`from floppy_formatter.reports import ...`

- `ReportType` — enum: `SCAN, FORMAT, RECOVERY, ANALYSIS, DIAGNOSTIC, COMPARISON, BATCH_VERIFY`
- `StatusLevel` — enum: `SUCCESS, WARNING, ERROR, INFO`; `.color(theme)` helper
- `SummaryItem(label: str, value: Any, status: StatusLevel = StatusLevel.INFO)`
- `ReportMetadata(title, report_type, subtitle="", device_path="", geometry="", timestamp=datetime.now())`
- `ReportData(metadata, summary_items=[], status=StatusLevel.INFO, status_message="", raw_data={})`
- `DARK_THEME` — a `Theme` instance
- `ReportGenerator(report_type: ReportType, data: ReportData, theme: Theme = DARK_THEME)`
  - `.generate_html() -> str`
  - `.export_html(path)`, `.export_pdf(path)`, `.export_text(path)`
- `generate_scan_report(data: dict, device_path="Unknown", geometry="Unknown") -> str`
- `generate_recovery_report(data: dict, device_path="Unknown", geometry="Unknown") -> str`
- `generate_diagnostic_report(data: dict, device_path="Unknown") -> str`
- `generate_comparison_report(data: dict) -> str`

## Module layout

| File | Responsibility |
|---|---|
| `models.py` | the dataclasses/enums above |
| `theme.py` | `Theme` dataclass, `DARK_THEME` (colors already in `report_screen.py`) |
| `html.py` | Qt-rich-text-safe HTML primitives: `page(title, theme, body)`, `summary_grid(items, theme)`, `table(headers, rows, theme)`, `status_banner(...)`, `escape()` |
| `sections.py` | `render_body(report_type, data, theme) -> str` — one branch per type, all `getattr`/`dict.get` defensive |
| `generator.py` | `ReportGenerator`; PDF via `QTextDocument`+`QPrinter` (as `main_window._save_batch_report_pdf` already does), text via `QTextDocument.toPlainText()` |
| `functions.py` | the four `generate_*_report` dict wrappers → build a `ReportData` → `ReportGenerator(...).generate_html()` |
| `__init__.py` | re-export the public API |

## Rendering constraints

Both consumers render the HTML with Qt's limited rich-text engine
(`QTextBrowser`, `QTextDocument`). Therefore:

- layout with `<table>`, never flexbox/grid
- inline `style="..."` and `<font color>` only; no external/`<style>` cascade
  reliance beyond what Qt supports (a `<style>` block for basic element rules is
  fine, Qt honours a subset)
- images as `<img src="data:image/png;base64,...">` (Qt supports data URIs)
- self-contained single file

## Non-goals

- No pixel-parity with the original (lost) implementation.
- No new dependency; `reportlab` present but unused (Qt path is enough).
- No change to `main_window.py` / `report_screen.py` behaviour.
- `.gitignore` `*.json` / `*.txt` breadth is noted but out of scope; only
  `reports/` → `/reports/` is changed here.

## Testing

`tests/unit/test_reports.py`:

- imports: every public name is importable from `floppy_formatter.reports`
- `ReportGenerator(type, data).generate_html()` for each `ReportType`: contains
  title, status message, each summary item label; tolerates empty `raw_data`
- `StatusLevel` → colour mapping
- `functions.generate_*` with representative dicts return non-empty HTML
- export (guarded `importorskip("PyQt6.QtPrintSupport")`): `export_pdf` writes a
  file starting with `%PDF`; `export_text` writes non-empty text; `export_html`
  round-trips `generate_html()`
