"""
Per-report-type body renderers.

``render_body(report_type, data, theme)`` returns the inner HTML for a report
(everything between the title block and the document end). Every reader of
``data.raw_data`` is defensive: missing keys degrade to a sensible default
rather than raising, because the GUI populates ``raw_data`` from many different
result objects.
"""

from __future__ import annotations

from typing import Any, Dict

from . import html as H
from .models import ReportData, ReportType
from .theme import Theme


def _rd(data: ReportData) -> Dict[str, Any]:
    return data.raw_data or {}


def _ms_to_str(ms: Any) -> str:
    try:
        seconds = float(ms) / 1000.0
    except (TypeError, ValueError):
        return "-"
    if seconds < 60:
        return f"{seconds:.1f} s"
    return f"{int(seconds // 60)} min {int(seconds % 60)} s"


def _sector_maps(data: ReportData, theme: Theme) -> str:
    rd = _rd(data)
    out = []
    for key, caption in (
        ("sector_map_h0_image", "Head 0"),
        ("sector_map_h1_image", "Head 1"),
        ("sector_map_image", "Sector map"),
    ):
        uri = rd.get(key)
        if uri:
            out.append(H.heading(caption, 2))
            out.append(H.image(uri))
    return "\n".join(out)


def _bad_sector_table(theme: Theme, bad_list: Any, limit: int = 200) -> str:
    if not bad_list:
        return ""
    nums = []
    for entry in bad_list:
        if isinstance(entry, dict):
            nums.append(entry.get("sector", entry.get("lba", "?")))
        else:
            nums.append(entry)
    shown = nums[:limit]
    body = H.paragraph(", ".join(str(n) for n in shown))
    if len(nums) > limit:
        body += H.paragraph(
            f"... and {len(nums) - limit} more", dim=True, theme=theme
        )
    return H.heading("Bad Sectors", 2) + body


# --------------------------------------------------------------------------- #
# Individual report bodies
# --------------------------------------------------------------------------- #

def _scan_body(data: ReportData, theme: Theme) -> str:
    rd = _rd(data)
    details = H.key_values(theme, [
        ("Total sectors", rd.get("total_sectors", "-")),
        ("Good sectors", rd.get("good_sectors", "-")),
        ("Bad sectors", rd.get("bad_sectors", "-")),
        ("Disk health", f"{rd.get('health_percentage', '-')}%"),
        ("Elapsed", _ms_to_str(rd.get("elapsed_ms"))),
    ])
    return "\n".join(filter(None, [
        H.heading("Scan Details", 2), details,
        _sector_maps(data, theme),
        _bad_sector_table(theme, rd.get("bad_sector_list")),
    ]))


def _format_body(data: ReportData, theme: Theme) -> str:
    rd = _rd(data)
    details = H.key_values(theme, [
        ("Total tracks", rd.get("total_tracks", "-")),
        ("Tracks formatted", rd.get("tracks_formatted", "-")),
        ("Tracks failed", rd.get("tracks_failed", "-")),
        ("Verify passed", "Yes" if rd.get("verify_passed", True) else "No"),
        ("Result", "Success" if rd.get("success") else "Failed"),
    ])
    body = [H.heading("Format Details", 2), details, _sector_maps(data, theme)]
    bad = rd.get("bad_sectors")
    if isinstance(bad, (list, tuple)) and bad:
        body.append(_bad_sector_table(theme, bad))
    return "\n".join(filter(None, body))


def _recovery_body(data: ReportData, theme: Theme) -> str:
    rd = _rd(data)
    details = H.key_values(theme, [
        ("Initial bad sectors", rd.get("initial_bad", "-")),
        ("Final bad sectors", rd.get("final_bad", "-")),
        ("Sectors recovered", rd.get("sectors_recovered", "-")),
        ("Passes executed", rd.get("passes_executed", rd.get("passes", "-"))),
        ("Converged", "Yes" if rd.get("converged") else "No"),
        ("Recovery rate", f"{rd.get('recovery_percentage', '-')}%"),
        ("Elapsed", _ms_to_str(rd.get("elapsed_ms"))),
    ])
    out = [H.heading("Recovery Details", 2), details]

    history = rd.get("convergence_history") or []
    if history:
        rows = []
        for point in history:
            if isinstance(point, dict):
                rows.append((point.get("pass", "?"), point.get("bad_sectors", "?")))
            else:
                rows.append(point)
        out.append(H.heading("Convergence", 2))
        out.append(H.table(theme, ["Pass", "Bad sectors"], rows))

    out.append(_sector_maps(data, theme))
    return "\n".join(filter(None, out))


