from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def write_jobs_snapshot(path: Path, jobs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": datetime.now().isoformat(),
        "jobCount": len(jobs),
        "jobs": jobs,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
