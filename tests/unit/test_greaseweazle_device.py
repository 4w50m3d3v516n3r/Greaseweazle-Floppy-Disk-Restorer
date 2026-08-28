"""
Unit tests for the Greaseweazle device wrapper (hardware.greaseweazle_device).

These focus on the serial-transport contract with greaseweazle.usb.Unit:

* The Greaseweazle wire protocol is written for *blocking* reads -- every
  ``_send_cmd()`` does ``ser.read(2)`` and expects to wait for the ack.  A
  finite pyserial ``timeout`` causes short reads on any command that takes
  longer than the timeout to acknowledge (a long seek, motor spin-up), which
  then desyncs the stream permanently ("Command returned garbage (00 != xx)").
  ``greaseweazle.tools.util.usb_open`` opens the port with no timeout; we must
  do the same.

* If opening fails part-way (the Unit handshake desyncs, ``set_bus_type``
  raises), the OS serial handle must still be released, otherwise the next
  ``connect()`` fails with "Access is denied" on the same COM port.
"""

import pytest

pytest.importorskip("greaseweazle")

import floppy_formatter.hardware.greaseweazle_device as gwd
from floppy_formatter.hardware.greaseweazle_device import (
    GreaseweazleDevice,
    greaseweazle_model_name,
)
from floppy_formatter.hardware import ConnectionError as GWConnectionError
from floppy_formatter.hardware.flux_io import DEFAULT_SAMPLE_FREQ


class _FakeSerial:
    """Minimal stand-in for pyserial.Serial."""

    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs
        self.timeout = kwargs.get("timeout", None)
        self.closed_count = 0
        self.baudrate = 9600
        self.in_waiting = 0

    def close(self):
        self.closed_count += 1

    def open(self):
        pass

    def reset_input_buffer(self):
        pass

    def reset_output_buffer(self):
        pass

    def read(self, n=1):
        return b""


def test_open_serial_uses_blocking_reads(monkeypatch):
    """The port must be opened for blocking reads (timeout=None), matching
    greaseweazle.tools.util.usb_open()."""
    import serial

    captured = {}

    class SpySerial(_FakeSerial):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            captured["args"] = args
            captured["kwargs"] = kwargs

    monkeypatch.setattr(serial, "Serial", SpySerial)

    ser = GreaseweazleDevice._open_serial("COM_TEST")

    # Blocking reads: the greaseweazle protocol depends on ser.read(2) waiting
    # for the acknowledgement rather than returning a short buffer.
    assert getattr(ser, "timeout", "missing") is None
    assert captured["kwargs"].get("timeout") in (None,)

    # Port name is forwarded.
    port = captured["args"][0] if captured["args"] else captured["kwargs"].get("port")
    assert port == "COM_TEST"

    # No bogus 115200 baud override -- meaningless on a USB-CDC device.
    assert captured["kwargs"].get("baudrate") in (None, 9600)


def test_open_device_direct_closes_serial_if_handshake_fails(monkeypatch):
    """If greaseweazle.usb.Unit(ser) raises during its handshake, the serial
    handle we just opened must be closed before the error propagates."""
    fake_ser = _FakeSerial()

    monkeypatch.setattr(GreaseweazleDevice, "_open_serial",
                        staticmethod(lambda path: fake_ser))

    def boom(_ser):
        raise RuntimeError("unpack requires a buffer of 2 bytes")

    monkeypatch.setattr(gwd.gw_usb, "Unit", boom)

    device = GreaseweazleDevice()
    with pytest.raises(GWConnectionError):
        device._open_device_direct("COM_TEST")

    assert fake_ser.closed_count >= 1, "serial handle leaked on failed handshake"


def test_connect_closes_serial_if_setup_fails(monkeypatch):
    """A failure after the Unit is created (e.g. set_bus_type desyncs) must not
    leak the port -- the next connect() would otherwise hit 'Access is denied'."""
    fake_ser = _FakeSerial()

    class FakeUnit:
        def __init__(self, ser):
            self.ser = ser
            self.hw_model = 4
            self.hw_submodel = 2
            self.major = 1
            self.minor = 6
            self.version = (1, 6)

        def set_bus_type(self, bus_type):
            raise RuntimeError("Command returned garbage (00 != 08)")

        def reset(self):
            pass

    monkeypatch.setattr(GreaseweazleDevice, "_open_serial",
                        staticmethod(lambda path: fake_ser))
    monkeypatch.setattr(gwd.gw_usb, "Unit", FakeUnit)
    monkeypatch.setattr(GreaseweazleDevice, "_find_greaseweazle_port",
                        lambda self: "COM_TEST")

    device = GreaseweazleDevice()
    with pytest.raises(GWConnectionError):
        device.connect()

    assert fake_ser.closed_count >= 1, "serial handle leaked on failed connect()"
    assert device._unit is None
    assert device.is_connected() is False


