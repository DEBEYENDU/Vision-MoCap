# Chapter 8: Performance

## 8.1 Throughput Targets

| Pipeline Stage     | Target | Actual (Full model, GPU) |
|-------------------|--------|-------------------------|
| Frame capture     | <33 ms | ~8 ms                   |
| Pose inference    | <33 ms | ~20 ms                  |
| Landmark rendering | <16 ms | ~2 ms                   |
| End-to-end latency | <50 ms | ~35 ms                  |

## 8.2 GPU Acceleration

MediaPipe's GPU delegate (OpenGL ES compute shaders) provides a
1.5×–2× speedup over CPU inference on compatible hardware.

## 8.3 Memory Optimization

- **Frame subsampling** — Configurable skip factor reduces memory
  usage linearly during long recordings.
- **Lazy loading** — Recordings are loaded on demand during playback,
  not cached permanently.
- **Buffer size** — The frame manager uses a single-frame buffer to
  minimize memory pressure in the capture pipeline.

## 8.4 Profiling Benchmarks

Benchmark tests in `tests/performance/test_profiling.py` measure:

- PoseResult construction throughput
- Playback seek latency (<1 ms target)
- Frame advance throughput (<33 ms/frame)
- Sequence deep-copy throughput (<10 ms for 1000 frames)
