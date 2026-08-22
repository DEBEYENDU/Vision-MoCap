"""NumPy binary exporter for the VisionMoCap application.

Converts a :class:`MotionSequence` to a ``.npy`` file containing a single
structured array with columns ``[frame, timestamp, lm_0_x, lm_0_y, lm_0_z,
lm_0_visibility, ..., lm_32_visibility]``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from src.core.exceptions import AnimationExportError
from src.motion.motion_sequence import MotionSequence


class NpyExporter:
    """Export a MotionSequence to a NumPy ``.npy`` binary file.

    The output is a 2-D structured NumPy array with one row per frame and
    the same columns as the CSV exporter (frame number, timestamp, then
    4 columns per landmark).
    """

    def export(self, sequence: MotionSequence, output_path: Path) -> None:
        """Write *sequence* to *output_path* as a ``.npy`` file.

        Args:
            sequence: The recorded motion data to export.
            output_path: Destination path for the ``.npy`` file.

        Raises:
            ValueError: If the sequence has no frames.
        """
        if not sequence.pose_results:
            raise ValueError("Cannot export empty sequence to NPY.")

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            data = self._build_array(sequence)
            np.save(str(output_path), data)
        except (OSError, ValueError) as e:
            raise AnimationExportError(
                f"Failed to write NPY file {output_path}: {e}",
                cause=e,
            )

    @staticmethod
    def _build_array(sequence: MotionSequence) -> NDArray[np.float64]:
        """Build a 2-D structured array from the sequence.

        Frames without landmarks (pose lost during recording) are
        padded with NaN so the array always has the documented shape
        ``(frames, 2 + 33 * 4)``.
        """
        num_frames = len(sequence.pose_results)
        cols = 2 + 33 * 4  # frame, timestamp, 33 landmarks × 4 fields
        arr = np.empty((num_frames, cols), dtype=np.float64)
        arr[:] = np.nan

        for i, pr in enumerate(sequence.pose_results):
            row = [float(i), pr.timestamp]
            for lm in pr.landmarks[:33]:
                row.extend([lm.x, lm.y, lm.z, lm.visibility])
            arr[i, :len(row)] = row

        return arr
