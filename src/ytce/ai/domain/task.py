from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


class TaskType(str, Enum):
    """
    Supported task types for AI analysis.

    IMPORTANT:
    - This enum is CLOSED by design.
    - New task types must be added explicitly.
    """

    BINARY_CLASSIFICATION = "binary_classification"
    MULTI_CLASS = "multi_class"
    MULTI_LABEL = "multi_label"
    SCORING = "scoring"
    TRANSLATION = "translation"
    LANGUAGE_DETECTION = "language_detection"


@dataclass(frozen=True)
class TaskConfig:
    """
    Declarative description of a single analysis task.

    This is a DOMAIN object:
    - no execution logic
    - no validation logic
    - no model or prompt details

    It describes WHAT the task means, not HOW it is executed.
    """

    # Stable identifier of the task.
    # Used as:
    # - result key
    # - CSV column prefix
    # - external reference (YAML, API)
    id: str

    # Type of task that defines expected output contract
    type: TaskType

    # Semantic intent of the task (user-defined)
    # This is the core signal passed to the LLM.
    question: str

    # --- Classification-related fields ---

    # Allowed labels for classification tasks
    # Required for:
    # - BINARY_CLASSIFICATION
    # - MULTI_CLASS
    # - MULTI_LABEL
    labels: Optional[List[str]] = None

    # Maximum number of labels that can be assigned
    # Used ONLY for MULTI_LABEL tasks
    max_labels: Optional[int] = None

    # --- Scoring-related fields ---

    # Numeric range of the score (min, max)
    # Required ONLY for SCORING tasks
    scale: Optional[Tuple[float, float]] = None

    # --- Translation-related fields ---
    # Target language for translation tasks (e.g., "Russian", "ru", "Spanish")
    # Required ONLY for TRANSLATION tasks
    target_language: Optional[str] = None


__all__ = [
    "TaskType",
    "TaskConfig",
]
