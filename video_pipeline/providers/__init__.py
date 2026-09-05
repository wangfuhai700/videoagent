from video_pipeline.providers.base import TtsProvider, VideoProvider
from video_pipeline.providers.mock import MockTtsProvider, MockVideoProvider
from video_pipeline.providers.seedance import SeedanceProvider
from video_pipeline.providers.wan import WanProvider
from video_pipeline.providers.tts_edge import EdgeTtsProvider
from video_pipeline.models import PipelineConfig


def get_video_provider(cfg: PipelineConfig) -> VideoProvider:
    mapping = {
        "mock": MockVideoProvider,
        "seedance": SeedanceProvider,
        "wan": WanProvider,
    }
    try:
        return mapping[cfg.video_provider](cfg)
    except KeyError as exc:
        raise ValueError(f"unknown video provider: {cfg.video_provider}") from exc


def get_tts_provider(cfg: PipelineConfig) -> TtsProvider:
    mapping = {
        "mock": MockTtsProvider,
        "edge": EdgeTtsProvider,
    }
    try:
        return mapping[cfg.tts_provider](cfg)
    except KeyError as exc:
        raise ValueError(f"unknown tts provider: {cfg.tts_provider}") from exc
