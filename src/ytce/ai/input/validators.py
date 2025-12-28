from typing import List, Dict, Set

from ytce.ai.domain.task import TaskType


def validate_tasks_config(tasks: List[Dict]) -> None:
    """
    Validate raw task definitions loaded from YAML.
    Raises ValueError on first violation.
    """

    if not isinstance(tasks, list) or not tasks:
        raise ValueError("'tasks' must be a non-empty list")

    seen_ids: Set[str] = set()

    for task in tasks:
        _validate_single_task(task, seen_ids)


def _validate_single_task(task: Dict, seen_ids: Set[str]) -> None:
    # --- id ---
    task_id = task.get("id")
    if not isinstance(task_id, str) or not task_id:
        raise ValueError("Each task must have a non-empty string 'id'")

    if task_id in seen_ids:
        raise ValueError(f"Duplicate task id: '{task_id}'")
    seen_ids.add(task_id)

    # --- type ---
    task_type_raw = task.get("type")
    if task_type_raw not in [t.value for t in TaskType]:
        raise ValueError(f"Invalid task type: {task_type_raw}")

    task_type = TaskType(task_type_raw)

    # --- question ---
    question = task.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"Task '{task_id}' must have a non-empty 'question'")

    labels = task.get("labels")
    max_labels = task.get("max_labels")
    scale = task.get("scale")
    target_language = task.get("target_language")

    # --- type-specific rules ---
    if task_type == TaskType.BINARY_CLASSIFICATION:
        if not isinstance(labels, list) or len(labels) != 2:
            raise ValueError(f"Task '{task_id}': binary_classification requires exactly 2 labels")
        _forbid(task_id, scale=scale, max_labels=max_labels)

    elif task_type == TaskType.MULTI_CLASS:
        if not isinstance(labels, list) or len(labels) < 3:
            raise ValueError(f"Task '{task_id}': multi_class requires at least 3 labels")
        _forbid(task_id, scale=scale, max_labels=max_labels)

    elif task_type == TaskType.MULTI_LABEL:
        if not isinstance(labels, list) or not labels:
            raise ValueError(f"Task '{task_id}': multi_label requires labels")
        if not isinstance(max_labels, int) or max_labels < 1 or max_labels > len(labels):
            raise ValueError(
                f"Task '{task_id}': max_labels must be between 1 and len(labels)"
            )
        _forbid(task_id, scale=scale)

    elif task_type == TaskType.SCORING:
        if not isinstance(scale, list) or len(scale) != 2:
            raise ValueError(f"Task '{task_id}': scoring requires scale: [min, max]")
        if not scale[0] < scale[1]:
            raise ValueError(f"Task '{task_id}': scale[0] must be < scale[1]")
        _forbid(task_id, labels=labels, max_labels=max_labels)

    elif task_type == TaskType.TRANSLATION:
        if not isinstance(target_language, str) or not target_language.strip():
            raise ValueError(
                f"Task '{task_id}': translation requires non-empty 'target_language' (e.g., 'Russian' or 'ru')"
            )
        _forbid(task_id, labels=labels, max_labels=max_labels, scale=scale)

    elif task_type == TaskType.LANGUAGE_DETECTION:
        # Language detection doesn't require any additional fields
        _forbid(task_id, labels=labels, max_labels=max_labels, scale=scale, target_language=target_language)


def _forbid(task_id: str, **fields):
    for name, value in fields.items():
        if value is not None:
            raise ValueError(f"Task '{task_id}': field '{name}' is not allowed for this task type")
