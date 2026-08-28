"""
Data models for generated operation reports.

These types are the stable contract between the GUI (which fills them in from
operation results) and the report renderers. Keep them permissive: every field
that a caller might omit has a default, and renderers must treat ``raw_data`` as
best-effort.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from .theme import Theme


class ReportType(Enum):
    """Kind of operation a report describes."""

    SCAN = "scan"
    FORMAT = "format"
    RECOVERY = "recovery"
    ANALYSIS = "analysis"
    DIAGNOSTIC = "diagnostic"
    COMPARISON = "comparison"
    BATCH_VERIFY = "batch_verify"


class StatusLevel(Enum):
    """Severity used for the report banner and per-item colouring."""

    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"

    def color(self, theme: "Theme") -> str:
        """Resolve this level to a hex colour from the given theme."""
        return {
            StatusLevel.SUCCESS: theme.success,
            StatusLevel.WARNING: theme.warning,
            StatusLevel.ERROR: theme.error,
            StatusLevel.INFO: theme.primary,
        }[self]

    @property
    def label(self) -> str:
        return self.name.capitalize()


@dataclass
class SummaryItem:
    """A single headline number/value shown in the report's summary grid."""

    label: str
    value: Any
    status: StatusLevel = StatusLevel.INFO


@dataclass
class ReportMetadata:
    """Title block / provenance for a report."""

    title: str
    report_type: ReportType
    subtitle: str = ""
    device_path: str = ""
    geometry: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ReportData:
    """Everything a renderer needs to build one report."""

    metadata: ReportMetadata
    summary_items: List[SummaryItem] = field(default_factory=list)
    status: StatusLevel = StatusLevel.INFO
    status_message: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)
