"""
Task executors for AI comment analysis.

This module provides executors for each task type that:
- Compile prompts using the prompt layer
- Call LLM models using the model layer
- Parse and validate JSON responses
- Return structured TaskResult objects
"""
from typing import Dict, List, Optional, Tuple

from ytce.ai.domain.comment import Comment
from ytce.ai.domain.config import RunConfig
from ytce.ai.domain.result import TaskResult
from ytce.ai.domain.task import TaskConfig, TaskType
from ytce.ai.models.base import ModelAdapter
from ytce.ai.models.tokens import TokenUsage
from ytce.ai.tasks.base import InvalidResponseError, TaskExecutionError
from ytce.ai.tasks.binary_classification import execute_task as execute_binary
from ytce.ai.tasks.multi_class import execute_task as execute_multi_class
from ytce.ai.tasks.multi_label import execute_task as execute_multi_label
from ytce.ai.tasks.scoring import execute_task as execute_scoring
from ytce.ai.tasks.translation import execute_task as execute_translation
from ytce.ai.tasks.language_detection import execute_task as execute_language_detection


def execute_task(
    task: TaskConfig,
    comments: List[Comment],
    model: ModelAdapter,
    run_config: RunConfig,
    custom_prompt: Optional[str] = None,
) -> Tuple[Dict[str, TaskResult], TokenUsage]:
    """
    Execute a task on a list of comments.
    
    This is the main entry point for task execution. It dispatches to the
    appropriate executor based on the task type.
    
    Args:
        task: TaskConfig describing the task to execute
        comments: List of comments to analyze
        model: ModelAdapter for LLM calls
        run_config: Runtime configuration
        custom_prompt: Optional custom context/background information
        
    Returns:
        Tuple of (Dictionary mapping comment_id to TaskResult, TokenUsage)
        
    Raises:
        ValueError: If task type is not supported
        TaskExecutionError: If execution fails
        InvalidResponseError: If LLM response cannot be parsed or validated
        
    Example:
        >>> from ytce.ai.domain.task import TaskConfig, TaskType
        >>> from ytce.ai.domain.comment import Comment
        >>> from ytce.ai.domain.config import RunConfig
        >>> from ytce.ai.models import create_adapter
        >>> 
        >>> task = TaskConfig(
        ...     id="sentiment",
        ...     type=TaskType.BINARY_CLASSIFICATION,
        ...     question="Is this positive?",
        ...     labels=["yes", "no"]
        ... )
        >>> 
        >>> comments = [Comment(id="c1", text="Great!")]
        >>> run_config = RunConfig(model="gpt-4.1-nano", api_key="sk-...")
        >>> model = create_adapter(run_config.model, run_config.api_key)
        >>> 
        >>> results = execute_task(task, comments, model, run_config)
        >>> print(results["c1"].value)
        "yes"
    """
    if task.type == TaskType.BINARY_CLASSIFICATION:
        return execute_binary(task, comments, model, run_config, custom_prompt)
    elif task.type == TaskType.MULTI_CLASS:
        return execute_multi_class(task, comments, model, run_config, custom_prompt)
    elif task.type == TaskType.MULTI_LABEL:
        return execute_multi_label(task, comments, model, run_config, custom_prompt)
    elif task.type == TaskType.SCORING:
        return execute_scoring(task, comments, model, run_config, custom_prompt)
    elif task.type == TaskType.TRANSLATION:
        return execute_translation(task, comments, model, run_config, custom_prompt)
    elif task.type == TaskType.LANGUAGE_DETECTION:
        return execute_language_detection(task, comments, model, run_config, custom_prompt)
    else:
        raise ValueError(f"Unsupported task type: {task.type}")


__all__ = [
    "execute_task",
    "TaskExecutionError",
    "InvalidResponseError",
]

