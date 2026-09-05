from __future__ import annotations

import subprocess
from pathlib import Path

from pydantic import BaseModel

from video_pipeline.ffmpeg_utils import run_ffmpeg
from video_pipeline.models import PipelineConfig, Shot, Storyboard

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
TEXT_EXT = {".txt", ".md"}


class Asset(BaseModel):
    id: str
    path: str
    kind: str
    name: str

    @property
    def file(self) -> Path:
        return Path(self.path)


def classify(path: Path) -> str | None:
    ext = path.suffix.lower()
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    if ext in AUDIO_EXT:
        return "audio"
    if ext in TEXT_EXT:
        return "text"
    return None


def collect_assets(paths: list[Path]) -> list[Asset]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(item for item in path.rglob("*") if item.is_file()))
        elif path.is_file():
            files.append(path)
    assets: list[Asset] = []
    index = 1
    for file in files:
        kind = classify(file)
        if not kind:
            continue
        assets.append(
            Asset(
                id=f"a{index}",
                path=str(file.resolve()),
                kind=kind,
                name=file.name,
            )
        )
        index += 1
    return assets


def visual_assets(assets: list[Asset]) -> list[Asset]:
    return [asset for asset in assets if asset.kind in {"image", "video"}]


def text_from_assets(assets: list[Asset]) -> str:
    chunks: list[str] = []
    for asset in assets:
        if asset.kind != "text":
            continue
        chunks.append(asset.file.read_text(encoding="utf-8").strip())
    return "\n".join(chunk for chunk in chunks if chunk)


def first_audio(assets: list[Asset]) -> Path | None:
    for asset in assets:
        if asset.kind == "audio":
            return asset.file
    return None


def assets_prompt(assets: list[Asset]) -> str:
    visuals = visual_assets(assets)
    if not visuals:
        return ""
    lines = "\n".join(f"- {asset.id} [{asset.kind}] {asset.name}" for asset in visuals)
    return (
        "用户提供的素材。有对应画面时在镜头里填写 asset_id；没有合适素材则 asset_id 留空。\n"
        f"{lines}"
    )


def bind_assets(storyboard: Storyboard, assets: list[Asset], cfg: PipelineConfig) -> Storyboard:
    visuals = visual_assets(assets)
    if not visuals:
        return storyboard

    shots = [shot.model_copy() for shot in storyboard.shots]
    used = {shot.asset_id for shot in shots if shot.asset_id}
    unused = [asset for asset in visuals if asset.id not in used]
    by_id = {asset.id: asset for asset in visuals}

    for shot, asset in zip((item for item in shots if not item.asset_id), unused):
        shot.asset_id = asset.id
    unused = [asset for asset in visuals if asset.id not in {shot.asset_id for shot in shots if shot.asset_id}]

    next_id = len(shots) + 1
    for asset in unused:
        if next_id > cfg.max_shots:
            break
        shots.append(
            Shot(
                id=next_id,
                duration_sec=5,
                narration=storyboard.theme,
                visual_prompt=f"Present user-provided {asset.kind} named {asset.name}. {storyboard.theme}",
                camera="slow push in",
                negative_prompt="text, watermark, logo, subtitles",
                asset_id=asset.id,
            )
        )
        next_id += 1

    for shot in shots:
        asset = by_id.get(shot.asset_id)
        if asset:
            shot.visual_prompt = (
                f"{shot.visual_prompt.rstrip('. ')}. "
                f"Use provided {asset.kind} `{asset.name}` as the on-screen subject."
            )

    return storyboard.model_copy(update={"shots": shots})


def still_to_clip(image: Path, dest: Path, duration: float, cfg: PipelineConfig) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    width, height = cfg.output_width, cfg.output_height
    frames = max(int(round(duration * cfg.fps)), cfg.fps * 2)
    motion = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"zoompan=z='min(zoom+0.0015,1.12)':d={frames}:s={width}x{height}:fps={cfg.fps},"
        "format=yuv420p"
    )
    static = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={cfg.fps},format=yuv420p"
    )
    def encode(vf: str) -> None:
        run_ffmpeg(
            [
                "-loop",
                "1",
                "-i",
                str(image),
                "-vf",
                vf,
                "-t",
                f"{duration:.3f}",
                "-an",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-y",
                str(dest),
            ]
        )

    try:
        encode(motion)
    except subprocess.CalledProcessError:
        encode(static)
    return dest


def clip_to_shot(video: Path, dest: Path, duration: float, cfg: PipelineConfig) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    vf = (
        f"scale={cfg.output_width}:{cfg.output_height}:force_original_aspect_ratio=decrease,"
        f"pad={cfg.output_width}:{cfg.output_height}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={cfg.fps},setsar=1,format=yuv420p"
    )
    run_ffmpeg(
        [
            "-i",
            str(video),
            "-t",
            f"{duration:.3f}",
            "-vf",
            vf,
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(dest),
        ]
    )
    return dest


def render_asset_shot(asset: Asset, dest: Path, duration: float, cfg: PipelineConfig) -> Path:
    if asset.kind == "image":
        return still_to_clip(asset.file, dest, duration, cfg)
    if asset.kind == "video":
        return clip_to_shot(asset.file, dest, duration, cfg)
    raise ValueError(f"asset {asset.id} is {asset.kind}, not visual")
