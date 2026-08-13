"""Headless performance benchmarks for the VisionMoCap pipeline.

Measures the pure-Python stages (filtering, interpolation, retargeting,
BVH export, serialization) on a synthetic sequence so numbers are
reproducible without a camera or a GPU.  The MediaPipe inference stage
is measured only when a model file is available.

Usage::

    python scripts/benchmark_pipeline.py [--frames N] [--warmup W]

Prints a markdown table of throughput (frames/s) and total times.
"""

from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path
from typing import Callable, List

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.animation.avatar_templates import build_mixamo_avatar
from src.animation.bvh_exporter import BvhExporter
from src.animation.csv_exporter import CsvExporter
from src.animation.motion_to_animation import MotionToAnimationConverter
from src.animation.retargeter import Retargeter
from src.animation.skeleton_mapper import SkeletonMapper
from src.core.models import Vector3D
from src.motion.motion_processor import MotionProcessor
from src.motion.motion_sequence import MotionSequence
from src.pose.pose_result import Landmark, PoseResult


# ---------------------------------------------------------------------------
# Synthetic data
# ---------------------------------------------------------------------------


def _make_pose(timestamp: float) -> PoseResult:
    # A plausible standing pose with slight sinusoidal sway so the
    # smoothing filters have real work to do.
    sway = np.sin(timestamp * 2.0) * 0.02
    landmarks = []
    for i in range(33):
        landmarks.append(
            Landmark(
                x=0.5 + 0.1 * np.cos(i) + sway,
                y=0.9 - 0.025 * i + sway,
                z=0.0,
                visibility=0.95,
            )
        )
    return PoseResult(
        timestamp=timestamp,
        landmarks=landmarks,
        world_landmarks=landmarks,
        confidence=0.9,
        frame_width=640,
        frame_height=480,
        pose_detected=True,
    )


def make_sequence(n_frames: int, fps: float = 30.0) -> MotionSequence:
    poses = [_make_pose(i / fps) for i in range(n_frames)]
    return MotionSequence(
        pose_results=poses,
        start_time=0.0,
        end_time=n_frames / fps,
        total_frames=n_frames,
        average_fps=fps,
        duration=n_frames / fps,
    )


# ---------------------------------------------------------------------------
# Benchmark harness
# ---------------------------------------------------------------------------


def _measure(fn: Callable[[], object], warmup: int, runs: int) -> tuple[float, float]:
    """Return (median seconds, best seconds) over *runs* repetitions."""
    for _ in range(warmup):
        fn()
    samples: List[float] = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - t0)
    return statistics.median(samples), min(samples)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=3000,
                        help="number of synthetic frames (default 3000)")
    parser.add_argument("--warmup", type=int, default=1,
                        help="warm-up repetitions per benchmark")
    parser.add_argument("--runs", type=int, default=3,
                        help="measured repetitions per benchmark")
    args = parser.parse_args()

    n = args.frames
    seq = make_sequence(n)
    rows: List[tuple[str, str]] = []

    def add_row(name: str, seconds: float, scale: int = 1) -> None:
        per_frame = seconds / max(n, 1) * 1e3
        rows.append(
            (name, f"{scale / seconds:9.1f}/s", f"{seconds:8.3f}s", f"{per_frame:8.3f} ms/f")
        )

    # 1. Motion processing pipeline (outlier removal → interpolation →
    #    moving average → exponential smoothing).
    processor = MotionProcessor()

    def bench_process() -> None:
        processor.process(seq)

    med, _ = _measure(bench_process, args.warmup, args.runs)
    add_row("MotionProcessor pipeline", med, scale=n)

    # 2. MotionSequence JSON round trip (serialization used by recordings).
    raw = json.dumps(seq.to_dict())

    def bench_serialize() -> None:
        MotionSequence.from_dict(json.loads(raw))

    med, _ = _measure(bench_serialize, args.warmup, args.runs)
    add_row("MotionSequence JSON round trip", med, scale=n)

    # 3. Retargeting onto the Mixamo skeleton.
    mapper = SkeletonMapper(preset="mixamo")
    avatar = build_mixamo_avatar()
    retargeter = Retargeter(mapper=mapper, avatar=avatar)
    processed = processor.process(seq)

    def bench_retarget() -> None:
        retargeter.retarget(processed)

    med, _ = _measure(bench_retarget, args.warmup, args.runs)
    add_row("Retargeting (Mixamo avatar)", med, scale=n)

    # 4. Retarget → AnimationClip.
    converter = MotionToAnimationConverter()

    def bench_convert() -> None:
        converter.convert(processed)

    med, _ = _measure(bench_convert, args.warmup, args.runs)
    add_row("Motion → AnimationClip", med, scale=n)

    # 5. BVH export.
    clip = converter.convert(processed)
    exporter = BvhExporter(avatar=avatar, clip=clip)

    def bench_bvh() -> None:
        with tempfile.TemporaryDirectory() as td:
            exporter.export(Path(td) / "clip.bvh")

    med, _ = _measure(bench_bvh, args.warmup, args.runs)
    add_row("BVH export", med, scale=n)

    # 6. CSV export (pure Python row building — typically the slowest).
    csv_exporter = CsvExporter()

    def bench_csv() -> None:
        with tempfile.TemporaryDirectory() as td:
            csv_exporter.export(processed, Path(td) / "clip.csv")

    med, _ = _measure(bench_csv, args.warmup, args.runs)
    add_row("CSV export", med, scale=n)

    # 7. MotionProcessor on an empty sequence (pipeline overhead).
    empty = make_sequence(0)
    t0 = time.perf_counter()
    for _ in range(100):
        processor.process(empty)
    overhead_ms = (time.perf_counter() - t0) / 100 * 1e3
    rows.append(("Pipeline fixed overhead", "-", "-", f"{overhead_ms:8.3f} ms/run"))

    # ------------------------------------------------------------------
    # MediaPipe inference (only if the model is present).
    # ------------------------------------------------------------------
    try:
        from src.pose.pose_detector import PoseDetector
        detector = PoseDetector()
        detector.initialize()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        def bench_infer() -> None:
            detector.detect(frame)

        med, _ = _measure(bench_infer, args.warmup, args.runs)
        add_row("MediaPipe pose inference (no pose)", med, scale=1)
        detector.shutdown()
    except Exception as e:
        rows.append(("MediaPipe pose inference", "skipped", f"({e})", "-"))

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    print(f"\n# VisionMoCap pipeline benchmark — {n} synthetic frames\n")
    print("| Stage | Throughput | Total | Per frame |")
    print("|-------|------------|-------|-----------|")
    for name, tp, total, per_frame in rows:
        print(f"| {name} | {tp} | {total} | {per_frame} |")
    print(f"\nRun with: python scripts/benchmark_pipeline.py --frames {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
