"""VisionMoCap AI - Markerless Motion Capture Application."""

import sys
from pathlib import Path

import cv2

from src.camera.manager import CameraManager
from src.config.manager import ConfigManager
from src.motion.frame_manager import FrameManager
from src.motion.motion_recorder import MotionRecorder
from src.pose.pose_detector import PoseDetector
from src.pose.skeleton_renderer import SkeletonRenderer
from src.utils.logger import LoggerSetup


def main() -> None:
    """Initialize and run the VisionMoCap application.

    Pipeline:
        Config -> Logging -> CameraManager -> FrameManager
        -> PoseDetector -> SkeletonRenderer -> MotionRecorder -> Display
    """
    config_manager = ConfigManager()
    config = config_manager.load()

    logger_setup = LoggerSetup(
        name="VisionMoCap",
        level=config.logging.level,
        log_dir=Path(config.logging.directory),
        max_file_size_mb=config.logging.max_file_size_mb,
        backup_count=config.logging.backup_count,
    )
    logger = logger_setup.get_logger()
    logger.info("VisionMoCap AI initialized successfully.")

    camera_mgr = CameraManager(config.camera)
    devices = camera_mgr.discover_cameras()

    if not devices:
        logger.error("No cameras found. Exiting.")
        sys.exit(1)

    camera_mgr.open_camera(devices[0].index)
    logger.info(
        "Using camera [%d] %s.",
        devices[0].index,
        devices[0].name,
    )

    frame_mgr = FrameManager(
        resize=None,
        color_conversion=None,
        buffer_size=1,
    )

    pose_detector = PoseDetector(config.pose)
    pose_detector.initialize()

    renderer = SkeletonRenderer(
        draw_landmarks=True,
        draw_connections=True,
        draw_joint_ids=True,
        draw_confidence=False,
    )

    recorder = MotionRecorder()

    window_name = "VisionMoCap AI"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    logger.info("Main loop started. Press 'Q' to quit, 'R' to record.")

    try:
        while True:
            raw_frame = camera_mgr.get_frame()
            if raw_frame is None:
                continue

            processed = frame_mgr.process(raw_frame)

            pose_result = pose_detector.detect(processed)

            if pose_result.pose_detected:
                processed = renderer.render(processed, pose_result)

            recorder.record(pose_result)

            current_fps = camera_mgr.get_current_fps()
            avg_fps = camera_mgr.get_average_fps()

            overlay_lines = [
                f"FPS: {current_fps:.1f} (avg: {avg_fps:.1f})",
                f"Frame: {frame_mgr.frame_number}",
                f"Pose: {'YES' if pose_result.pose_detected else 'NO'}",
            ]

            if recorder.is_recording:
                overlay_lines.append(
                    f"REC {recorder.recorded_frame_count} frames"
                )

            y_offset = 30
            for line in overlay_lines:
                cv2.putText(
                    processed,
                    line,
                    (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )
                y_offset += 24

            cv2.putText(
                processed,
                "Q:Quit  R:Record",
                (10, processed.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (150, 150, 150),
                1,
                cv2.LINE_AA,
            )

            cv2.imshow(window_name, processed)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                logger.info("Exit key pressed.")
                break
            elif key == ord("r"):
                if recorder.is_recording:
                    sequence = recorder.stop()
                    if sequence is not None:
                        exports_dir = Path("exports")
                        exports_dir.mkdir(parents=True, exist_ok=True)
                        timestamp_str = (
                            f"{sequence.start_time:.0f}"
                        )
                        path = exports_dir / f"recording_{timestamp_str}.json"
                        sequence.save_json(path)
                        logger.info(
                            "Recording saved to %s (%d frames, %.1f FPS).",
                            path,
                            sequence.total_frames,
                            sequence.average_fps,
                        )
                else:
                    recorder.start()

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    finally:
        if recorder.is_recording:
            recorder.cancel()
        pose_detector.shutdown()
        camera_mgr.close_camera()
        cv2.destroyAllWindows()
        logger.info("VisionMoCap AI shut down gracefully.")

    sys.exit(0)


if __name__ == "__main__":
    main()
