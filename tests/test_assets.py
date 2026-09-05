from pathlib import Path

from video_pipeline.assets import bind_assets, collect_assets, still_to_clip
from video_pipeline.config import load_config
from video_pipeline.ffmpeg_utils import probe_duration, run_ffmpeg
from video_pipeline.orchestrator import Pipeline
from video_pipeline.storyboard import heuristic_storyboard


def _make_png(path: Path, color: str = "0x1f4e79") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=720x1280:d=0.1",
            "-frames:v",
            "1",
            "-y",
            str(path),
        ]
    )
    return path


def test_collect_and_bind_assets(tmp_path: Path):
    _make_png(tmp_path / "online.png")
    _make_png(tmp_path / "offline.png", "0x2e7d32")
    (tmp_path / "notes.txt").write_text("口播补充：调度要把在线优先级写死。\n", encoding="utf-8")
    assets = collect_assets([tmp_path])
    kinds = {asset.kind for asset in assets}
    assert kinds == {"image", "text"}
    cfg = load_config()
    cfg.max_shots = 6
    board = heuristic_storyboard("混部", "在线要稳。", cfg)
    bound = bind_assets(board, assets, cfg)
    assert bound.shots[0].asset_id
    assert any(shot.asset_id for shot in bound.shots)
    assert len(bound.shots) >= 2


def test_still_to_clip(tmp_path: Path):
    png = _make_png(tmp_path / "card.png")
    cfg = load_config()
    dest = tmp_path / "clip.mp4"
    still_to_clip(png, dest, 2.0, cfg)
    assert dest.exists()
    assert probe_duration(dest) >= 1.5


def test_pipeline_uses_user_image(tmp_path: Path):
    png = _make_png(tmp_path / "materials" / "mix.png")
    cfg = load_config()
    cfg.video_provider = "mock"
    cfg.tts_provider = "mock"
    cfg.max_shots = 2
    assets = collect_assets([png.parent])
    job = tmp_path / "job"
    final = Pipeline(cfg, job, assets).run("TencentOS 混部", "在线任务要稳，延迟必须可控。")
    assert final.exists()
    assert probe_duration(final) > 2
    board_text = (job / "storyboard.json").read_text(encoding="utf-8")
    assert "a1" in board_text
    assert (job / "assets.json").exists()
