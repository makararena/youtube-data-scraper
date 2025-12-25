"""
Job specification loader.

Parses questions.yaml into a structured JobSpec that combines:
- Input configuration (where to load comments from)
- Task definitions (what analysis to run)
- Custom prompt (optional context)
"""
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ytce.ai.domain.task import TaskConfig, TaskType
from ytce.ai.input.config import InputConfig
from ytce.ai.input.validators import validate_tasks_config


@dataclass(frozen=True)
class JobSpec:
    """
    Parsed job specification loaded from questions.yaml.
    Pure input-layer DTO.
    
    Combines all job-level configuration:
    - input: Where to load comments from
    - tasks: What analysis tasks to run
    - custom_prompt: Optional background context
    """
    
    input: InputConfig
    tasks: List[TaskConfig]
    custom_prompt: Optional[str] = None


def load_job(path: str) -> JobSpec:
    """
    Load and parse questions.yaml into a JobSpec.
    
    Pipeline:
    1. Load YAML file
    2. Validate structure (job-level)
    3. Parse input section
    4. Parse tasks section (reuses existing validator)
    5. Extract custom_prompt
    6. Assemble JobSpec
    
    Args:
        path: Path to questions.yaml file
        
    Returns:
        JobSpec containing parsed configuration
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If structure is invalid or required fields are missing
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Job file not found: {path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    
    if not isinstance(raw, dict):
        raise ValueError("Invalid job file: expected YAML mapping")
    
    _validate_job_structure(raw)
    
    input_cfg = _parse_input(raw["input"])
    tasks = _parse_tasks(raw["tasks"])
    custom_prompt = raw.get("custom_prompt")
    
    # Normalize custom_prompt: empty string -> None
    if custom_prompt == "":
        custom_prompt = None
    
    return JobSpec(
        input=input_cfg,
        tasks=tasks,
        custom_prompt=custom_prompt,
    )


def _validate_job_structure(raw: Dict[str, Any]) -> None:
    """
    Validate job-level structure.
    
    Checks that required top-level sections exist.
    Does NOT validate task-specific rules (labels, scale, etc.) -
    that's done by validate_tasks_config.
    """
    if "input" not in raw:
        raise ValueError("Job file is missing 'input' section")
    
    if "tasks" not in raw:
        raise ValueError("Job file is missing 'tasks' section")
    
    if not isinstance(raw["tasks"], list) or not raw["tasks"]:
        raise ValueError("'tasks' must be a non-empty list")


def _parse_input(raw_input: Dict[str, Any]) -> InputConfig:
    """
    Parse input section into InputConfig.
    
    Pure mapping: no validation logic, just structure extraction.
    """
    required_fields = ["path", "format", "id_field", "text_field"]
    
    for field in required_fields:
        if field not in raw_input:
            raise ValueError(f"Input section is missing '{field}'")
    
    return InputConfig(
        path=str(raw_input["path"]),
        format=str(raw_input["format"]),
        id_field=str(raw_input["id_field"]),
        text_field=str(raw_input["text_field"]),
    )


def _parse_tasks(raw_tasks: List[Dict[str, Any]]) -> List[TaskConfig]:
    """
    Parse tasks section into List[TaskConfig].
    
    Reuses existing validate_tasks_config to avoid duplication.
    """
    # Reuse existing validator
    validate_tasks_config(raw_tasks)
    
    tasks: List[TaskConfig] = []
    
    for task in raw_tasks:
        tasks.append(
            TaskConfig(
                id=task["id"],
                type=TaskType(task["type"]),
                question=task["question"],
                labels=task.get("labels"),
                max_labels=task.get("max_labels"),
                scale=tuple(task["scale"]) if "scale" in task else None,
            )
        )
    
    return tasks


__all__ = ["JobSpec", "load_job"]

