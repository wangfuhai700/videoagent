from __future__ import annotations

import time
from pathlib import Path

import httpx

from video_pipeline.ffmpeg_utils import download_file
from video_pipeline.models import Shot, Storyboard
from video_pipeline.providers.base import VideoProvider

RATIO_SIZE = {
    "16:9": "1280*720",
    "9:16": "720*1280",
    "1:1": "960*960",
}


class WanProvider(VideoProvider):
    """Aliyun DashScope Wan text-to-video (async)."""

    name = "wan"

    def __init__(self, cfg) -> None:
        super().__init__(cfg)
        self.base = (cfg.video_base_url or "https://dashscope.aliyuncs.com/api/v1").rstrip("/")
        if not cfg.video_api_key:
            raise RuntimeError("wan 需要 DASHSCOPE_API_KEY / VIDEO_API_KEY")
        if not cfg.video_model:
            self.cfg.video_model = "wanx2.1-t2v-turbo"

    def generate(self, storyboard: Storyboard, shot: Shot, dest: Path) -> Path:
        prompt = "，".join(
            part
            for part in (
                storyboard.style,
                storyboard.character_bible,
                shot.camera,
                shot.visual_prompt,
            )
            if part
        )
        task_id = self._create(prompt, shot)
        video_url = self._poll(task_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
        download_file(video_url, dest)
        return dest

    def _create(self, prompt: str, shot: Shot) -> str:
        payload = {
            "model": self.cfg.video_model,
            "input": {"prompt": prompt, "negative_prompt": shot.negative_prompt},
            "parameters": {
                "size": RATIO_SIZE.get(self.cfg.aspect_ratio, "720*1280"),
                "duration": int(round(shot.duration_sec)),
            },
        }
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{self.base}/services/aigc/video-generation/video-synthesis",
                headers={
                    "Authorization": f"Bearer {self.cfg.video_api_key}",
                    "Content-Type": "application/json",
                    "X-DashScope-Async": "enable",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        task_id = (data.get("output") or {}).get("task_id") or data.get("task_id")
        if not task_id:
            raise RuntimeError(f"wan create missing task id: {data}")
        return task_id

    def _poll(self, task_id: str) -> str:
        deadline = time.time() + self.cfg.poll_timeout_sec
        url = f"{self.base}/tasks/{task_id}"
        with httpx.Client(timeout=30) as client:
            while time.time() < deadline:
                response = client.get(
                    url,
                    headers={"Authorization": f"Bearer {self.cfg.video_api_key}"},
                )
                response.raise_for_status()
                data = response.json()
                output = data.get("output") or {}
                status = (output.get("task_status") or data.get("status") or "").upper()
                if status in {"SUCCEEDED", "SUCCESS"}:
                    video_url = (
                        output.get("video_url")
                        or (output.get("results") or [{}])[0].get("url")
                        or data.get("video_url")
                    )
                    if not video_url:
                        raise RuntimeError(f"wan succeeded without url: {data}")
                    return video_url
                if status in {"FAILED", "CANCELED", "UNKNOWN"}:
                    raise RuntimeError(f"wan task {task_id} {status}: {data}")
                time.sleep(self.cfg.poll_interval_sec)
        raise TimeoutError(f"wan task {task_id} timed out")
