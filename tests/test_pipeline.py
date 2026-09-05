from pathlib import Path

from video_pipeline.config import load_config
from video_pipeline.ffmpeg_utils import probe_duration
from video_pipeline.orchestrator import Pipeline
from video_pipeline.storyboard import heuristic_storyboard


def test_mock_pipeline_produces_mp4(tmp_path: Path):
    cfg = load_config()
    cfg.video_provider = "mock"
    cfg.tts_provider = "mock"
    cfg.max_shots = 2
    board = heuristic_storyboard(
        "测试成片",
        "第一镜把主题说清楚，在线任务必须稳定。\n第二镜给出结论，离线任务只能吃剩余算力。",
        cfg,
    )
    job = tmp_path / "job"
    pipeline = Pipeline(cfg, job)
    # Bypass LLM and use the tiny board by writing then running internals.
    (job / "storyboard.json").write_text(board.model_dump_json(indent=2), encoding="utf-8")
    pipeline._run_tts(board)
    pipeline._run_video(board)
    aligned = pipeline._align(board)
    assert len(aligned) == 2
    for clip in aligned:
        assert clip.exists()
        assert probe_duration(clip) > 1

    from video_pipeline.assemble import concat_and_subtitle, write_ass

    audios = [job / "shots" / f"{shot.id:02d}" / "narration.wav" for shot in board.shots]
    ass = write_ass(board, audios, job / "subtitles.ass")
    final = concat_and_subtitle(aligned, ass, job / "final.mp4", cfg)
    assert final.exists()
    assert probe_duration(final) > 3
    assert (job / "state.json").exists()
