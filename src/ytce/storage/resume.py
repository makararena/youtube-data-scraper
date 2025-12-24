from __future__ import annotations

import os


def should_skip_existing(path: str, *, resume: bool) -> bool:
    return resume and os.path.exists(path) and os.path.getsize(path) > 0
