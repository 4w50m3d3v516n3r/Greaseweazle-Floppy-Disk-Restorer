"""
Regression test: the Write Image operation must pause RPM polling.

Every worker-thread operation (scan/format/restore/analyze) calls
``drive_control.pause_rpm_polling()`` before starting its QThread, because the
drive-control panel's 500 ms ``_rpm_timer`` polls ``device.try_get_rpm()`` ->
``Unit.read_track()`` on the GUI thread. If that keeps firing while a worker
thread drives the same pyserial port, the two threads interleave bytes on the
wire and the Greaseweazle command protocol desyncs permanently -- every command
then fails with "Command returned garbage (xx != yy)".

``write_image`` used to slip through: ``_on_start_clicked`` early-returns for it
*before* reaching the shared ``pause_rpm_polling()`` call, and
``_start_write_image_operation`` never paused it either.
"""

from unittest.mock import MagicMock

import pytest

pytest.importorskip("PyQt6")

from floppy_formatter.gui import main_window


def test_start_write_image_pauses_rpm_polling(monkeypatch):
    # Dialog: pretend the user accepted with a usable format spec.
    fake_dialog = MagicMock()
    fake_dialog.exec.return_value = 1
    fake_dialog.DialogCode.Accepted = 1
    fake_dialog.get_config.return_value = MagicMock(
        format_spec=MagicMock(name="1.44MB HD", total_sectors=2880, total_tracks=160),
        verify_after_write=True,
    )
    monkeypatch.setattr(
        main_window, "WriteImageConfigDialog", lambda *a, **k: fake_dialog
    )

    # Don't spin up a real thread / worker / serial link.
    monkeypatch.setattr(main_window, "QThread", MagicMock())
    monkeypatch.setattr(main_window, "DiskImageWorker", MagicMock())

    win = MagicMock()
    main_window.MainWindow._start_write_image_operation(win)

    win._drive_control.pause_rpm_polling.assert_called_once()

    # ...and it must light up the Progress tab / enter the operation state, the
    # bookkeeping _on_start_clicked does for every other operation but skips here.
    assert win._state == main_window.WorkbenchState.WRITING_IMAGE
    win._operation_toolbar.start_operation.assert_called_once()
    assert win._analytics_panel.start_progress.call_args[0][0] == "write_image"


def test_cancelled_write_image_dialog_leaves_polling_resumed(monkeypatch):
    fake_dialog = MagicMock()
    fake_dialog.exec.return_value = 0  # rejected
    fake_dialog.DialogCode.Accepted = 1
    monkeypatch.setattr(
        main_window, "WriteImageConfigDialog", lambda *a, **k: fake_dialog
    )
    monkeypatch.setattr(main_window, "QThread", MagicMock())
    monkeypatch.setattr(main_window, "DiskImageWorker", MagicMock())

    win = MagicMock()
    main_window.MainWindow._start_write_image_operation(win)

    win._drive_control.resume_rpm_polling.assert_called_once()
