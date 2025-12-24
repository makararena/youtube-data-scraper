from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple

import requests

# Keep the UA identical across scrapers to avoid behavioral divergence.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36"
)

YOUTUBE_CONSENT_URL = "https://consent.youtube.com/save"

YT_CFG_RE = r"ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;"
YT_INITIAL_DATA_RE = (
    r"(?:window\s*\[\s*[\"']ytInitialData[\"']\s*\]|ytInitialData)\s*=\s*({.+?})\s*;"
    r"\s*(?:var\s+meta|</script|\n)"
)
YT_HIDDEN_INPUT_RE = (
    r'<input\s+type="hidden"\s+name="([A-Za-z0-9_]+)"\s+value="([A-Za-z0-9_\-\.]*)"\s*(?:required|)\s*>'
)


def ensure_repo_root_on_syspath(current_file: str, levels_up: int = 2) -> None:
    """
    Add repo root to sys.path so modules in subfolders can import `shared`.

    levels_up=2 works for:
      repo/youtube-channel-videos/youtube_channel_videos/*.py
      repo/youtube-comment-downloader/youtube_comment_downloader/*.py
    """
    import os
    import sys

    repo_root = os.path.abspath(os.path.join(os.path.dirname(current_file), *[".."] * levels_up))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    session.cookies.set("CONSENT", "YES+cb", domain=".youtube.com")
    return session


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


def handle_consent(session: requests.Session, response: requests.Response, continue_url: str, *, timeout: int = 30) -> requests.Response:
    """
    If YouTube redirects to a consent page, accept automatically and return the final response.
    """
    if "consent" not in str(response.url):
        return response
    params = dict(re.findall(YT_HIDDEN_INPUT_RE, response.text))
    params.update({"continue": continue_url, "set_eom": False, "set_ytc": True, "set_apyt": True})
    return session.post(YOUTUBE_CONSENT_URL, params=params, timeout=timeout)


def fetch_html(session: requests.Session, url: str, *, timeout: int = 30) -> Tuple[str, str]:
    response = session.get(url, timeout=timeout)
    response = handle_consent(session, response, url, timeout=timeout)
    return response.text, str(response.url)


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


def inertube_ajax_request(
    session: requests.Session,
    endpoint: Dict[str, Any],
    ytcfg: Dict[str, Any],
    *,
    retries: int = 5,
    sleep: float = 2.0,
    timeout: int = 60,
) -> Dict[str, Any]:
    url = "https://www.youtube.com" + endpoint["commandMetadata"]["webCommandMetadata"]["apiUrl"]
    payload = {"context": ytcfg["INNERTUBE_CONTEXT"], "continuation": endpoint["continuationCommand"]["token"]}

    for _ in range(retries):
        try:
            resp = session.post(url, params={"key": ytcfg["INNERTUBE_API_KEY"]}, json=payload, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (403, 413):
                return {}
        except requests.exceptions.Timeout:
            pass
        time.sleep(sleep)
    return {}


def search_dict(partial: Any, search_key: str) -> Generator[Any, None, None]:
    """
    DFS stack traversal of nested dict/list.
    NOTE: This does NOT preserve list ordering; do NOT use this to build ordered result lists.
    """
    stack: List[Any] = [partial]
    while stack:
        current_item = stack.pop()
        if isinstance(current_item, dict):
            for key, value in current_item.items():
                if key == search_key:
                    yield value
                else:
                    stack.append(value)
        elif isinstance(current_item, list):
            stack.extend(current_item)


def pick_longest_continuation(endpoints: Iterable[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    endpoints = list(endpoints)
    if not endpoints:
        return None
    return max(endpoints, key=lambda x: len(x.get("continuationCommand", {}).get("token", "")))


def parse_view_count(view_count_raw: str) -> Optional[int]:
    """
    Convert localized view strings into an integer when possible.
    Examples:
      "123 874 vues" -> 123874
      "1.2M views"   -> 1200000
      "500K views"   -> 500000
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


