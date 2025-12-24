from __future__ import annotations

import time
from typing import Any, Dict

import requests


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
