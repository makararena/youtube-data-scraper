from dataclasses import dataclass
from typing import Dict, List, Optional, Union

@dataclass(frozen=True)
class TaskResult:
    """
    Result of a single task for a single comment.

    DOMAIN object:
    - contains no execution logic
    - contains no formatting logic
    - represents a normalized, structured outcome
    """

    # The actual result value.
    #
    # Possible types:
    # - str           → binary / multi_class
    # - List[str]     → multi_label
    # - float         → scoring
    value: Union[str, List[str], float]

    # Optional confidence score provided by the model.
    # Range is expected to be [0.0, 1.0], but this is NOT enforced here.
    confidence: Optional[float] = None

@dataclass(frozen=True)
class EnrichedComment:
    """
    Comment enriched with results of all analysis tasks.
    """

    id: str
    text: str

    # Original metadata passed through the system unchanged
    metadata: Optional[Dict] = None

    # Mapping: task_id -> TaskResult
    results: Dict[str, TaskResult] = None

__all__ = [
    "TaskResult",
    "EnrichedComment",
]
