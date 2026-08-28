"""
Unit tests for drive_control_panel helpers.

The panel used to hardcode drive unit 1 as the default select line, which meant
every operation targeted a non-existent drive on the common single-drive setup
(drive answers on unit 0 = ``gw --drive=A``) and every seek to track 0 failed
with "Track 0 not found". The default now follows the user's setting, which
itself defaults to 0.
"""

import pytest

pytest.importorskip("PyQt6")

from floppy_formatter.gui.panels import drive_control_panel as dcp


def test_default_drive_index_follows_settings(monkeypatch):
    class _Dev:
        default_drive_unit = 1

    class _Settings:
        device = _Dev()

    monkeypatch.setattr(
        "floppy_formatter.core.settings.get_settings", lambda: _Settings()
    )
    assert dcp._default_drive_index() == 1


def test_default_drive_index_defaults_to_zero(monkeypatch):
    class _Dev:
        default_drive_unit = 0

    class _Settings:
        device = _Dev()

    monkeypatch.setattr(
        "floppy_formatter.core.settings.get_settings", lambda: _Settings()
    )
    assert dcp._default_drive_index() == 0


def test_default_drive_index_rejects_out_of_range(monkeypatch):
    class _Dev:
        default_drive_unit = 7

    class _Settings:
        device = _Dev()

    monkeypatch.setattr(
        "floppy_formatter.core.settings.get_settings", lambda: _Settings()
    )
    assert dcp._default_drive_index() == 0


def test_default_drive_index_survives_broken_settings(monkeypatch):
    def _boom():
        raise RuntimeError("settings file corrupt")

    monkeypatch.setattr("floppy_formatter.core.settings.get_settings", _boom)
    assert dcp._default_drive_index() == 0
