"""
Input configuration for loading comments.

Defines the structure for specifying where and how to load comment data.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class InputConfig:
    """
    Configuration for loading comments from a file.
    
    Specifies:
    - path: File path to load comments from
    - format: File format (csv, jsonl, parquet)
    - id_field: Field name containing comment ID
    - text_field: Field name containing comment text
    """
    
    path: str
    format: str
    id_field: str
    text_field: str


__all__ = ["InputConfig"]

