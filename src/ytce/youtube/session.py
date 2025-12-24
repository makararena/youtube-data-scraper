from __future__ import annotations

import re

import requests

# Keep the UA identical across scrapers to avoid behavioral divergence.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36"
)

YOUTUBE_CONSENT_URL = "https://consent.youtube.com/save"
YT_HIDDEN_INPUT_RE = (
    r'<input\s+type="hidden"\s+name="([A-Za-z0-9_]+)"\s+value="([A-Za-z0-9_\-\.]*)"\s*'
    r'(?:required|)\s*>'
)


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    session.cookies.set("CONSENT", "YES+cb", domain=".youtube.com")
    return session


def handle_consent(
    session: requests.Session,
    response: requests.Response,
    continue_url: str,
    *,
    timeout: int = 30,
) -> requests.Response:
    """
    If YouTube redirects to a consent page, accept automatically and return the final response.
    """
    if "consent" not in str(response.url):
        return response
    params = dict(re.findall(YT_HIDDEN_INPUT_RE, response.text))
    params.update({"continue": continue_url, "set_eom": False, "set_ytc": True, "set_apyt": True})
    return session.post(YOUTUBE_CONSENT_URL, params=params, timeout=timeout)
