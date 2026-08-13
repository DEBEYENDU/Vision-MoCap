"""Unit tests for the camera manager (src/camera/manager.py).

OpenCV is mocked out entirely so tests run headless and deterministic.
"""

from __future__ import annotations

import pytest

from src.camera.backend import Backend
from src.camera.manager import CameraManager, _backend_order, _FPSMonitor
from src.config.manager import CameraConfig
from src.core.exceptions import CameraError


class FakeCapture:
    """A minimal stand-in for cv2.VideoCapture."""

    def __init__(
        self,
        is_opened: bool = True,
        frame_shape=(480, 640, 3),
        read_ok: bool = True,
        fps: float = 30.0,
        fail_reads_after: int = -1,
    ) -> None:
        self._is_opened = is_opened
        self._shape = frame_shape
        self._read_ok = read_ok
        self._fps = fps
        self._fail_after = fail_reads_after
        self.released = False
        self.reads = 0

    def isOpened(self) -> bool:
        return self._is_opened

    def read(self) -> tuple[bool, object]:
        self.reads += 1
        if not self._read_ok:
            return False, None
        if 0 <= self._fail_after < self.reads:
            return False, None
        import numpy as np
        return True, np.zeros(self._shape, dtype=np.uint8)

    def release(self) -> None:
        self.released = True

    def get(self, prop_id: int) -> float:
        if prop_id == 5:  # CAP_PROP_FPS
            return self._fps
        return 0.0

    def set(self, prop_id: int, value: float) -> bool:
        return True


class FakeCv2:
    """Replaces the cv2 module namespace for the manager."""

    def __init__(self, factory, error_type=None) -> None:
        self._factory = factory
        self.VideoCapture = factory
        self.CAP_ANY = 0
        self.CAP_DSHOW = 700
        self.CAP_MSMF = 1400
        self.CAP_PROP_FPS = 5
        self.CAP_PROP_FRAME_WIDTH = 3
        self.CAP_PROP_FRAME_HEIGHT = 4
        self.CAP_PROP_DEVICE_DESCRIPTION = 21
        self.error = error_type or Exception
        self._log = []

    def error_exception(self, msg: str):
        return self.error(msg)


class TestBackendOrder:
    def test_configured_backend_first_then_any(self) -> None:
        cfg = CameraConfig(backend="msmf")
        order = _backend_order(cfg)
        assert order == [Backend.MEDIA_FOUNDATION, Backend.ANY]

    def test_invalid_backend_falls_back_to_directshow(self) -> None:
        cfg = CameraConfig(backend="bogus")
        order = _backend_order(cfg)
        assert order == [Backend.DIRECTSHOW, Backend.ANY]

    def test_any_backend_not_duplicated(self) -> None:
        cfg = CameraConfig(backend="any")
        order = _backend_order(cfg)
        assert order == [Backend.ANY]


class TestOpenCamera:
    def test_negative_index_raises(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "src.camera.manager.cv2", FakeCv2(lambda i, b: FakeCapture())
        )
        manager = CameraManager()
        with pytest.raises(CameraError, match="non-negative"):
            manager.open_camera(-1)

    def test_falls_back_when_configured_backend_fails(self, monkeypatch) -> None:
        captures = []

        def factory(index, backend):
            cap = FakeCapture(is_opened=backend == Backend.ANY)
            captures.append((index, backend))
            return cap

        monkeypatch.setattr("src.camera.manager.cv2", FakeCv2(factory))
        monkeypatch.setattr("src.camera.manager._warmup_camera", lambda i: None)

        cfg = CameraConfig(backend="msmf")
        manager = CameraManager(config=cfg)
        assert manager.open_camera(3) is True
        assert manager.get_current_camera() is not None
        assert manager.get_current_camera().backend is Backend.ANY
        backends = [b for _, b in captures]
        assert backends == [Backend.MEDIA_FOUNDATION, Backend.ANY]

    def test_all_backends_fail_raises(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "src.camera.manager.cv2",
            FakeCv2(lambda i, b: FakeCapture(is_opened=False)),
        )
        manager = CameraManager()
        with pytest.raises(CameraError, match="did not respond"):
            manager.open_camera(1)

    def test_first_backend_succeeds(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "src.camera.manager.cv2", FakeCv2(lambda i, b: FakeCapture())
        )
        manager = CameraManager()
        assert manager.open_camera(0) is True

    def test_open_sets_last_opened_index(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "src.camera.manager.cv2", FakeCv2(lambda i, b: FakeCapture())
        )
        manager = CameraManager()
        manager.open_camera(2)
        assert manager._last_opened_index == 2


