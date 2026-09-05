from __future__ import annotations

from pathlib import Path

from video_pipeline.ffmpeg_utils import probe_duration, run_ffmpeg
from video_pipeline.models import Shot, Storyboard
from video_pipeline.providers.base import TtsProvider, VideoProvider
from video_pipeline.storyboard import estimate_speech_seconds


class MockVideoProvider(VideoProvider):
    name = "mock"

    def generate(self, storyboard: Storyboard, shot: Shot, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        color = ["#1f4e79", "#2e7d32", "#6a1b9a", "#b71c1c", "#00695c"][(shot.id - 1) % 5]
        filter_complex = (
            f"color=c={color}:s={self.cfg.output_width}x{self.cfg.output_height}:d={shot.duration_sec},"
            f"drawtext=text='SHOT {shot.id}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2"
        )
        run_ffmpeg(
            [
                "-f",
                "lavfi",
                "-i",
                filter_complex,
                "-f",
                "lavfi",
                "-i",
                f"anullsrc=r=44100:cl=stereo",
                "-shortest",
                "-t",
                f"{shot.duration_sec}",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-y",
                str(dest),
            ]
        )
        if probe_duration(dest) <= 0:
            raise RuntimeError(f"mock video empty: {dest}")
        return dest


class MockTtsProvider(TtsProvider):
    name = "mock"

    def synthesize(self, text: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        seconds = max(2.0, estimate_speech_seconds(text))
        # A quiet tone so ffmpeg has a real audio stream without needing network TTS.
        run_ffmpeg(
            [
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=220:duration={seconds}:sample_rate=44100",
                "-af",
                "volume=0.08",
                "-y",
                str(dest),
            ]
        )
        return dest
