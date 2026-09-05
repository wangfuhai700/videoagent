from __future__ import annotations

import asyncio
from pathlib import Path

from video_pipeline.providers.base import TtsProvider


class EdgeTtsProvider(TtsProvider):
    name = "edge"

    def synthesize(self, text: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        asyncio.run(self._speak(text, dest))
        return dest

    async def _speak(self, text: str, dest: Path) -> None:
        import edge_tts

        communicate = edge_tts.Communicate(text, self.cfg.tts_voice)
        await communicate.save(str(dest))
