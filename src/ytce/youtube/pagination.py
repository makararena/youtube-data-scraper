from __future__ import annotations

from typing import Any, Dict, Generator, Iterable, List, Optional


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
