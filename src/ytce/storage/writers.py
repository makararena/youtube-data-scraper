from __future__ import annotations

import io
import json
import os
from typing import Any, Dict, Iterable


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_json(path: str, payload: Any) -> None:
    ensure_dir(os.path.dirname(path) or ".")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def write_jsonl(path: str, items: Iterable[Dict[str, Any]]) -> int:
    ensure_dir(os.path.dirname(path) or ".")
    count = 0
    with io.open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            count += 1
    return count
