from __future__ import annotations

import time
from pathlib import Path

import httpx

from video_pipeline.ffmpeg_utils import download_file
from video_pipeline.models import Shot, Storyboard
from video_pipeline.providers.base import VideoProvider


class SeedanceProvider(VideoProvider):
    """Volcengine Ark Seedance async video API.

    POST /api/v3/contents/generations/tasks
    GET  /api/v3/contents/generations/tasks/{id}
    """

    name = "seedance"

    def __init__(self, cfg) -> None:
        super().__init__(cfg)
        self.base = (cfg.video_base_url or "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
        if not cfg.video_api_key:
            raise RuntimeError("seedance 需要 ARK_API_KEY / VIDEO_API_KEY")

    def generate(self, storyboard: Storyboard, shot: Shot, dest: Path) -> Path:
        prompt = self._prompt(storyboard, shot)
        task_id = self._create(prompt, shot)
        video_url = self._poll(task_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
        download_file(video_url, dest)
        return dest

    def _prompt(self, storyboard: Storyboard, shot: Shot) -> str:
        parts = [
            storyboard.style,
            storyboard.character_bible,
            f"camera: {shot.camera}",
            shot.visual_prompt,
            "no on-screen text, no watermark, no logo, no subtitles",
        ]
        return "，".join(part for part in parts if part)

    def _create(self, prompt: str, shot: Shot) -> str:
        payload = {
            "model": self.cfg.video_model,
            "content": [{"type": "text", "text": prompt}],
            "duration": int(round(shot.duration_sec)),
            "ratio": self.cfg.aspect_ratio,
            "resolution": self.cfg.resolution,
            "watermark": False,
        }
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{self.base}/contents/generations/tasks",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        task_id = data.get("id") or data.get("task_id")
        if not task_id:
            raise RuntimeError(f"seedance create missing task id: {data}")
        return task_id

    def _poll(self, task_id: str) -> str:
        deadline = time.time() + self.cfg.poll_timeout_sec
        url = f"{self.base}/contents/generations/tasks/{task_id}"
        with httpx.Client(timeout=30) as client:
            while time.time() < deadline:
                response = client.get(url, headers=self._headers())
                response.raise_for_status()
                data = response.json()
                status = (data.get("status") or "").lower()
                if status in {"succeeded", "success"}:
                    video_url = (data.get("content") or {}).get("video_url") or data.get("video_url")
                    if not video_url:
                        raise RuntimeError(f"seedance succeeded without url: {data}")
                    return video_url
                if status in {"failed", "cancelled", "expired", "error"}:
                    raise RuntimeError(f"seedance task {task_id} {status}: {data}")
                time.sleep(self.cfg.poll_interval_sec)
        raise TimeoutError(f"seedance task {task_id} timed out")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.cfg.video_api_key}",
            "Content-Type": "application/json",
        }
