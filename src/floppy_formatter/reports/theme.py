"""
Colour themes for generated reports.

The values in ``DARK_THEME`` match the palette already hard-coded in
``gui/screens/report_screen.py`` so on-screen and exported reports look alike.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """A flat colour set consumed by the HTML primitives."""

    background: str
    surface: str
    border: str
    text: str
    text_dim: str
    text_bright: str
    primary: str
    success: str
    warning: str
    error: str
    table_header: str
    table_row_alt: str
    font_family: str = "'Segoe UI', 'DejaVu Sans', Arial, sans-serif"


DARK_THEME = Theme(
    background="#1e1e1e",
    surface="#252526",
    border="#3c3c3c",
    text="#cccccc",
    text_dim="#858585",
    text_bright="#ffffff",
    primary="#0e639c",
    success="#4ec9b0",
    warning="#f0a030",
    error="#f14c4c",
    table_header="#2d2d30",
    table_row_alt="#2a2a2a",
)


LIGHT_THEME = Theme(
    background="#ffffff",
    surface="#f3f3f3",
    border="#d0d0d0",
    text="#1e1e1e",
    text_dim="#6a6a6a",
    text_bright="#000000",
    primary="#0e639c",
    success="#1a7f64",
    warning="#8a5a00",
    error="#b3261e",
    table_header="#e6e6e6",
    table_row_alt="#f7f7f7",
)
