from __future__ import annotations

import re
from typing import Optional


def parse_view_count(view_count_raw: str) -> Optional[int]:
    """
    Convert localized view strings into an integer when possible.
    Examples:
      "123,874 views" -> 123874
      "1.2M views" -> 1200000
      "500K views" -> 500000
    """
    if not view_count_raw:
        return None
    s = view_count_raw.replace(" ", "").replace(",", "").replace("\u202f", "").replace("\xa0", "")
    match = re.search(r"([\d.]+)\s*([KMB]?)", s, re.IGNORECASE)
    if not match:
        return None
    number = float(match.group(1))
    mult = (match.group(2) or "").upper()
    if mult == "K":
        return int(number * 1_000)
    if mult == "M":
        return int(number * 1_000_000)
    if mult == "B":
        return int(number * 1_000_000_000)
    return int(number)
