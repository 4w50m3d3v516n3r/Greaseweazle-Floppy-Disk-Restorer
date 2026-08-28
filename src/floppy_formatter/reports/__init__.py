"""
Operation report generation (HTML / PDF / plain text).

Public API consumed by the GUI:

    from floppy_formatter.reports import (
        ReportGenerator, ReportType, ReportData, ReportMetadata,
        SummaryItem, StatusLevel, DARK_THEME,
        generate_scan_report, generate_recovery_report,
        generate_diagnostic_report, generate_comparison_report,
    )
"""

from .functions import (
    generate_comparison_report,
    generate_diagnostic_report,
    generate_recovery_report,
    generate_scan_report,
)
from .generator import ReportGenerator
from .models import (
    ReportData,
    ReportMetadata,
    ReportType,
    StatusLevel,
    SummaryItem,
)
from .theme import DARK_THEME, LIGHT_THEME, Theme

__all__ = [
    "ReportGenerator",
    "ReportType",
    "ReportData",
    "ReportMetadata",
    "SummaryItem",
    "StatusLevel",
    "Theme",
    "DARK_THEME",
    "LIGHT_THEME",
    "generate_scan_report",
    "generate_recovery_report",
    "generate_diagnostic_report",
    "generate_comparison_report",
]
