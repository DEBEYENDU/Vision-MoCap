"""QA end-to-end driver — drives the real AppController pipeline.

Steps 2-5 + Step 8 of the final QA: real webcam, real MediaPipe pose
detection, real recording, playback-vs-recording comparison, animation
creation, BVH/CSV/NPY export, and file-handle verification.

Usage: python tools/qa_pipeline.py [--record-seconds 5]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.manager import AppConfig
from src.gui.app_controller import AppController

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}" + (f"  ({detail})" if detail else ""))
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def main() -> int:
    global PASS, FAIL
    parser = argparse.ArgumentParser()
    parser.add_argument("--record-seconds", type=float, default=6.0)
    parser.add_argument("--use-legacy", action="store_true",
                        help="force legacy mocap clip for downstream steps")
    parser.add_argument("--warmup-seconds", type=float, default=8.0)
    args = parser.parse_args()

    ctrl = AppController(config=AppConfig())
    print("\n[STEP 2] Start camera + pose detection")
    devices = ctrl.discover_cameras()
    available = [d for d in devices if d.is_available]
    check("camera discovery", len(available) > 0,
          f"{len(available)} available of {len(devices)} probed")
    ok = ctrl.start_current_camera() if available else False
    check("start_current_camera()", ok)
    if not ok:
        err = ctrl.pop_error()
        check("no camera error queued", err is None, str(err))
        ctrl.shutdown()
        return 1

    cam = ctrl.get_current_camera()
    check("camera opened", cam is not None, getattr(cam, "name", "?"))

    time.sleep(args.warmup_seconds)
    frames_with_pose = 0
    samples = 0
    confidence_sum = 0.0
    frame = None
    pose = None
    for _ in range(40):
        frame = ctrl.get_next_frame()
        pose = ctrl.get_pose_result()
        if frame is not None:
            samples += 1
        if pose is not None and pose.pose_detected and pose.confidence > 0.5:
            frames_with_pose += 1
            confidence_sum += pose.confidence
        time.sleep(0.05)
    check("camera produces frames", frame is not None, f"{samples}/40 polled")
    check(
        "pose detection active",
        frames_with_pose > 0,
        f"{(frames_with_pose / 40 * 100):.0f}% frames with pose, "
        f"mean conf {(confidence_sum / max(frames_with_pose, 1)):.2f}",
    )
    fps = ctrl.get_average_fps()
    check("FPS monitor reports rate", fps > 1.0, f"{fps:.1f} FPS")

    print("\n[STEP 3] Record a test clip")
    ctrl.start_recording()
    check("recording started", ctrl.is_recording)
    time.sleep(args.record_seconds)
    n_recorded = ctrl.recorded_frame_count
    check("frames accumulated", n_recorded > 10, f"{n_recorded} frames")
    saved = ctrl.stop_recording()
    check("recording stopped + JSON saved", saved is not None, str(saved))
    if saved is None:
        ctrl.shutdown()
        return 1

    data = json.loads(Path(saved).read_text(encoding="utf-8"))
    meta = data.get("metadata", {})
    frame_count = meta.get("frame_count", 0)
    check("JSON metadata frame_count", frame_count == n_recorded,
          f"{frame_count} == {n_recorded}")
    av_fps = meta.get("average_fps", 0)
    check("JSON average_fps valid", 1.0 < av_fps < 120.0, f"{av_fps:.2f} FPS")
    poses = data.get("pose_results", [])
    stamps = [p.get("timestamp", 0.0) for p in poses]
    check("timestamps monotonic",
          all(b > a for a, b in zip(stamps, stamps[1:])) if len(stamps) > 1 else False,
          f"first={stamps[0]:.3f} last={stamps[-1]:.3f}")
    live_detected = len([p for p in poses if p.get("pose_detected") and p.get("landmarks")])
    check("live landmarks captured", live_detected > 0,
          f"{live_detected}/{len(poses)} frames with landmarks")

    # If the current room has nobody in front of the camera, the live
    # clip contains no landmarks.  Fall back to the project's proven
    # real mocap recording so the downstream pipeline is still verified
    # end-to-end with genuine data.
    fallback = None
    if live_detected == 0 or args.use_legacy:
        import shutil
        source = Path("exports/recordings/recording_1785820551.json")
        check("LEGACY FALLBACK: using proven mocap clip",
              source.exists(), str(source))
        if not source.exists():
            print("  ERROR  no proven mocap clip available; cannot verify "
                  "downstream pipeline")
            ctrl.shutdown()
            return 1
        tmp = Path("exports") / "qa_test" / "fallback_clip.json"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, tmp)
        saved = tmp
        data = json.loads(saved.read_text(encoding="utf-8"))
        poses = data.get("pose_results", [])
        frame_count = len(poses)
        check("fallback clip has landmarks",
              len([p for p in poses if p.get("landmarks")]) > 0,
              f"{len(poses)} frames")

    print("\n[STEP 3b] Playback matches recording")
    ok_load = ctrl.load_recording(str(saved))
    check("load_recording()", ok_load)
    check("playback sequence loaded", ctrl.has_playback_sequence)
    check("total frames match JSON",
          ctrl.playback_total_frames == frame_count,
          f"{ctrl.playback_total_frames} == {frame_count}")

    ctrl.play_playback()
    time.sleep(0.2)
    check("playback entered PLAYING", ctrl.is_playback_playing)
    parsed = ctrl._playback_ctrl.sequence
    match = 0
    total_checked = 0
    stride = max(1, frame_count // 20)
    for idx in range(0, frame_count, stride):
        src = poses[idx].get("landmarks")
        if not src or len(src) != 33:
            continue
        parsed_pose = parsed.pose_results[idx]
        if not parsed_pose.pose_detected or len(parsed_pose.landmarks) != 33:
            continue
        dx = abs(parsed_pose.landmarks[0].x - src[0]["x"])
        dy = abs(parsed_pose.landmarks[0].y - src[0]["y"])
        match += dx < 0.01 and dy < 0.01
        total_checked += 1
    check("playback frames match recording",
          total_checked >= 5 and match == total_checked,
          f"{match}/{total_checked} frames identical")
    ctrl.stop_playback()

    print("\n[STEP 4] Generate animation")
    ok_anim = ctrl.create_animation()
    check("create_animation()", ok_anim)
    clip = ctrl.animation_clip
    check("animation clip created", clip is not None)
    if clip is not None:
        check("keyframes match frame count", len(clip.keyframes) == frame_count,
              f"{len(clip.keyframes)} == {frame_count}")
    ctrl.play_playback()
    time.sleep(0.15)
    preview = ctrl.get_playback_frame()
    check("animation preview frame renders", preview is not None,
          f"shape={None if preview is None else preview.shape}")
    ctrl.stop_playback()

    print("\n[STEP 5] Export BVH / CSV / NPY")
    out_dir = Path("exports") / "qa_test"
    out_dir.mkdir(parents=True, exist_ok=True)
    bvh_path = out_dir / "qa_clip.bvh"
    ok_bvh = ctrl.export_bvh(bvh_path)
    check("export_bvh()", ok_bvh, str(bvh_path))
    if ok_bvh:
        text = bvh_path.read_text(encoding="utf-8")
        check("BVH: HIERARCHY present", "HIERARCHY" in text)
        check("BVH: MOTION present", "MOTION" in text)
        check("BVH: Frames line matches", f"Frames: {frame_count}" in text,
              f"expected {frame_count}")
        check("BVH: Frame Time valid",
              any("Frame Time:" in l for l in text.splitlines()), "")
        check("BVH: ZXY rotation order",
              "Zrotation Xrotation Yrotation" in text)
        check("BVH: root has 6 channels",
              "CHANNELS 6 Xposition Yposition Zposition" in text)
        check("BVH: root OFFSET zero", "OFFSET 0.000000 0.000000 0.000000" in text)

    csv_path = out_dir / "qa_clip.csv"
    npy_path = out_dir / "qa_clip.npy"
    check("export_csv()", ctrl.export_csv(csv_path), str(csv_path))
    check("export_npy()", ctrl.export_npy(npy_path), str(npy_path))

    print("\n[STEP 8] File handles closed (delete-all proof)")
    to_delete = [bvh_path, csv_path, npy_path, Path(saved)]
    for p in to_delete:
        try:
            p.unlink()
            print(f"  PASS  deleted {p.name}")
        except PermissionError as e:
            print(f"  FAIL  still locked: {p.name} — {e}")
            FAIL += 1
    try:
        out_dir.rmdir()
        print("  PASS  export dir removed (no lingering handles)")
    except OSError:
        pass

    ctrl.shutdown()
    print(f"\n===== QA PIPELINE RESULT: {PASS} passed, {FAIL} failed =====")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
