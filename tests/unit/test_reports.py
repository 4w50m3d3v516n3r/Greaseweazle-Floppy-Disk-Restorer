"""
Unit tests for the reconstructed floppy_formatter.reports package.

The package must satisfy the existing call sites in gui/main_window.py and
gui/screens/report_screen.py without those needing changes.
"""

from datetime import datetime

import pytest


def test_public_api_importable():
    import floppy_formatter.reports as r

    for name in [
        "ReportType",
        "StatusLevel",
        "SummaryItem",
        "ReportMetadata",
        "ReportData",
        "ReportGenerator",
        "DARK_THEME",
        "generate_scan_report",
        "generate_recovery_report",
        "generate_diagnostic_report",
        "generate_comparison_report",
    ]:
        assert hasattr(r, name), f"missing public name: {name}"


def test_report_type_has_all_values():
    from floppy_formatter.reports import ReportType

    for name in ["SCAN", "FORMAT", "RECOVERY", "ANALYSIS",
                 "DIAGNOSTIC", "COMPARISON", "BATCH_VERIFY"]:
        assert hasattr(ReportType, name)


def test_status_level_colour_mapping():
    from floppy_formatter.reports import StatusLevel, DARK_THEME

    colours = {StatusLevel.SUCCESS.color(DARK_THEME),
               StatusLevel.WARNING.color(DARK_THEME),
               StatusLevel.ERROR.color(DARK_THEME),
               StatusLevel.INFO.color(DARK_THEME)}
    assert len(colours) == 4  # all distinct
    for c in colours:
        assert c.startswith("#")


def _scan_data():
    from floppy_formatter.reports import (
        ReportData, ReportMetadata, ReportType, SummaryItem, StatusLevel,
    )
    meta = ReportMetadata(
        title="Disk Scan Report",
        subtitle="Scan completed on 2026-08-28 10:00:00",
        report_type=ReportType.SCAN,
        device_path="COM7",
        geometry="80C x 2H x 18S",
    )
    return ReportData(
        metadata=meta,
        summary_items=[
            SummaryItem("Total Sectors", 2880),
            SummaryItem("Good Sectors", 2875, StatusLevel.SUCCESS),
            SummaryItem("Bad Sectors", 5, StatusLevel.ERROR),
        ],
        status=StatusLevel.WARNING,
        status_message="5 bad sectors found",
        raw_data={
            "total_sectors": 2880, "good_sectors": 2875, "bad_sectors": 5,
            "bad_sector_list": [10, 11, 12, 900, 2001],
            "elapsed_ms": 42000, "health_percentage": 99,
        },
    )


@pytest.mark.parametrize("rtype_name", [
    "SCAN", "FORMAT", "RECOVERY", "ANALYSIS", "BATCH_VERIFY",
])
def test_generate_html_for_each_type_tolerates_minimal_data(rtype_name):
    from floppy_formatter.reports import (
        ReportGenerator, ReportData, ReportMetadata, ReportType,
    )
    rtype = getattr(ReportType, rtype_name)
    data = ReportData(metadata=ReportMetadata(title=f"{rtype_name} report",
                                              report_type=rtype))
    html = ReportGenerator(rtype, data).generate_html()
    assert isinstance(html, str) and len(html) > 100
    assert f"{rtype_name} report" in html
    assert "<table" in html.lower()  # Qt-rich-text layout, not flex/grid
    assert "display:flex" not in html.replace(" ", "")
    assert "display:grid" not in html.replace(" ", "")


def test_scan_html_contains_summary_and_status():
    from floppy_formatter.reports import ReportGenerator, ReportType

    html = ReportGenerator(ReportType.SCAN, _scan_data()).generate_html()
    assert "Disk Scan Report" in html
    assert "5 bad sectors found" in html
    for label in ("Total Sectors", "Good Sectors", "Bad Sectors"):
        assert label in html
    assert "COM7" in html


def test_generator_default_theme_and_batch_signature():
    """main_window builds these with no theme and a raw batch object."""
    from floppy_formatter.reports import (
        ReportGenerator, ReportData, ReportMetadata, ReportType,
    )

    class _FakeDiskResult:
        display_grade = "A"
        overall_score = 98.0
        good_sectors = 2880
        bad_sectors = 0
        total_sectors = 2880

        class disk_info:  # noqa: N801
            label = "Disk 1"

    class _FakeBatch:
        disk_results = [_FakeDiskResult(), _FakeDiskResult()]
        disks_verified = 2
        disks_skipped = 0
        disks_failed = 0
        average_score = 98.0
        pass_rate = 100.0
        grade_distribution = {"A": 2, "B": 0, "C": 0, "D": 0, "F": 0, "S": 0}
        start_time = datetime(2026, 8, 28, 10, 0, 0)
        end_time = datetime(2026, 8, 28, 10, 30, 0)
        total_duration_ms = 1800000

    data = ReportData(
        metadata=ReportMetadata(title="Batch Disk Verification Report",
                                report_type=ReportType.BATCH_VERIFY,
                                timestamp=datetime.now()),
        raw_data={"batch_result": _FakeBatch(), "batch_config": {
            "batch_name": "Batch A", "operator": "me", "total_disks": 2,
        }},
    )
    gen = ReportGenerator(ReportType.BATCH_VERIFY, data)  # no theme arg
    html = gen.generate_html()
    assert "Batch Disk Verification Report" in html
    assert "Batch A" in html


def test_dict_function_wrappers_return_html():
    from floppy_formatter.reports import (
        generate_scan_report, generate_recovery_report,
        generate_diagnostic_report, generate_comparison_report,
    )

    scan = generate_scan_report(
        {"total_sectors": 2880, "good_sectors": 2870, "bad_sectors": 10,
         "bad_sector_list": [1, 2, 3], "elapsed_ms": 1000},
        device_path="COM7", geometry="80x2x18",
    )
    assert "<html" in scan.lower() or "<table" in scan.lower()

    rec = generate_recovery_report(
        {"initial_bad": 20, "final_bad": 2, "passes_executed": 5,
         "convergence_history": [{"pass": 1, "bad_sectors": 20}], "elapsed_ms": 5000},
        device_path="COM7", geometry="80x2x18",
    )
    assert "2" in rec

    assert len(generate_diagnostic_report({}, device_path="COM7")) > 50
    assert len(generate_comparison_report({})) > 50


def test_exports_write_files(tmp_path):
    pytest.importorskip("PyQt6.QtPrintSupport")
    from PyQt6.QtWidgets import QApplication
    from floppy_formatter.reports import ReportGenerator, ReportType

    _app = QApplication.instance() or QApplication([])

    gen = ReportGenerator(ReportType.SCAN, _scan_data())

    html_path = tmp_path / "r.html"
    gen.export_html(str(html_path))
    assert html_path.read_text(encoding="utf-8").strip().lower().startswith("<")

    txt_path = tmp_path / "r.txt"
    gen.export_text(str(txt_path))
    assert "Bad Sectors" in txt_path.read_text(encoding="utf-8")

    pdf_path = tmp_path / "r.pdf"
    gen.export_pdf(str(pdf_path))
    assert pdf_path.read_bytes()[:5] == b"%PDF-"
