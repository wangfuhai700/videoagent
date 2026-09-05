from __future__ import annotations

import os
from pathlib import Path

import yaml

from video_pipeline.models import PipelineConfig

RATIO_SIZE = {
    "16:9": (1280, 720),
    "9:16": (720, 1280),
    "1:1": (720, 720),
}


def load_config(path: str | Path | None = None) -> PipelineConfig:
    data: dict = {}
    if path:
        loaded = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError("config file must be a YAML mapping")
        data = loaded

    env_overrides = {
        "llm_base_url": os.getenv("LLM_BASE_URL"),
        "llm_model": os.getenv("LLM_MODEL"),
        "llm_api_key": os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"),
        "video_provider": os.getenv("VIDEO_PROVIDER"),
        "video_model": os.getenv("ARK_VIDEO_MODEL") or os.getenv("VIDEO_MODEL"),
        "video_api_key": os.getenv("ARK_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or os.getenv("VIDEO_API_KEY"),
        "video_base_url": os.getenv("VIDEO_BASE_URL"),
        "tts_provider": os.getenv("TTS_PROVIDER"),
        "tts_voice": os.getenv("TTS_VOICE"),
        "concurrency": os.getenv("VIDEO_CONCURRENCY"),
    }
    for key, value in env_overrides.items():
        if value not in (None, ""):
            data[key] = int(value) if key == "concurrency" else value

    cfg = PipelineConfig.model_validate(data)
    if cfg.aspect_ratio == "16:9":
        cfg.output_width, cfg.output_height = 1280, 720
    elif cfg.aspect_ratio == "1:1":
        cfg.output_width, cfg.output_height = 720, 720
    else:
        cfg.output_width, cfg.output_height = 720, 1280
    if cfg.resolution == "1080p":
        cfg.output_width = int(cfg.output_width * 1.5)
        cfg.output_height = int(cfg.output_height * 1.5)
    elif cfg.resolution == "480p":
        cfg.output_width = int(cfg.output_width * 0.67)
        cfg.output_height = int(cfg.output_height * 0.67)
    return cfg
