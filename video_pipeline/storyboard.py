from __future__ import annotations

import json
import re
from typing import Any

import httpx

from video_pipeline.models import PipelineConfig, Shot, Storyboard

STORYBOARD_SYSTEM = """你是短视频分镜导演。把主题或口播文案拆成可直接调用视频模型的分镜 JSON。
硬性约束：
- 只输出 JSON，不要 markdown。
- shots 数量 4-12，id 从 1 连续编号。
- 每个镜头 duration_sec 取 4、5、6、8 之一，且必须覆盖 narration 朗读时长（中文约 4.5 字/秒）。
- visual_prompt 用视频模型能吃的画面描述：主体、动作、场景、光线、镜头运动；保持角色/场景一致。
- narration 是口播原文，口语化，一句一镜，不要旁白编号。
- 竖屏默认 9:16，横屏 16:9。
JSON 结构：
{
  "title": "string",
  "theme": "string",
  "aspect_ratio": "9:16",
  "style": "string",
  "character_bible": "角色外观锁定，跨镜复用",
  "shots": [
    {
      "id": 1,
      "duration_sec": 5,
      "narration": "口播",
      "visual_prompt": "画面提示词",
      "camera": "slow push in",
      "negative_prompt": "text, watermark, logo"
    }
  ]
}
"""


def estimate_speech_seconds(text: str) -> float:
    compact = re.sub(r"\s+", "", text)
    return max(2.0, round(len(compact) / 4.5, 2))


def clamp_video_duration(seconds: float) -> float:
    allowed = (4, 5, 6, 8, 10, 12)
    return min(allowed, key=lambda item: abs(item - max(4.0, min(15.0, seconds))))


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?；;])", text)
    sentences = [part.strip() for part in parts if part.strip()]
    if sentences:
        return sentences
    chunk_size = 24
    return [text[i : i + chunk_size].strip() for i in range(0, len(text), chunk_size) if text[i : i + chunk_size].strip()]


def heuristic_storyboard(theme: str, copy: str, cfg: PipelineConfig) -> Storyboard:
    source = copy.strip() or theme.strip()
    paragraphs = [block.strip() for block in re.split(r"\n+", source) if block.strip()] or [source]
    packed: list[str] = []
    for paragraph in paragraphs:
        buf = ""
        for sentence in _split_sentences(paragraph):
            candidate = f"{buf}{sentence}"
            if buf and estimate_speech_seconds(candidate) > 7:
                packed.append(buf)
                buf = sentence
            else:
                buf = candidate
        if buf:
            packed.append(buf)
    packed = packed[: cfg.max_shots]
    if not packed:
        packed = [source]
    shots = []
    for index, narration in enumerate(packed, start=1):
        duration = clamp_video_duration(estimate_speech_seconds(narration) + 0.6)
        shots.append(
            Shot(
                id=index,
                duration_sec=duration,
                narration=narration,
                visual_prompt=(
                    f"{cfg.aspect_ratio} cinematic shot of: {theme}. "
                    f"On-screen action matching: {narration}. "
                    "photoreal, consistent character, no captions, no watermark"
                ),
                camera="slow push in" if index % 2 else "gentle pan",
                negative_prompt="text, watermark, logo, subtitles",
            )
        )
    return Storyboard(
        title=theme[:40] or "未命名短片",
        theme=theme,
        aspect_ratio=cfg.aspect_ratio,
        style="cinematic, consistent lighting, same character design",
        character_bible=f"围绕主题「{theme}」保持同一角色与场景色调",
        shots=shots,
    )


def _extract_json(text: str) -> dict[str, Any]:
    raw = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.S)
    if fenced:
        raw = fenced.group(1)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("LLM did not return JSON")
    return json.loads(raw[start : end + 1])


def llm_storyboard(theme: str, copy: str, cfg: PipelineConfig) -> Storyboard:
    if not cfg.llm_api_key:
        return heuristic_storyboard(theme, copy, cfg)

    user = (
        f"主题：{theme}\n"
        f"画幅：{cfg.aspect_ratio}\n"
        f"最多镜头：{cfg.max_shots}\n"
        f"已有文案（可为空，空则你撰写口播）：\n{copy or '（无，请根据主题撰写口播）'}"
    )
    payload = {
        "model": cfg.llm_model,
        "temperature": 0.4,
        "messages": [
            {"role": "system", "content": STORYBOARD_SYSTEM},
            {"role": "user", "content": user},
        ],
    }
    url = cfg.llm_base_url.rstrip("/") + "/v1/chat/completions"
    headers = {"Authorization": f"Bearer {cfg.llm_api_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=60) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    data = _extract_json(content)
    data.setdefault("theme", theme)
    data.setdefault("aspect_ratio", cfg.aspect_ratio)
    storyboard = Storyboard.model_validate(data)
    for shot in storyboard.shots:
        needed = estimate_speech_seconds(shot.narration) + 0.4
        if shot.duration_sec < needed:
            shot.duration_sec = clamp_video_duration(needed)
    return storyboard
