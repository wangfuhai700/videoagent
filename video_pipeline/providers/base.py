from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from video_pipeline.models import PipelineConfig, Shot, Storyboard


class VideoProvider(ABC):
    name: str

    def __init__(self, cfg: PipelineConfig) -> None:
        self.cfg = cfg

    @abstractmethod
    def generate(self, storyboard: Storyboard, shot: Shot, dest: Path) -> Path:
        """Generate one shot clip to dest (mp4)."""


class TtsProvider(ABC):
    name: str

    def __init__(self, cfg: PipelineConfig) -> None:
        self.cfg = cfg

    @abstractmethod
    def synthesize(self, text: str, dest: Path) -> Path:
        """Generate narration audio to dest (wav/mp3)."""
