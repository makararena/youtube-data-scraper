from __future__ import annotations

from typing import Tuple

import requests

from ytce.youtube.session import handle_consent


def fetch_html(session: requests.Session, url: str, *, timeout: int = 30) -> Tuple[str, str]:
    response = session.get(url, timeout=timeout)
    response = handle_consent(session, response, url, timeout=timeout)
    return response.text, str(response.url)
