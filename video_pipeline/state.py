from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobState:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "shots").mkdir(exist_ok=True)
        self.path = self.root / "state.json"
        self.data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {"created_at": utc_now(), "steps": {}, "shots": {}}

    def save(self) -> None:
        self.data["updated_at"] = utc_now()
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def mark(self, step: str, **payload: Any) -> None:
        self.data.setdefault("steps", {})[step] = {"at": utc_now(), **payload}
        self.save()

    def shot_dir(self, shot_id: int) -> Path:
        path = self.root / "shots" / f"{shot_id:02d}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def update_shot(self, shot_id: int, **payload: Any) -> None:
        shots = self.data.setdefault("shots", {})
        current = shots.get(str(shot_id), {})
        current.update(payload)
        current["updated_at"] = utc_now()
        shots[str(shot_id)] = current
        self.save()
