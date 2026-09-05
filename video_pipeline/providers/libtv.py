"""LibTV Agent-IM is a sequential 'messenger' API, not a per-shot concurrent video API.

Official libtv-skills tells the client agent NOT to split storyboards or fire
one request per shot. Use this helper only for Path B: one natural-language
job handed to LibTV, then download whatever clips it returns.

Per-shot concurrent generation should use Seedance / Wan providers instead.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any


IM_BASE = os.getenv("OPENAPI_IM_BASE") or os.getenv("IM_BASE_URL") or "https://im.liblib.tv"


def _headers() -> dict[str, str]:
    key = os.getenv("LIBTV_ACCESS_KEY")
    if not key:
        raise RuntimeError("LIBTV_ACCESS_KEY is required for Path B")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def create_session(message: str) -> dict[str, Any]:
    req = urllib.request.Request(
        f"{IM_BASE}/openapi/session",
        data=json.dumps({"message": message}).encode("utf-8"),
        headers=_headers(),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def query_session(session_id: str, after_seq: int = 0) -> dict[str, Any]:
    url = f"{IM_BASE}/openapi/session/{session_id}?afterSeq={after_seq}"
    req = urllib.request.Request(url, headers=_headers(), method="GET")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_for_urls(session_id: str, timeout_sec: float = 600, interval_sec: float = 8) -> list[str]:
    deadline = time.time() + timeout_sec
    after_seq = 0
    urls: list[str] = []
    while time.time() < deadline:
        payload = query_session(session_id, after_seq)
        messages = payload.get("messages") or []
        for msg in messages:
            after_seq = max(after_seq, int(msg.get("seq") or 0))
            content = str(msg.get("content") or "")
            if msg.get("role") == "assistant":
                urls.extend(_extract_media_urls(content))
        if urls:
            return list(dict.fromkeys(urls))
        time.sleep(interval_sec)
    raise TimeoutError(f"LibTV session {session_id} timed out")


def _extract_media_urls(text: str) -> list[str]:
    import re

    return re.findall(r"https?://[^\s\"']+\.(?:mp4|webm|mov|png|jpe?g|webp)", text, flags=re.I)