def _analysis_body(data: ReportData, theme: Theme) -> str:
    rd = _rd(data)
    details = H.key_values(theme, [
        ("Overall grade", rd.get("overall_grade", "-")),
        ("Quality score", f"{rd.get('overall_quality_score', '-')}"),
        ("Format type", rd.get("format_type", "Unknown")),
        ("Standard format", "Yes" if rd.get("format_is_standard") else "No"),
        ("Copy protected", "Yes" if rd.get("is_copy_protected") else "No"),
        ("Protected tracks", rd.get("protected_track_count", 0)),
    ])
    out = [H.heading("Analysis Details", 2), details]

    grade_dist = rd.get("grade_distribution") or {}
    if grade_dist:
        rows = [(g, grade_dist.get(g, 0)) for g in ["A", "B", "C", "D", "F"]]
        out.append(H.heading("Grade Distribution", 2))
        out.append(H.table(theme, ["Grade", "Tracks"], rows))

    protections = rd.get("protection_types") or []
    if protections:
        out.append(H.heading("Detected Protection", 2))
        out.append(H.paragraph(", ".join(str(p) for p in protections)))

    recs = rd.get("recommendations") or []
    if recs:
        out.append(H.heading("Recommendations", 2))
        out.append("<ul>" + "".join(f"<li>{H.escape(r)}</li>" for r in recs) + "</ul>")

    track_results = rd.get("track_results") or []
    if track_results:
        rows = [
            (t.get("cylinder"), t.get("head"), t.get("grade"),
             f"{t.get('quality_score', '-')}")
            for t in track_results if isinstance(t, dict)
        ]
        if rows:
            out.append(H.heading("Per-Track (first rows)", 2))
            out.append(H.table(theme, ["Cyl", "Head", "Grade", "Score"], rows))

    return "\n".join(filter(None, out))


def _batch_body(data: ReportData, theme: Theme) -> str:
    rd = _rd(data)
    config = rd.get("batch_config") or {}
    result = rd.get("batch_result")

    cfg_rows = [(k.replace("_", " ").title(), v) for k, v in config.items()]
    out = [H.heading("Batch Configuration", 2), H.key_values(theme, cfg_rows)]

    if result is not None:
        g = getattr(result, "grade_distribution", {}) or {}
        out.append(H.heading("Summary", 2))
        out.append(H.key_values(theme, [
            ("Disks verified", getattr(result, "disks_verified", "-")),
            ("Disks skipped", getattr(result, "disks_skipped", "-")),
            ("Disks failed", getattr(result, "disks_failed", "-")),
            ("Average score", f"{getattr(result, 'average_score', '-')}"),
            ("Pass rate", f"{getattr(result, 'pass_rate', '-')}%"),
            ("Total time", _ms_to_str(getattr(result, "total_duration_ms", None))),
        ]))
        if g:
            out.append(H.table(
                theme, ["Grade", "Count"],
                [(k, g.get(k, 0)) for k in ["A", "B", "C", "D", "F", "S"]],
            ))

        disk_rows = []
        for idx, disk in enumerate(getattr(result, "disk_results", []) or [], 1):
            info = getattr(disk, "disk_info", None)
            label = getattr(info, "label", None) or getattr(info, "name", None) or f"Disk {idx}"
            disk_rows.append((
                idx, label,
                getattr(disk, "display_grade", getattr(disk, "grade", "-")),
                f"{getattr(disk, 'overall_score', '-')}",
                getattr(disk, "good_sectors", "-"),
                getattr(disk, "bad_sectors", "-"),
            ))
        if disk_rows:
            out.append(H.heading("Per-Disk Results", 2))
            out.append(H.table(
                theme, ["#", "Disk", "Grade", "Score", "Good", "Bad"], disk_rows,
            ))

    return "\n".join(filter(None, out))


def _diagnostic_body(data: ReportData, theme: Theme) -> str:
    rd = _rd(data)
    if not rd:
        return H.paragraph("Diagnostic data not available.")
    rows = [(k.replace("_", " ").title(), v) for k, v in rd.items()
            if not isinstance(v, (list, dict))]
    return H.heading("Diagnostics", 2) + H.key_values(theme, rows)


def _comparison_body(data: ReportData, theme: Theme) -> str:
    rd = _rd(data)
    if not rd:
        return H.paragraph("Comparison data not available.")
    rows = [(k.replace("_", " ").title(), v) for k, v in rd.items()
            if not isinstance(v, (list, dict))]
    return H.heading("Comparison", 2) + H.key_values(theme, rows)


_BODIES = {
    ReportType.SCAN: _scan_body,
    ReportType.FORMAT: _format_body,
    ReportType.RECOVERY: _recovery_body,
    ReportType.ANALYSIS: _analysis_body,
    ReportType.BATCH_VERIFY: _batch_body,
    ReportType.DIAGNOSTIC: _diagnostic_body,
    ReportType.COMPARISON: _comparison_body,
}


def render_body(report_type: ReportType, data: ReportData, theme: Theme) -> str:
    renderer = _BODIES.get(report_type, _diagnostic_body)
    return renderer(data, theme)