class TestReconnect:
    def test_reconnect_reopens_last_camera(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "src.camera.manager.cv2", FakeCv2(lambda i, b: FakeCapture())
        )
        manager = CameraManager()
        manager.open_camera(4)
        manager.close_camera()
        assert manager.reconnect() is True
        assert manager.get_current_camera() is not None
        assert manager.get_current_camera().index == 4

    def test_reconnect_without_history_returns_false(self) -> None:
        manager = CameraManager()
        assert manager.reconnect() is False

    def test_reconnect_when_open_fails_returns_false(self, monkeypatch) -> None:
        manager = CameraManager()
        manager._last_opened_index = 1
        monkeypatch.setattr(
            "src.camera.manager.cv2",
            FakeCv2(lambda i, b: FakeCapture(is_opened=False)),
        )
        assert manager.reconnect() is False


class TestDiscoverCameras:
    def test_respects_max_camera_index_cap(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "src.camera.manager.cv2", FakeCv2(lambda i, b: FakeCapture())
        )
        monkeypatch.setattr("src.camera.manager._warmup_camera", lambda i: None)
        cfg = CameraConfig(max_camera_index=3)
        manager = CameraManager(config=cfg)
        devices = manager.discover_cameras()
        assert len(devices) == 3
        assert manager.get_current_camera() is not None
        assert manager.get_current_camera().index == 0

    def test_cap_maximum_of_ten(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "src.camera.manager.cv2", FakeCv2(lambda i, b: FakeCapture())
        )
        cfg = CameraConfig(max_camera_index=999)
        manager = CameraManager(config=cfg)
        devices = manager.discover_cameras()
        assert len(devices) == 10

    def test_no_working_camera_returns_unavailable_devices(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "src.camera.manager.cv2",
            FakeCv2(lambda i, b: FakeCapture(is_opened=False)),
        )
        manager = CameraManager()
        devices = manager.discover_cameras()
        assert len(devices) >= 1
        assert all(not d.is_available for d in devices)
        assert manager.get_current_camera() is None

    def test_probe_cv2_error_does_not_raise(self, monkeypatch) -> None:
        class CvError(Exception):
            pass

        def factory(index, backend):
            raise CvError("simulated open failure")

        monkeypatch.setattr(
            "src.camera.manager.cv2",
            FakeCv2(factory, error_type=CvError),
        )
        manager = CameraManager()
        device, cap, frame = manager._probe_capture(0, [Backend.DIRECTSHOW, Backend.ANY])
        assert cap is None and frame is None
        assert not device.is_available


class TestGetFrame:
    def test_no_open_camera_raises(self) -> None:
        manager = CameraManager()
        with pytest.raises(CameraError, match="No camera is open"):
            manager.get_frame()

    def test_returns_frame(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "src.camera.manager.cv2", FakeCv2(lambda i, b: FakeCapture())
        )
        manager = CameraManager()
        manager.open_camera(0)
        frame = manager.get_frame()
        assert frame is not None
        assert frame.shape == (480, 640, 3)

    def test_read_failure_returns_none(self, monkeypatch) -> None:
        # The camera probes OK during open_camera (read #1, plus one
        # junk-frame read), then starts failing on subsequent reads.
        monkeypatch.setattr(
            "src.camera.manager.cv2",
            FakeCv2(lambda i, b: FakeCapture(fail_reads_after=1)),
        )
        manager = CameraManager()
        manager.open_camera(0)
        assert manager.get_frame() is None


class TestFPSMonitor:
    def test_empty_monitor_returns_zero(self) -> None:
        mon = _FPSMonitor()
        assert mon.current_fps == 0.0
        assert mon.average_fps == 0.0
        assert mon.min_fps == 0.0
        assert mon.max_fps == 0.0

    def test_reset_clears(self) -> None:
        mon = _FPSMonitor()
        mon.tick()
        mon.reset()
        assert mon.current_fps == 0.0
