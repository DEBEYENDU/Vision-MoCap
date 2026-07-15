"""Unit tests for CSV and NPY exporters."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path
from typing import List

import numpy as np

from src.animation.csv_exporter import CsvExporter
from src.animation.npy_exporter import NpyExporter
from src.motion.motion_sequence import MotionSequence
from src.pose.pose_result import Landmark, PoseResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_landmarks(count: int = 33) -> List[Landmark]:
    return [
        Landmark(x=float(i), y=float(i * 2), z=float(i * 3), visibility=0.9)
        for i in range(count)
    ]


def _make_pose(timestamp: float) -> PoseResult:
    return PoseResult(
        timestamp=timestamp,
        landmarks=_make_landmarks(),
        world_landmarks=_make_landmarks(),
        confidence=0.85,
        frame_width=640,
        frame_height=480,
        pose_detected=True,
    )


def _make_sequence(n_frames: int = 5) -> MotionSequence:
    return MotionSequence(
        pose_results=[_make_pose(t) for t in range(n_frames)],
        start_time=0.0,
        end_time=float(n_frames - 1),
        total_frames=n_frames,
        average_fps=30.0,
        duration=float(n_frames - 1),
    )


# ---------------------------------------------------------------------------
# CSV Tests
# ---------------------------------------------------------------------------


class TestCsvExporter:
    def test_export_creates_file(self) -> None:
        seq = _make_sequence()
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            p = Path(f.name)
        try:
            CsvExporter().export(seq, p)
            assert p.exists()
            assert p.stat().st_size > 0
        finally:
            p.unlink()

    def test_export_header(self) -> None:
        seq = _make_sequence(1)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            p = Path(f.name)
        try:
            CsvExporter().export(seq, p)
            with open(p, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)
            assert header[0] == "frame"
            assert header[1] == "timestamp"
            assert header[2] == "lm_0_x"
            assert header[5] == "lm_0_visibility"
            assert header[-1] == "lm_32_visibility"
        finally:
            p.unlink()

    def test_export_row_count(self) -> None:
        n = 7
        seq = _make_sequence(n)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            p = Path(f.name)
        try:
            CsvExporter().export(seq, p)
            with open(p, newline="", encoding="utf-8") as f:
                lines = list(csv.reader(f))
            assert len(lines) == n + 1  # header + n data rows
        finally:
            p.unlink()

    def test_export_column_count(self) -> None:
        seq = _make_sequence(1)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            p = Path(f.name)
        try:
            CsvExporter().export(seq, p)
            with open(p, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader)
                row = next(reader)
            expected = 2 + 33 * 4  # frame, timestamp, 33*4
            assert len(row) == expected
        finally:
            p.unlink()

    def test_export_empty_raises(self) -> None:
        seq = _make_sequence(0)
        try:
            CsvExporter().export(seq, Path("dummy.csv"))
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_export_data_values(self) -> None:
        seq = _make_sequence(2)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            p = Path(f.name)
        try:
            CsvExporter().export(seq, p)
            with open(p, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader)
                row0 = next(reader)
                row1 = next(reader)
            assert float(row0[0]) == 0.0  # frame index
            assert float(row1[0]) == 1.0
            assert float(row0[1]) == 0.0  # timestamp
            assert float(row1[1]) == 1.0
        finally:
            p.unlink()


# ---------------------------------------------------------------------------
# NPY Tests
# ---------------------------------------------------------------------------


class TestNpyExporter:
    def test_export_creates_file(self) -> None:
        seq = _make_sequence()
        with tempfile.NamedTemporaryFile(suffix=".npy", delete=False) as f:
            p = Path(f.name)
        try:
            NpyExporter().export(seq, p)
            assert p.exists()
            assert p.stat().st_size > 0
        finally:
            p.unlink()

    def test_export_shape(self) -> None:
        n = 4
        seq = _make_sequence(n)
        with tempfile.NamedTemporaryFile(suffix=".npy", delete=False) as f:
            p = Path(f.name)
        try:
            NpyExporter().export(seq, p)
            data = np.load(str(p))
            expected_cols = 2 + 33 * 4
            assert data.shape == (n, expected_cols)
        finally:
            p.unlink()

    def test_export_roundtrip_values(self) -> None:
        seq = _make_sequence(3)
        with tempfile.NamedTemporaryFile(suffix=".npy", delete=False) as f:
            p = Path(f.name)
        try:
            NpyExporter().export(seq, p)
            data = np.load(str(p))
            assert data[0, 0] == 0.0  # frame index
            assert data[1, 0] == 1.0
            assert data[0, 1] == 0.0  # timestamp
            assert data[1, 1] == 1.0
            # lm_0_x = 0, lm_0_y = 0, lm_1_x = 1, lm_1_y = 2
            assert data[0, 2] == 0.0  # lm_0_x
            assert data[0, 3] == 0.0  # lm_0_y
            assert data[0, 6] == 1.0  # lm_1_x
            assert data[0, 7] == 2.0  # lm_1_y
        finally:
            p.unlink()

    def test_export_empty_raises(self) -> None:
        seq = _make_sequence(0)
        try:
            NpyExporter().export(seq, Path("dummy.npy"))
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
