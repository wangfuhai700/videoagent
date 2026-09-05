from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from video_pipeline.assemble import align_shot, concat_and_subtitle, write_ass
from video_pipeline.models import PipelineConfig, Shot, Storyboard
from video_pipeline.providers import get_tts_provider, get_video_provider
from video_pipeline.state import JobState
from video_pipeline.storyboard import llm_storyboard


class Pipeline:
    def __init__(self, cfg: PipelineConfig, job_dir: Path) -> None:
        self.cfg = cfg
        self.state = JobState(job_dir)
        self.video = get_video_provider(cfg)
        self.tts = get_tts_provider(cfg)

    def run(self, theme: str, copy: str = "") -> Path:
        board_path = self.state.root / "storyboard.json"
        if board_path.exists():
            storyboard = Storyboard.model_validate_json(board_path.read_text(encoding="utf-8"))
        else:
            storyboard = llm_storyboard(theme, copy, self.cfg)
            board_path.write_text(storyboard.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")
        self.state.mark("storyboard", shots=len(storyboard.shots), title=storyboard.title)

        self._run_tts(storyboard)
        self._run_video(storyboard)
        aligned = self._align(storyboard)
        audio_paths = [self.state.shot_dir(shot.id) / "narration.wav" for shot in storyboard.shots]
        ass_path = write_ass(storyboard, audio_paths, self.state.root / "subtitles.ass")
        bgm = Path(self.cfg.bgm_path) if self.cfg.bgm_path else None
        final = concat_and_subtitle(aligned, ass_path, self.state.root / "final.mp4", self.cfg, bgm)
        self.state.mark("final", path=str(final))
        return final

    def _run_tts(self, storyboard: Storyboard) -> None:
        def work(shot: Shot) -> None:
            dest = self.state.shot_dir(shot.id) / "narration.wav"
            if dest.exists() and dest.stat().st_size > 0:
                return
            self.tts.synthesize(shot.narration, dest)
            self.state.update_shot(shot.id, tts=str(dest))

        self._bounded(storyboard.shots, work, max(2, min(self.cfg.concurrency, 6)), "tts")

    def _run_video(self, storyboard: Storyboard) -> None:
        def work(shot: Shot) -> None:
            dest = self.state.shot_dir(shot.id) / "raw.mp4"
            if dest.exists() and dest.stat().st_size > 0:
                return
            self.video.generate(storyboard, shot, dest)
            self.state.update_shot(shot.id, video=str(dest))

        self._bounded(storyboard.shots, work, self.cfg.concurrency, "video")

    def _align(self, storyboard: Storyboard) -> list[Path]:
        aligned: list[Path] = []
        for shot in storyboard.shots:
            video = self.state.shot_dir(shot.id) / "raw.mp4"
            audio = self.state.shot_dir(shot.id) / "narration.wav"
            dest = self.state.shot_dir(shot.id) / "aligned.mp4"
            if not dest.exists():
                align_shot(video, audio, dest, self.cfg)
            aligned.append(dest)
            self.state.update_shot(shot.id, aligned=str(dest))
        self.state.mark("align", count=len(aligned))
        return aligned

    def _bounded(self, shots: list[Shot], fn, concurrency: int, label: str) -> None:
        errors: list[str] = []
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {pool.submit(fn, shot): shot.id for shot in shots}
            for future in as_completed(futures):
                shot_id = futures[future]
                try:
                    future.result()
                except Exception as exc:  # noqa: BLE001 - collect all shot failures
                    errors.append(f"shot {shot_id}: {exc}")
        if errors:
            raise RuntimeError(f"{label} failed:\n" + "\n".join(errors))
        self.state.mark(label, ok=True)
