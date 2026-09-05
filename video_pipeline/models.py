from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

AspectRatio = Literal["16:9", "9:16", "1:1"]
VideoProvider = Literal["mock", "seedance", "wan"]
TtsProvider = Literal["mock", "edge"]


class Shot(BaseModel):
    id: int = Field(ge=1)
    duration_sec: float = Field(ge=2, le=15)
    narration: str
    visual_prompt: str
    camera: str = "medium shot"
    negative_prompt: str = ""

    @field_validator("narration", "visual_prompt")
    @classmethod
    def not_blank(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("field must not be blank")
        return text


class Storyboard(BaseModel):
    title: str
    theme: str
    aspect_ratio: AspectRatio = "9:16"
    style: str = "cinematic, consistent lighting, same character design"
    character_bible: str = ""
    shots: list[Shot]

    @field_validator("shots")
    @classmethod
    def ordered_ids(cls, shots: list[Shot]) -> list[Shot]:
        if not shots:
            raise ValueError("storyboard needs at least one shot")
        ids = [shot.id for shot in shots]
        if ids != list(range(1, len(shots) + 1)):
            raise ValueError("shot ids must be consecutive starting at 1")
        return shots


class PipelineConfig(BaseModel):
    aspect_ratio: AspectRatio = "9:16"
    resolution: Literal["480p", "720p", "1080p"] = "720p"
    fps: int = 24
    concurrency: int = Field(default=3, ge=1, le=8)
    max_shots: int = Field(default=12, ge=1, le=30)
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_api_key: str = ""
    video_provider: VideoProvider = "mock"
    video_model: str = "doubao-seedance-1-5-pro-251215"
    video_api_key: str = ""
    video_base_url: str = ""
    tts_provider: TtsProvider = "mock"
    tts_voice: str = "zh-CN-XiaoxiaoNeural"
    bgm_path: str = ""
    bgm_volume: float = 0.18
    output_width: int = 1080
    output_height: int = 1920
    poll_interval_sec: float = 8.0
    poll_timeout_sec: float = 600.0
