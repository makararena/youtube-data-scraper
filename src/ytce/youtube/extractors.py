from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

YT_CFG_RE = r"ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;"
YT_INITIAL_DATA_RE = (
    r"(?:window\s*\[\s*[\"']ytInitialData[\"']\s*\]|ytInitialData)\s*=\s*({.+?})\s*;"
    r"\s*(?:var\s+meta|</script|\n)"
)


def _regex_search(text: str, pattern: str, group: int = 1, default: Optional[str] = None) -> Optional[str]:
    match = re.search(pattern, text, re.DOTALL)
    return match.group(group) if match else default


def _extract_json_object(text: str, start_pattern: str) -> Optional[str]:
    """
    Extract a JSON object from text starting at a pattern match.
    Handles nested braces properly.
    """
    match = re.search(start_pattern, text)
    if not match:
        return None

    start_pos = match.end() - 1  # position of opening '{'
    brace_count = 0
    in_string = False
    escape_next = False

    for i in range(start_pos, len(text)):
        char = text[i]

        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":
            brace_count += 1
        elif char == "}":
            brace_count -= 1
            if brace_count == 0:
                return text[start_pos : i + 1]

    return None


def extract_ytcfg(html: str) -> Dict[str, Any]:
    ytcfg_str = _regex_search(html, YT_CFG_RE, default=None)
    if not ytcfg_str:
        ytcfg_str = _extract_json_object(html, r"ytcfg\.set\s*\(\s*\{")
    if not ytcfg_str:
        raise RuntimeError("Failed to extract ytcfg")
    try:
        return json.loads(ytcfg_str)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse ytcfg JSON: {e}")


def extract_ytinitialdata(html: str) -> Dict[str, Any]:
    data_str = _regex_search(html, YT_INITIAL_DATA_RE, default=None)
    if not data_str:
        data_str = _extract_json_object(
            html, r"(?:window\s*\[\s*[\"']ytInitialData[\"']\s*\]|ytInitialData)\s*=\s*\{"
        )
    if not data_str:
        raise RuntimeError("Failed to extract ytInitialData")
    try:
        return json.loads(data_str)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse ytInitialData JSON: {e}")
