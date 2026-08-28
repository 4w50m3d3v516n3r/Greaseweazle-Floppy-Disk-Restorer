"""
Regression tests for main_window's report-data adapters.

The report feature was unreachable for a long time (missing `reports` package),
so its glue in main_window drifted from the current result dataclasses -- e.g.
it read `TrackAnalysisResult.quality_score` / `.grade`, which don't exist
(grade/score live on the optional `.quality` sub-object).
"""

import pytest

pytest.importorskip("PyQt6")

from floppy_formatter.gui.main_window import _analysis_track_rows


class _FakeQuality:
    def __init__(self, score, grade):
        self.score = score
        self.grade = grade  # str() of a QualityGrade enum -> "A".. here just a str


class _FakeTrack:
    def __init__(self, cyl, head, quality):
        self.cylinder = cyl
        self.head = head
        self.quality = quality


def test_track_rows_from_quality_subobject():
    tracks = [
        _FakeTrack(0, 0, _FakeQuality(97.25, "A")),
        _FakeTrack(0, 1, _FakeQuality(61.4, "C")),
    ]
    rows = _analysis_track_rows(tracks)
    assert rows == [
        {"cylinder": 0, "head": 0, "quality_score": 97.2, "grade": "A"},
        {"cylinder": 0, "head": 1, "quality_score": 61.4, "grade": "C"},
    ]


def test_track_rows_handles_missing_quality():
    rows = _analysis_track_rows([_FakeTrack(5, 1, None)])
    assert rows == [{"cylinder": 5, "head": 1, "quality_score": 0.0, "grade": "?"}]


def test_track_rows_empty_and_limit():
    assert _analysis_track_rows(None) == []
    assert _analysis_track_rows([]) == []
    many = [_FakeTrack(i, 0, _FakeQuality(90, "A")) for i in range(50)]
    assert len(_analysis_track_rows(many, limit=20)) == 20


def test_real_dataclasses_have_expected_shape():
    """Guard against another silent rename of the analyze result types."""
    import dataclasses

    from floppy_formatter.gui.workers.analyze_worker import (
        TrackAnalysisResult, DiskAnalysisResult,
    )

    track_fields = {f.name for f in dataclasses.fields(TrackAnalysisResult)}
    assert "quality" in track_fields
    assert "quality_score" not in track_fields  # the trap we fell into

    disk_fields = {f.name for f in dataclasses.fields(DiskAnalysisResult)}
    for name in ("overall_grade", "overall_quality_score", "format_type",
                 "is_copy_protected", "protection_types", "recommendations",
                 "track_results"):
        assert name in disk_fields
    assert hasattr(DiskAnalysisResult, "get_grade_distribution")
