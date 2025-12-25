import yaml
from dataclasses import dataclass
from typing import List, Optional

from ytce.ai.domain.task import TaskConfig, TaskType
from .validators import validate_tasks_config


@dataclass(frozen=True)
class QuestionsConfig:
    """
    Configuration loaded from questions.yaml.
    
    Contains:
    - tasks: List of analysis tasks to perform
    - custom_prompt: Optional background story/context about the channel
    """
    tasks: List[TaskConfig]
    custom_prompt: Optional[str] = None


def load_questions(path: str) -> QuestionsConfig:
    """
    Load questions.yaml and convert it into a QuestionsConfig object.
    
    Returns:
        QuestionsConfig containing tasks and optional custom_prompt
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw or "tasks" not in raw:
        raise ValueError("questions.yaml must contain top-level 'tasks' field")

    tasks_raw = raw["tasks"]

    validate_tasks_config(tasks_raw)

    task_configs: List[TaskConfig] = []

    for task in tasks_raw:
        task_configs.append(
            TaskConfig(
                id=task["id"],
                type=TaskType(task["type"]),
                question=task["question"],
                labels=task.get("labels"),
                max_labels=task.get("max_labels"),
                scale=tuple(task["scale"]) if "scale" in task else None,
            )
        )

    # Extract custom_prompt if present
    custom_prompt = raw.get("custom_prompt")
    if custom_prompt is not None and not isinstance(custom_prompt, str):
        raise ValueError("'custom_prompt' must be a string if provided")

    return QuestionsConfig(
        tasks=task_configs,
        custom_prompt=custom_prompt if custom_prompt else None,
    )


__all__ = ["QuestionsConfig", "load_questions"]
