from pathlib import Path

from video_pipeline.assemble import wrap_cjk, write_ass
from video_pipeline.models import Shot, Storyboard
from video_pipeline.storyboard import clamp_video_duration, estimate_speech_seconds, heuristic_storyboard
from video_pipeline.config import load_config


def test_speech_estimate_and_duration_clamp():
    assert estimate_speech_seconds("一二三四五六七八九") > 1
    assert clamp_video_duration(3.2) == 4
    assert clamp_video_duration(7.6) in {8, 6}


def test_heuristic_storyboard_ids():
    cfg = load_config()
    board = heuristic_storyboard(
        "离在线混部",
        "在线任务要稳。离线任务吃剩余算力。CPU、IO、缓存、网络都要隔离。最后统一调度。",
        cfg,
    )
    assert board.shots
    assert [shot.id for shot in board.shots] == list(range(1, len(board.shots) + 1))
    for shot in board.shots:
        assert shot.duration_sec >= 4


def test_ass_timeline(tmp_path: Path):
    board = Storyboard(
        title="demo",
        theme="demo",
        shots=[
            Shot(id=1, duration_sec=4, narration="第一句口播内容", visual_prompt="scene one"),
            Shot(id=2, duration_sec=5, narration="第二句更长一点的口播", visual_prompt="scene two"),
        ],
    )
    missing = [tmp_path / "missing.wav", tmp_path / "missing2.wav"]
    dest = write_ass(board, missing, tmp_path / "sub.ass")
    text = dest.read_text(encoding="utf-8")
    assert "Dialogue:" in text
    assert wrap_cjk("一二三四五六七八九十一二三四五六七八", 8).count(r"\N") >= 1
