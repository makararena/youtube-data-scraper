"""
JSON output formatting helpers for prompt generation.

This module provides utilities to generate JSON schema descriptions
for different task types, ensuring consistent output format.
"""
from typing import List, Optional, Tuple

from ytce.ai.domain.comment import Comment
from ytce.ai.domain.task import TaskConfig, TaskType


def format_json_schema(task: TaskConfig) -> str:
    """
    Generate JSON schema description for task output.
    
    Returns a human-readable description of the expected JSON output format
    based on the task type and configuration.
    
    Args:
        task: TaskConfig describing the task
        
    Returns:
        String description of expected JSON output format
        
    Examples:
        >>> task = TaskConfig(
        ...     id="sentiment",
        ...     type=TaskType.BINARY_CLASSIFICATION,
        ...     question="Is this positive?",
        ...     labels=["yes", "no"]
        ... )
        >>> schema = format_json_schema(task)
        >>> "yes" in schema
        True
    """
    if task.type == TaskType.BINARY_CLASSIFICATION:
        return _format_binary_schema(task)
    elif task.type == TaskType.MULTI_CLASS:
        return _format_multi_class_schema(task)
    elif task.type == TaskType.MULTI_LABEL:
        return _format_multi_label_schema(task)
    elif task.type == TaskType.SCORING:
        return _format_scoring_schema(task)
    elif task.type == TaskType.TRANSLATION:
        return _format_translation_schema(task)
    elif task.type == TaskType.LANGUAGE_DETECTION:
        return _format_language_detection_schema(task)
    else:
        raise ValueError(f"Unknown task type: {task.type}")


def _format_binary_schema(task: TaskConfig) -> str:
    """Format JSON schema for binary classification."""
    if not task.labels or len(task.labels) != 2:
        raise ValueError(
            f"Binary classification requires exactly 2 labels, got: {task.labels}"
        )
    
    label1, label2 = task.labels[0], task.labels[1]
    
    return f"""The output must be a JSON array where each element is an object with:
- "comment_id": string (the ID of the comment)
- "value": string (must be exactly one of: "{label1}" or "{label2}")
- "confidence": number (optional, between 0.0 and 1.0)

Example:
[
  {{"comment_id": "comment_1", "value": "{label1}", "confidence": 0.95}},
  {{"comment_id": "comment_2", "value": "{label2}", "confidence": 0.87}}
]"""


def _format_multi_class_schema(task: TaskConfig) -> str:
    """Format JSON schema for multi-class classification."""
    if not task.labels:
        raise ValueError(f"Multi-class classification requires labels, got: {task.labels}")
    
    labels_str = ", ".join(f'"{label}"' for label in task.labels)
    
    return f"""The output must be a JSON array where each element is an object with:
- "comment_id": string (the ID of the comment)
- "value": string (must be exactly one of: {labels_str})
- "confidence": number (optional, between 0.0 and 1.0)

Example:
[
  {{"comment_id": "comment_1", "value": "{task.labels[0]}", "confidence": 0.92}},
  {{"comment_id": "comment_2", "value": "{task.labels[1] if len(task.labels) > 1 else task.labels[0]}", "confidence": 0.88}}
]"""


def _format_multi_label_schema(task: TaskConfig) -> str:
    """Format JSON schema for multi-label classification."""
    if not task.labels:
        raise ValueError(f"Multi-label classification requires labels, got: {task.labels}")
    
    labels_str = ", ".join(f'"{label}"' for label in task.labels)
    max_labels_text = f" (maximum {task.max_labels} labels)" if task.max_labels else ""
    
    return f"""The output must be a JSON array where each element is an object with:
- "comment_id": string (the ID of the comment)
- "value": array of strings (each string must be one of: {labels_str}){max_labels_text}
- "confidence": number (optional, between 0.0 and 1.0)

Example:
[
  {{"comment_id": "comment_1", "value": ["{task.labels[0]}", "{task.labels[1] if len(task.labels) > 1 else task.labels[0]}"], "confidence": 0.91}},
  {{"comment_id": "comment_2", "value": ["{task.labels[0]}"], "confidence": 0.85}}
]"""


