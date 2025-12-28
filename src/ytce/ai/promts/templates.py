"""
Prompt templates for different task types.

This module provides base prompt templates that are customized
by the prompt compiler based on TaskConfig.
"""
from typing import List, Optional

from ytce.ai.domain.comment import Comment
from ytce.ai.domain.task import TaskConfig, TaskType
from ytce.ai.promts.formatter import format_comments_for_prompt, format_json_schema


# Prompt version for tracking changes
PROMPT_VERSION = "1.0"


def get_task_instruction(task: TaskConfig) -> str:
    """
    Get task-specific instruction text based on task type.
    
    Args:
        task: TaskConfig describing the task
        
    Returns:
        Instruction string for the task
    """
    if task.type == TaskType.BINARY_CLASSIFICATION:
        return _get_binary_instruction(task)
    elif task.type == TaskType.MULTI_CLASS:
        return _get_multi_class_instruction(task)
    elif task.type == TaskType.MULTI_LABEL:
        return _get_multi_label_instruction(task)
    elif task.type == TaskType.SCORING:
        return _get_scoring_instruction(task)
    elif task.type == TaskType.TRANSLATION:
        return _get_translation_instruction(task)
    elif task.type == TaskType.LANGUAGE_DETECTION:
        return _get_language_detection_instruction(task)
    else:
        raise ValueError(f"Unknown task type: {task.type}")


def _get_binary_instruction(task: TaskConfig) -> str:
    """Get instruction for binary classification."""
    if not task.labels or len(task.labels) != 2:
        raise ValueError(
            f"Binary classification requires exactly 2 labels, got: {task.labels}"
        )
    
    label1, label2 = task.labels[0], task.labels[1]
    
    return f"""You are analyzing comments and need to classify each one into exactly one of two categories: "{label1}" or "{label2}".

For each comment, determine which category it belongs to based on the question: "{task.question}"

You must choose exactly one label for each comment."""


def _get_multi_class_instruction(task: TaskConfig) -> str:
    """Get instruction for multi-class classification."""
    if not task.labels:
        raise ValueError(f"Multi-class classification requires labels, got: {task.labels}")
    
    labels_list = ", ".join(f'"{label}"' for label in task.labels)
    
    return f"""You are analyzing comments and need to classify each one into exactly one category.

Question: {task.question}

Available categories: {labels_list}

For each comment, determine which single category it belongs to. You must choose exactly one label for each comment."""


def _get_multi_label_instruction(task: TaskConfig) -> str:
    """Get instruction for multi-label classification."""
    if not task.labels:
        raise ValueError(f"Multi-label classification requires labels, got: {task.labels}")
    
    labels_list = ", ".join(f'"{label}"' for label in task.labels)
    max_labels_text = f" You can select up to {task.max_labels} labels per comment." if task.max_labels else ""
    
    return f"""You are analyzing comments and need to identify which topics/categories apply to each comment.

Question: {task.question}

Available labels: {labels_list}

For each comment, select all labels that apply.{max_labels_text} A comment can have zero, one, or multiple labels."""


def _get_scoring_instruction(task: TaskConfig) -> str:
    """Get instruction for scoring tasks."""
    if not task.scale:
        raise ValueError(f"Scoring task requires scale, got: {task.scale}")
    
    min_score, max_score = task.scale
    
    return f"""You are analyzing comments and need to assign a numeric score to each one.

Question: {task.question}

Score range: {min_score} to {max_score} (inclusive)

For each comment, assign a score between {min_score} and {max_score} that reflects your assessment. Use the full range appropriately."""


def _get_translation_instruction(task: TaskConfig) -> str:
    """Get instruction for translation tasks."""
    if not task.target_language or not task.target_language.strip():
        raise ValueError("Translation task requires non-empty target_language")

    target_language = task.target_language.strip()

    # task.question is still required by the input layer; we treat it as additional guidance.
    extra = f'\n\nAdditional guidance: "{task.question}"' if task.question and task.question.strip() else ""

    return f"""You are translating YouTube comments into the target language: "{target_language}".

For each comment:
- Preserve meaning, tone, and intent.
- Preserve emojis, punctuation, and formatting where reasonable.
- Preserve proper nouns, product names, and usernames.
- Do not add explanations or commentary; output ONLY the translation text.
- If the comment is already in "{target_language}", return it unchanged.
- If the comment contains multiple languages, translate all content into "{target_language}" (keep names/handles as-is).{extra}"""


def _get_language_detection_instruction(task: TaskConfig) -> str:
    """Get instruction for language detection tasks."""
    return f"""You are analyzing comments to detect the primary language of each comment.

Question: {task.question}

For each comment, identify the primary language and return its ISO 639-1 or ISO 639-2 language code (e.g., "en" for English, "ru" for Russian, "es" for Spanish, "fr" for French, "de" for German, "zh" for Chinese, "ja" for Japanese, "ko" for Korean, etc.).

Important:
- Use standard ISO 639 language codes (2-letter codes preferred, 3-letter codes acceptable)
- If a comment contains multiple languages, identify the primary/dominant language
- If a comment is mostly emojis or symbols without clear language, use "und" (undetermined) or "mul" (multiple languages)
- Return the language code in lowercase (e.g., "en", not "EN")
- Be confident in your detection - use high confidence scores (0.8-1.0) when the language is clear"""


def build_base_prompt(
    task: TaskConfig,
    comments: List[Comment],
    custom_prompt: Optional[str] = None,
    max_comment_length: Optional[int] = None,
) -> str:
    """
    Build the complete prompt for a task.
    
    This is the main template function that combines:
    - Task-specific instructions
    - Custom context (if provided)
    - Comment data
    - JSON output format requirements
    
    Args:
        task: TaskConfig describing the task
        comments: List of comments to analyze
        custom_prompt: Optional custom context/background information
        
    Returns:
        Complete prompt string ready to send to LLM
    """
    # Build prompt sections
    sections = []
    
    # Header with version
    sections.append(f"# AI Comment Analysis Task (Prompt Version {PROMPT_VERSION})")
    sections.append("")
    
    # Custom context (if provided)
    if custom_prompt:
        sections.append("## Context")
        sections.append(custom_prompt.strip())
        sections.append("")
    
    # Task instruction
    sections.append("## Task")
    sections.append(get_task_instruction(task))
    sections.append("")
    
    # Comments to analyze
    sections.append("## Comments to Analyze")
    sections.append(format_comments_for_prompt(comments, max_comment_length=max_comment_length))
    sections.append("")
    
    # Output format requirements
    sections.append("## Output Format")
    sections.append(format_json_schema(task))
    sections.append("")
    
    # Final instructions
    sections.append("## Instructions")
    sections.append(
        """Please analyze all comments above and return your results as a JSON array.
Each element in the array must correspond to one comment, using the exact format specified above.
Ensure all comment IDs match exactly, and that your output is valid JSON."""
    )
    
    return "\n".join(sections)


__all__ = [
    "PROMPT_VERSION",
    "get_task_instruction",
    "build_base_prompt",
]