def test_disconnect_is_idempotent_and_closes_handle(monkeypatch):
    fake_ser = _FakeSerial()

    class FakeUnit:
        def __init__(self):
            self.ser = fake_ser

        def drive_motor(self, unit, state):
            raise RuntimeError("Command returned garbage (00 != 06)")

        def drive_deselect(self):
            raise RuntimeError("Command returned garbage (00 != 0d)")

        def drive_select(self, unit):
            pass

        def reset(self):
            pass

    device = GreaseweazleDevice()
    device._unit = FakeUnit()
    device._selected_drive = 1
    device._motor_running = True

    device.disconnect()
    device.disconnect()  # no-op, must not raise

    assert fake_ser.closed_count >= 1
    assert device._unit is None


# ---------------------------------------------------------------------------
# Hardware model identification
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("hw_model, hw_submodel, expected", [
    (4, 0, "Greaseweazle V4"),
    (4, 1, "Greaseweazle V4 Slim"),
    (4, 2, "Greaseweazle V4.1"),
    (1, 0, "Greaseweazle F1"),
    (7, 7, 'Greaseweazle F7 v3 "Thunderbolt"'),
    (8, 0, "Adafruit Floppy Generic"),      # no "Greaseweazle " prefix
    (9, 9, "Unknown (0x0909)"),             # board newer than the table
    (4, 99, "Unknown (0x0463)"),            # unknown submodel
])
def test_greaseweazle_model_name(hw_model, hw_submodel, expected):
    assert greaseweazle_model_name(hw_model, hw_submodel) == expected


class _InfoUnit:
    def __init__(self, **kw):
        self.hw_model = kw.get("hw_model", 4)
        self.hw_submodel = kw.get("hw_submodel", 2)
        self.major = kw.get("major", 1)
        self.minor = kw.get("minor", 6)
        self.version = (self.major, self.minor)
        self.sample_freq = kw.get("sample_freq", 72_000_000)
        self.update_mode = kw.get("update_mode", False)
        if "update_needed" in kw:
            self.update_needed = kw["update_needed"]


def test_model_and_firmware_properties():
    dev = GreaseweazleDevice()
    assert dev.model_name == "Greaseweazle (not connected)"
    assert dev.firmware_version is None

    dev._unit = _InfoUnit(hw_model=4, hw_submodel=2, major=1, minor=6)
    assert dev.model_name == "Greaseweazle V4.1"
    assert dev.firmware_version == (1, 6)
    assert "V4.1" in dev._get_device_info_string()
    assert "1.6" in dev._get_device_info_string()


def test_sample_freq_property_falls_back_when_not_connected():
    dev = GreaseweazleDevice()
    assert dev.sample_freq == DEFAULT_SAMPLE_FREQ

    dev._unit = _InfoUnit(sample_freq=24_000_000)
    assert dev.sample_freq == 24_000_000

    dev._unit = _InfoUnit(sample_freq=0)  # bogus / missing report
    assert dev.sample_freq == DEFAULT_SAMPLE_FREQ


# ---------------------------------------------------------------------------
# Firmware guard
# ---------------------------------------------------------------------------

def test_check_firmware_rejects_bootloader_mode():
    dev = GreaseweazleDevice()
    dev._unit = _InfoUnit(update_mode=True)
    with pytest.raises(GWConnectionError):
        dev._check_firmware()


def test_check_firmware_rejects_too_old_firmware():
    dev = GreaseweazleDevice()
    dev._unit = _InfoUnit(major=0, minor=20, update_needed=True)
    with pytest.raises(GWConnectionError):
        dev._check_firmware()


def test_check_firmware_warns_but_allows_old_firmware():
    dev = GreaseweazleDevice()
    dev._unit = _InfoUnit(major=1, minor=3)  # below RECOMMENDED_FIRMWARE (1, 6)
    dev._check_firmware()  # must not raise
    assert dev.firmware_warning is not None
    assert "1.3" in dev.firmware_warning


def test_check_firmware_clean_for_current_firmware():
    dev = GreaseweazleDevice()
    dev._unit = _InfoUnit(major=1, minor=6)
    dev._check_firmware()
    assert dev.firmware_warning is None


# ---------------------------------------------------------------------------
# Seek: "Track 0 not found" -> actionable error
# ---------------------------------------------------------------------------

class _NoTrk0Unit:
    """Fake unit whose seek() fails the way the firmware does when no drive
    responds on the selected unit."""

    def __init__(self):
        self.ser = _FakeSerial()

    def drive_select(self, unit):
        pass

    def seek(self, cyl, head):
        raise RuntimeError("Seek: Track 0 not found")

    def reset(self):
        pass


def test_seek_translates_track0_error_to_actionable_message():
    from floppy_formatter.hardware import SeekError

    dev = GreaseweazleDevice()
    dev._unit = _NoTrk0Unit()
    dev._selected_drive = 1
    dev._current_cylinder = 5  # force an actual seek

    with pytest.raises(SeekError) as excinfo:
        dev.seek(0, 0)

    msg = str(excinfo.value)
    # Names the unit that failed and points at the other one + cable/jumper.
    assert "unit 1" in msg
    assert "unit 0" in msg
    assert "jumper" in msg.lower() or "cable" in msg.lower()
    # Original firmware text is preserved for diagnostics.
    assert "Track 0 not found" in msg
