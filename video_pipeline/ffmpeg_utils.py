from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import httpx


def require_ffmpeg() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg/ffprobe 未安装")


def run_ffmpeg(args: list[str]) -> None:
    require_ffmpeg()
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", *args]
    subprocess.run(cmd, check=True)


def probe_duration(path: Path) -> float:
    require_ffmpeg()
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout or "{}")
    return float((data.get("format") or {}).get("duration") or 0)


def download_file(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with dest.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
    return dest


def find_cjk_font() -> tuple[str, Path | None]:
    candidates = [
        ("WenQuanYi Micro Hei", Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc")),
        ("Noto Sans CJK SC", Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")),
        ("PingFang SC", Path("/System/Library/Fonts/PingFang.ttc")),
        ("Microsoft YaHei", Path("C:/Windows/Fonts/msyh.ttc")),
    ]
    for name, path in candidates:
        if path.exists():
            return name, path.parent
    return "Sans", None


def escape_filter_path(path: Path) -> str:
    return path.resolve().as_posix().replace("\\", "\\\\").replace(":", "\\:").replace("'", r"\'")
