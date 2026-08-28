"""
Dict-based convenience wrappers used by ``gui/screens/report_screen.py``.

Each returns a complete HTML string. They accept the loosely-typed dicts the
report screen already assembles and forward them straight into the section
renderers (which read the same keys).
"""

from __future__ import annotations

from typing import Any, Dict

from .generator import ReportGenerator
from .models import ReportData, ReportMetadata, ReportType, StatusLevel, SummaryItem


def _wrap(report_type: ReportType, title: str, data: Dict[str, Any],
          device_path: str = "Unknown", geometry: str = "Unknown",
          summary_items=None, status=StatusLevel.INFO,
          status_message: str = "") -> str:
    meta = ReportMetadata(
        title=title,
        report_type=report_type,
        device_path=device_path or "",
        geometry=geometry or "",
    )
    report_data = ReportData(
        metadata=meta,
        summary_items=summary_items or [],
        status=status,
        status_message=status_message,
        raw_data=dict(data or {}),
    )
    return ReportGenerator(report_type, report_data).generate_html()


def generate_scan_report(data: Dict[str, Any], device_path: str = "Unknown",
                         geometry: str = "Unknown") -> str:
    good = data.get("good_sectors", 0)
    bad = data.get("bad_sectors", 0)
    items = [
        SummaryItem("Total Sectors", data.get("total_sectors", "-")),
        SummaryItem("Good Sectors", good, StatusLevel.SUCCESS),
        SummaryItem("Bad Sectors", bad,
                    StatusLevel.SUCCESS if not bad else StatusLevel.ERROR),
    ]
    status = StatusLevel.SUCCESS if not bad else StatusLevel.WARNING
    message = "All sectors readable" if not bad else f"{bad} bad sector(s) found"
    return _wrap(ReportType.SCAN, "Disk Scan Report", data, device_path,
                 geometry, items, status, message)


def generate_recovery_report(data: Dict[str, Any], device_path: str = "Unknown",
                             geometry: str = "Unknown") -> str:
    initial = data.get("initial_bad", 0)
    final = data.get("final_bad", 0)
    recovered = data.get("sectors_recovered", max(0, initial - final))
    items = [
        SummaryItem("Initial Bad", initial),
        SummaryItem("Recovered", recovered, StatusLevel.SUCCESS),
        SummaryItem("Final Bad", final,
                    StatusLevel.SUCCESS if not final else StatusLevel.ERROR),
        SummaryItem("Passes", data.get("passes_executed", data.get("passes", "-"))),
    ]
    if not final:
        status, message = StatusLevel.SUCCESS, "All sectors recovered"
    elif recovered:
        status, message = StatusLevel.WARNING, (
            f"Partial recovery: {recovered} of {initial} sectors recovered"
        )
    else:
        status, message = StatusLevel.ERROR, "No sectors recovered"
    return _wrap(ReportType.RECOVERY, "Disk Recovery Report", data, device_path,
                 geometry, items, status, message)


def generate_diagnostic_report(data: Dict[str, Any],
                               device_path: str = "Unknown") -> str:
    return _wrap(ReportType.DIAGNOSTIC, "Drive Diagnostic Report", data,
                 device_path)


def generate_comparison_report(data: Dict[str, Any]) -> str:
    return _wrap(ReportType.COMPARISON, "Image Comparison Report", data)
