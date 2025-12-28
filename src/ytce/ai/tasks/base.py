"""
Base task executor and shared utilities.

This module provides base functionality for all task executors, including
JSON parsing, response validation, and error handling.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Tuple

from ytce.ai.domain.comment import Comment
from ytce.ai.domain.config import RunConfig
from ytce.ai.domain.result import TaskResult
from ytce.ai.domain.task import TaskConfig
from ytce.ai.models.base import ModelAdapter
from ytce.ai.models.errors import ModelError
from ytce.ai.promts import compile_prompt

if TYPE_CHECKING:
    from ytce.ai.models.tokens import TokenUsage

logger = logging.getLogger("ytce.ai.tasks")


class TaskExecutionError(Exception):
    """Base exception for task execution errors."""
    pass


class InvalidResponseError(TaskExecutionError):
    """Error raised when LLM response cannot be parsed or validated."""
    pass


def _edit_distance(a: str, b: str, max_distance: Optional[int] = None) -> int:
    """
    Compute Levenshtein edit distance between two strings.
    
    Uses a simple dynamic programming approach and optionally short-circuits
    when the minimum possible distance exceeds max_distance.
    """
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    if max_distance is not None and abs(len(a) - len(b)) > max_distance:
        return max_distance + 1
    
    # Use two rows to keep memory small.
    prev_row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur_row = [i]
        min_in_row = cur_row[0]
        for j, cb in enumerate(b, 1):
            insert_cost = cur_row[j - 1] + 1
            delete_cost = prev_row[j] + 1
            replace_cost = prev_row[j - 1] + (0 if ca == cb else 1)
            cur_val = min(insert_cost, delete_cost, replace_cost)
            cur_row.append(cur_val)
            if cur_val < min_in_row:
                min_in_row = cur_val
        if max_distance is not None and min_in_row > max_distance:
            return max_distance + 1
        prev_row = cur_row
    return prev_row[-1]


def _best_fuzzy_match_id(
    raw_id: str,
    candidates: List[str],
    max_distance: int = 2,
) -> Optional[Tuple[str, int]]:
    """
    Find a unique closest candidate within max_distance.
    
    Returns (candidate, distance) if there is a single best match,
    otherwise None to avoid ambiguous corrections.
    """
    best_id = None
    best_distance = max_distance + 1
    is_tie = False
    
    for candidate in candidates:
        distance = _edit_distance(raw_id, candidate, max_distance=max_distance)
        if distance < best_distance:
            best_id = candidate
            best_distance = distance
            is_tie = False
        elif distance == best_distance:
            is_tie = True
    
    if best_id is None or best_distance > max_distance or is_tie:
        return None
    return best_id, best_distance


def parse_json_response(response: str) -> List[Dict[str, Any]]:
    """
    Parse JSON response from LLM.
    
    Handles common issues:
    - JSON wrapped in markdown code blocks
    - Trailing commas
    - Extra whitespace
    
    Args:
        response: Raw response string from LLM
        
    Returns:
        List of result dictionaries
        
    Raises:
        InvalidResponseError: If response cannot be parsed as JSON
    """
    # Remove markdown code blocks if present
    response = response.strip()
    if response.startswith("```"):
        # Extract JSON from code block
        lines = response.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line (```)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response = "\n".join(lines)
    
    # Try to fix common JSON issues before parsing
    # Remove trailing commas before closing brackets/braces
    response = re.sub(r',(\s*[}\]])', r'\1', response)
    
    # Try to parse JSON
    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        # Try to fix common issues before giving up
        error_msg = str(e)
        
        # Check if response was truncated (common with max_tokens limit)
        if "Unterminated string" in error_msg or "Expecting" in error_msg:
            # Try to find where the JSON breaks and provide better error
            error_pos = getattr(e, "pos", None)
            if error_pos:
                # Show context around the error
                start = max(0, error_pos - 100)
                end = min(len(response), error_pos + 100)
                context = response[start:end]
                raise InvalidResponseError(
                    f"Failed to parse JSON response: {error_msg}\n"
                    f"The response may have been truncated (max_tokens limit reached).\n"
                    f"Error at position {error_pos}:\n"
                    f"...{context}...\n"
                    f"\nTry reducing batch_size or increasing max_tokens for this task type."
                )
        
        raise InvalidResponseError(
            f"Failed to parse JSON response: {error_msg}\n"
            f"Response preview: {response[:500]}..."
        )
    
    # Ensure it's a list
    if not isinstance(data, list):
        raise InvalidResponseError(
            f"Expected JSON array, got {type(data).__name__}"
        )
    
    return data


def validate_result_item(
    item: Dict[str, Any],
    task: TaskConfig,
    expected_comment_ids: List[str],
) -> None:
    """
    Validate a single result item against task configuration.
    
    Args:
        item: Result dictionary from LLM
        task: TaskConfig describing expected format
        expected_comment_ids: List of comment IDs that should be present
        
    Raises:
        InvalidResponseError: If validation fails
    """
    # Check required fields
    if "comment_id" not in item:
        raise InvalidResponseError(
            "Result item missing required field: comment_id"
        )
    
    if "value" not in item:
        raise InvalidResponseError(
            "Result item missing required field: value"
        )
    
    comment_id = item["comment_id"]
    value = item["value"]
    
    # Validate comment_id exists
    if comment_id not in expected_comment_ids:
        raise InvalidResponseError(
            f"Unknown comment_id in result: {comment_id}"
        )
    
    # Validate value type and content based on task type
    if task.type.value == "binary_classification":
        if not isinstance(value, str):
            raise InvalidResponseError(
                f"Binary classification expects str, got {type(value).__name__}"
            )
        if task.labels and value not in task.labels:
            raise InvalidResponseError(
                f"Value '{value}' not in allowed labels: {task.labels}"
            )
    
    elif task.type.value == "multi_class":
        if not isinstance(value, str):
            raise InvalidResponseError(
                f"Multi-class expects str, got {type(value).__name__}"
            )
        if task.labels and value not in task.labels:
            raise InvalidResponseError(
                f"Value '{value}' not in allowed labels: {task.labels}"
            )
    
    elif task.type.value == "multi_label":
        if not isinstance(value, list):
            raise InvalidResponseError(
                f"Multi-label expects list, got {type(value).__name__}"
            )
        if not all(isinstance(v, str) for v in value):
            raise InvalidResponseError(
                "Multi-label values must all be strings"
            )
        if task.labels:
            invalid_labels = [v for v in value if v not in task.labels]
            if invalid_labels:
                raise InvalidResponseError(
                    f"Values {invalid_labels} not in allowed labels: {task.labels}"
                )
        if task.max_labels and len(value) > task.max_labels:
            raise InvalidResponseError(
                f"Too many labels: {len(value)} > {task.max_labels}"
            )
    
    elif task.type.value == "scoring":
        if not isinstance(value, (int, float)):
            raise InvalidResponseError(
                f"Scoring expects number, got {type(value).__name__}"
            )
        if task.scale:
            min_score, max_score = task.scale
            if not (min_score <= value <= max_score):
                raise InvalidResponseError(
                    f"Score {value} outside allowed range [{min_score}, {max_score}]"
                )
    
    elif task.type.value == "translation":
        if not isinstance(value, str):
            raise InvalidResponseError(
                f"Translation expects str, got {type(value).__name__}"
            )
        if not value.strip():
            raise InvalidResponseError(
                "Translation value cannot be empty"
            )
    
    elif task.type.value == "language_detection":
        if not isinstance(value, str):
            raise InvalidResponseError(
                f"Language detection expects str (ISO code), got {type(value).__name__}"
            )
        if not value.strip():
            raise InvalidResponseError(
                "Language detection value (ISO code) cannot be empty"
            )
        # Basic validation: ISO 639-1 codes are 2 letters, ISO 639-2 can be 3 letters
        # We'll accept any non-empty string but warn if it doesn't look like an ISO code
        value_clean = value.strip().lower()
        if len(value_clean) < 2 or len(value_clean) > 3:
            logger.warning(
                f"Language code '{value}' doesn't look like a standard ISO 639 code "
                f"(expected 2-3 characters). Continuing anyway."
            )


def convert_to_task_result(
    item: Dict[str, Any],
    task: TaskConfig,
) -> TaskResult:
    """
    Convert validated result item to TaskResult domain object.
    
    Args:
        item: Validated result dictionary
        task: TaskConfig (for type checking)
        
    Returns:
        TaskResult domain object
    """
    value = item["value"]
    confidence = item.get("confidence")
    
    # Ensure value type matches task type
    if task.type.value == "scoring":
        value = float(value)
    elif task.type.value == "multi_label":
        # Ensure it's a list
        if not isinstance(value, list):
            value = [value] if isinstance(value, str) else []
    
    return TaskResult(
        value=value,
        confidence=float(confidence) if confidence is not None else None,
    )


def execute_task_base(
    task: TaskConfig,
    comments: List[Comment],
    model: ModelAdapter,
    run_config: RunConfig,
    custom_prompt: Optional[str] = None,
) -> tuple[Dict[str, TaskResult], "TokenUsage"]:
    """
    Base execution logic shared by all task types.
    
    This function handles:
    1. Prompt compilation
    2. Model invocation
    3. JSON parsing
    4. Response validation
    5. Result conversion
    
    Args:
        task: TaskConfig describing the task
        comments: List of comments to analyze
        model: ModelAdapter for LLM calls
        run_config: Runtime configuration
        custom_prompt: Optional custom context
        
    Returns:
        Dictionary mapping comment_id to TaskResult
        
    Raises:
        InvalidResponseError: If response cannot be parsed or validated
        ModelError: If model call fails
    """
    if not comments:
        from ytce.ai.models.tokens import TokenUsage
        return {}, TokenUsage()
    
    # Compile prompt
    logger.debug(f"Compiling prompt for {len(comments)} comments")
    prompt = compile_prompt(
        task=task,
        comments=comments,
        custom_prompt=custom_prompt,
        max_comment_length=run_config.max_comment_length,
    )
    logger.debug(f"Prompt length: {len(prompt)} characters")
    
    # Determine max_tokens based on task type
    # Translation tasks need more tokens since they output full translated text
    if task.type.value == "translation":
        # Estimate: each comment translation can be up to 2x original length
        # Add buffer for JSON structure (roughly 50 tokens per comment for JSON overhead)
        estimated_tokens = sum(len(c.text.split()) for c in comments) * 3 + (len(comments) * 50) + 500
        max_tokens = max(4000, int(estimated_tokens))
        # Cap at 8000 to avoid hitting model limits, but allow up to 16000 for very long translations
        max_tokens = min(max_tokens, 16000)
        logger.debug(f"Translation task: using max_tokens={max_tokens} (estimated: {estimated_tokens})")
    else:
        max_tokens = 2000  # Classification/scoring tasks need less
        logger.debug(f"Using default max_tokens={max_tokens}")
    
    # Call model
    logger.debug(f"Calling model: {model.get_model_name()}")
    try:
        response, token_usage = model.generate(
            prompt=prompt,
            temperature=run_config.temperature,
            max_tokens=max_tokens,
        )
        logger.debug(f"Model response received: {len(response)} characters, {token_usage.completion_tokens} tokens")
    except ModelError as e:
        raise TaskExecutionError(
            f"Model call failed for task '{task.id}': {str(e)}"
        ) from e
    
    # Parse JSON response
    logger.debug("Parsing JSON response")
    try:
        results = parse_json_response(response)
        logger.debug(f"Parsed {len(results)} result items")
    except InvalidResponseError as e:
        logger.error(f"JSON parsing failed: {str(e)}")
        raise InvalidResponseError(
            f"Failed to parse response for task '{task.id}': {str(e)}"
        ) from e
    
    # Get expected comment IDs
    expected_ids = [c.id for c in comments]
    
    # Validate and convert results
    logger.debug(f"Validating {len(results)} results against {len(expected_ids)} expected comments")
    task_results: Dict[str, TaskResult] = {}
    skipped_items: List[Dict[str, Any]] = []
    
    for item in results:
        try:
            # Check if comment_id is in expected list
            comment_id = item.get("comment_id")
            if not comment_id:
                logger.warning(f"Skipping result with missing comment_id: {item}")
                continue
            
            if comment_id not in expected_ids:
                # LLM hallucinated or returned ID from wrong batch - skip it
                logger.warning(f"Skipping unexpected comment_id: {comment_id} (not in expected batch)")
                skipped_items.append(item)
                continue
            
            # Validate the rest of the item
            validate_result_item(item, task, expected_ids)
            task_result = convert_to_task_result(item, task)
            task_results[comment_id] = task_result
        except InvalidResponseError as e:
            logger.error(f"Validation failed for item: {str(e)}")
            raise InvalidResponseError(
                f"Validation failed for task '{task.id}': {str(e)}"
            ) from e
    
    if skipped_items:
        logger.info(f"Skipped {len(skipped_items)} unexpected result(s) from LLM response")
    
    # Ensure all comments have results
    missing_ids = set(expected_ids) - set(task_results.keys())
    if missing_ids and skipped_items:
        fixed = []
        for item in skipped_items:
            raw_id = item.get("comment_id")
            if not raw_id:
                continue
            match = _best_fuzzy_match_id(raw_id, list(missing_ids), max_distance=2)
            if not match:
                continue
            matched_id, distance = match
            patched_item = dict(item)
            patched_item["comment_id"] = matched_id
            try:
                validate_result_item(patched_item, task, expected_ids)
            except InvalidResponseError as e:
                logger.warning(
                    f"Skipping auto-correction for comment_id {raw_id}: {str(e)}"
                )
                continue
            task_results[matched_id] = convert_to_task_result(patched_item, task)
            missing_ids.discard(matched_id)
            fixed.append((raw_id, matched_id, distance))
        
        if fixed:
            for raw_id, matched_id, distance in fixed:
                logger.warning(
                    f"Auto-corrected comment_id typo: {raw_id} -> {matched_id} (distance {distance})"
                )
            logger.info(f"Auto-corrected {len(fixed)} comment_id typo(s)")
    
    missing_ids = set(expected_ids) - set(task_results.keys())
    if missing_ids:
        # Check if response was likely truncated
        # If completion_tokens equals max_tokens, the response was cut off
        was_truncated = token_usage.completion_tokens >= max_tokens * 0.95  # 95% threshold
        
        if was_truncated:
            raise InvalidResponseError(
                f"Response was truncated (used {token_usage.completion_tokens}/{max_tokens} tokens). "
                f"Missing results for {len(missing_ids)} comments: {sorted(list(missing_ids))[:5]}{'...' if len(missing_ids) > 5 else ''}\n"
                f"Try reducing batch_size (current: {len(comments)} comments per batch). "
                f"For translation tasks, consider using batch_size=5-10."
            )
        else:
            raise InvalidResponseError(
                f"Missing results for {len(missing_ids)} comments: {sorted(list(missing_ids))[:5]}{'...' if len(missing_ids) > 5 else ''}\n"
                f"The LLM response did not include all requested comments. "
                f"This may indicate an issue with the prompt or model response."
            )
    
    return task_results, token_usage


__all__ = [
    "TaskExecutionError",
    "InvalidResponseError",
    "parse_json_response",
    "validate_result_item",
    "convert_to_task_result",
    "execute_task_base",
]
