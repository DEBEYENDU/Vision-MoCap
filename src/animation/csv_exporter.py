"""CSV exporter for the VisionMoCap application.

Converts a :class:`MotionSequence` to a wide-format CSV file where each row
represents one frame and columns contain landmark coordinates and visibility.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from src.core.exceptions import AnimationExportError
from src.motion.motion_sequence import MotionSequence


class CsvExporter:
    """Export a MotionSequence to CSV format.

    The output has one header row and one data row per frame.
    Columns are::

        frame, timestamp, lm_0_x, lm_0_y, lm_0_z, lm_0_visibility,
        lm_1_x, ..., lm_32_visibility
    """

    def export(self, sequence: MotionSequence, output_path: Path) -> None:
        """Write *sequence* to *output_path* as a CSV file.

        Args:
            sequence: The recorded motion data to export.
            output_path: Destination path for the ``.csv`` file.

        Raises:
            ValueError: If the sequence has no frames.
        """
        if not sequence.pose_results:
            raise ValueError("Cannot export empty sequence to CSV.")

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_csv(sequence, output_path)
        except OSError as e:
            raise AnimationExportError(
                f"Failed to write CSV file {output_path}: {e}",
                cause=e,
            )

    @staticmethod
    def _header() -> List[str]:
        cols: List[str] = ["frame", "timestamp"]
        for i in range(33):
            cols.extend([f"lm_{i}_x", f"lm_{i}_y", f"lm_{i}_z", f"lm_{i}_visibility"])
        return cols

    def _write_csv(self, sequence: MotionSequence, output_path: Path) -> None:
        header = self._header()
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for frame_idx, pr in enumerate(sequence.pose_results):
                row: List[float] = [frame_idx, pr.timestamp]
                for lm in pr.landmarks[:33]:
                    row.extend([lm.x, lm.y, lm.z, lm.visibility])
                # Frames without landmarks (pose lost during recording)
                # are padded with NaN so every row matches the header.
                if len(row) < len(header):
                    row.extend([float("nan")] * (len(header) - len(row)))
                writer.writerow(row)