def _format_scoring_schema(task: TaskConfig) -> str:
    """Format JSON schema for scoring tasks."""
    if not task.scale:
        raise ValueError(f"Scoring task requires scale, got: {task.scale}")
    
    min_score, max_score = task.scale
    
    return f"""The output must be a JSON array where each element is an object with:
- "comment_id": string (the ID of the comment)
- "value": number (must be between {min_score} and {max_score}, inclusive)
- "confidence": number (optional, between 0.0 and 1.0)

Example:
[
  {{"comment_id": "comment_1", "value": {min_score + (max_score - min_score) * 0.7:.2f}, "confidence": 0.93}},
  {{"comment_id": "comment_2", "value": {min_score + (max_score - min_score) * 0.3:.2f}, "confidence": 0.89}}
]"""


def _format_translation_schema(task: TaskConfig) -> str:
    """Format JSON schema for translation tasks."""
    if not task.target_language or not task.target_language.strip():
        raise ValueError(f"Translation task requires target_language, got: {task.target_language}")

    target_language = task.target_language.strip()

    return f"""The output must be a JSON array where each element is an object with:
- "comment_id": string (the ID of the comment)
- "value": string (the translated comment text in "{target_language}")
- "confidence": number (optional, between 0.0 and 1.0)

Example:
[
  {{"comment_id": "comment_1", "value": "Пример перевода.", "confidence": 0.93}},
  {{"comment_id": "comment_2", "value": "Ещё один пример.", "confidence": 0.88}}
]"""


def _format_language_detection_schema(task: TaskConfig) -> str:
    """Format JSON schema for language detection tasks."""
    return """The output must be a JSON array where each element is an object with:
- "comment_id": string (the ID of the comment)
- "value": string (ISO 639-1 or ISO 639-2 language code, e.g., "en", "ru", "es", "fr", "de", "zh", "ja", "ko")
- "confidence": number (optional, between 0.0 and 1.0, indicating confidence in language detection)

Example:
[
  {"comment_id": "comment_1", "value": "en", "confidence": 0.95},
  {"comment_id": "comment_2", "value": "ru", "confidence": 0.92},
  {"comment_id": "comment_3", "value": "es", "confidence": 0.88},
  {"comment_id": "comment_4", "value": "und", "confidence": 0.65}
]

Common ISO 639-1 codes:
- "en" = English
- "ru" = Russian
- "es" = Spanish
- "fr" = French
- "de" = German
- "zh" = Chinese
- "ja" = Japanese
- "ko" = Korean
- "pt" = Portuguese
- "it" = Italian
- "ar" = Arabic
- "hi" = Hindi
- "und" = Undetermined (for unclear/mixed content)
- "mul" = Multiple languages"""


def truncate_comment_text(text: str, max_length: int) -> tuple[str, bool]:
    """
    Truncate comment text intelligently, preserving word boundaries when possible.
    
    Args:
        text: Comment text to truncate
        max_length: Maximum length in characters
        
    Returns:
        Tuple of (truncated_text, was_truncated)
    """
    if len(text) <= max_length:
        return text, False
    
    # Try to truncate at word boundary
    truncated = text[:max_length]
    # Find last space before the limit
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:  # Only use word boundary if it's not too far back
        truncated = truncated[:last_space]
    
    return truncated + "...", True


def format_comments_for_prompt(comments: List[Comment], max_comment_length: Optional[int] = None) -> str:
    """
    Format a list of comments into a string representation for the prompt.
    
    Args:
        comments: List of Comment domain objects
        max_comment_length: Optional maximum characters per comment (longer will be truncated)
        
    Returns:
        Formatted string with comment IDs and text
    """
    lines = []
    truncated_count = 0
    
    for i, comment in enumerate(comments, 1):
        lines.append(f"Comment {i}:")
        lines.append(f"  ID: {comment.id}")
        
        # Truncate comment text if needed
        comment_text = comment.text
        if max_comment_length and len(comment_text) > max_comment_length:
            comment_text, was_truncated = truncate_comment_text(comment_text, max_comment_length)
            if was_truncated:
                truncated_count += 1
        
        lines.append(f"  Text: {comment_text}")
        if comment.author:
            lines.append(f"  Author: {comment.author}")
        lines.append("")  # Empty line between comments
    
    # Add note if any comments were truncated
    if truncated_count > 0:
        note = f"\nNote: {truncated_count} comment(s) were truncated to {max_comment_length} characters for token efficiency.\n"
        # Insert note before the comments section
        return note + "\n".join(lines)
    
    return "\n".join(lines)


__all__ = [
    "format_json_schema",
    "format_comments_for_prompt",
]

