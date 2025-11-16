# app/logger.py

from pathlib import Path

from datetime import datetime

import json, os, time

from typing import Any, Dict



LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))

LOG_DIR.mkdir(parents=True, exist_ok=True)



def _log_path() -> Path:

    # daily rotation: logs/chat-YYYYMMDD.jsonl

    day = datetime.utcnow().strftime("%Y%m%d")

    return LOG_DIR / f"chat-{day}.jsonl"



def log_event(kind: str, payload: Dict[str, Any]) -> None:

    record = {

        "ts": time.time(),

        "event": kind,

        **payload,

    }

    with _log_path().open("a", encoding="utf-8") as f:

        f.write(json.dumps(record, ensure_ascii=False) + "\n")

