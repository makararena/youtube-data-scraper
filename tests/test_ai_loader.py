"""Tests for AI comment loader with different file formats."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from ytce.ai.input.comments import load_comments


# Path to test data files
TEST_DATA_DIR = Path(__file__).parent.parent / "data"
JSONL_FILE = TEST_DATA_DIR / "test_comments.jsonl"
CSV_FILE = TEST_DATA_DIR / "test_comments.csv"
PARQUET_FILE = TEST_DATA_DIR / "test_comments.parquet"


def test_load_comments_jsonl():
    """Test loading comments from JSONL format."""
    if not JSONL_FILE.exists():
        pytest.skip(f"Test data file not found: {JSONL_FILE}")
    
    comments = load_comments(str(JSONL_FILE))
    
    assert len(comments) > 0, "Should load at least one comment"
    
    # Verify comment structure
    for comment in comments:
        assert comment.id is not None and comment.id.strip() != "", "Comment ID should not be empty"
        assert comment.text is not None and comment.text.strip() != "", "Comment text should not be empty"
        assert isinstance(comment.id, str), "Comment ID should be a string"
        assert isinstance(comment.text, str), "Comment text should be a string"
    
    # Check first comment has expected fields
    first_comment = comments[0]
    assert first_comment.id is not None
    assert first_comment.text is not None
    # Optional fields may or may not be present
    print(f"✓ Loaded {len(comments)} comments from JSONL")
    print(f"  First comment ID: {first_comment.id[:20]}...")
    print(f"  First comment text: {first_comment.text[:50]}...")


def test_load_comments_csv():
    """Test loading comments from CSV format."""
    if not CSV_FILE.exists():
        pytest.skip(f"Test data file not found: {CSV_FILE}")
    
    comments = load_comments(str(CSV_FILE))
    
    assert len(comments) > 0, "Should load at least one comment"
    
    # Verify comment structure
    for comment in comments:
        assert comment.id is not None and comment.id.strip() != "", "Comment ID should not be empty"
        assert comment.text is not None and comment.text.strip() != "", "Comment text should not be empty"
        assert isinstance(comment.id, str), "Comment ID should be a string"
        assert isinstance(comment.text, str), "Comment text should be a string"
    
    # Check first comment has expected fields
    first_comment = comments[0]
    assert first_comment.id is not None
    assert first_comment.text is not None
    
    print(f"✓ Loaded {len(comments)} comments from CSV")
    print(f"  First comment ID: {first_comment.id[:20]}...")
    print(f"  First comment text: {first_comment.text[:50]}...")


def test_load_comments_parquet():
    """Test loading comments from Parquet format."""
    if not PARQUET_FILE.exists():
        pytest.skip(f"Test data file not found: {PARQUET_FILE}")
    
    try:
        comments = load_comments(str(PARQUET_FILE))
    except ImportError as e:
        pytest.skip(f"Parquet support not available: {e}")
    
    assert len(comments) > 0, "Should load at least one comment"
    
    # Verify comment structure
    for comment in comments:
        assert comment.id is not None and comment.id.strip() != "", "Comment ID should not be empty"
        assert comment.text is not None and comment.text.strip() != "", "Comment text should not be empty"
        assert isinstance(comment.id, str), "Comment ID should be a string"
        assert isinstance(comment.text, str), "Comment text should be a string"
    
    # Check first comment has expected fields
    first_comment = comments[0]
    assert first_comment.id is not None
    assert first_comment.text is not None
    
    print(f"✓ Loaded {len(comments)} comments from Parquet")
    print(f"  First comment ID: {first_comment.id[:20]}...")
    print(f"  First comment text: {first_comment.text[:50]}...")


def test_all_formats_load_same_comments():
    """Test that all formats load the same number of comments."""
    files = [
        (JSONL_FILE, "JSONL"),
        (CSV_FILE, "CSV"),
        (PARQUET_FILE, "Parquet"),
    ]
    
    comment_counts = {}
    comments_by_format = {}
    
    for file_path, format_name in files:
        if not file_path.exists():
            pytest.skip(f"Test data file not found: {file_path}")
        
        try:
            comments = load_comments(str(file_path))
            comment_counts[format_name] = len(comments)
            comments_by_format[format_name] = comments
        except ImportError as e:
            if format_name == "Parquet":
                pytest.skip(f"Parquet support not available: {e}")
            raise
    
    # All formats should load the same number of comments
    counts = list(comment_counts.values())
    assert len(set(counts)) == 1, f"All formats should load same count, got: {comment_counts}"
    
    # Verify that comment IDs match across formats
    jsonl_ids = {c.id for c in comments_by_format["JSONL"]}
    csv_ids = {c.id for c in comments_by_format["CSV"]}
    
    assert jsonl_ids == csv_ids, "JSONL and CSV should have same comment IDs"
    
    if "Parquet" in comments_by_format:
        parquet_ids = {c.id for c in comments_by_format["Parquet"]}
        assert jsonl_ids == parquet_ids, "JSONL and Parquet should have same comment IDs"
    
    print(f"✓ All formats loaded {counts[0]} comments")
    print(f"  Comment counts: {comment_counts}")


def test_comment_metadata_preserved():
    """Test that optional metadata fields are preserved."""
    if not JSONL_FILE.exists():
        pytest.skip(f"Test data file not found: {JSONL_FILE}")
    
    comments = load_comments(str(JSONL_FILE))
    
    # Check that at least some comments have metadata
    comments_with_author = [c for c in comments if c.author is not None]
    comments_with_votes = [c for c in comments if c.votes is not None]
    
    print(f"✓ Comments with author: {len(comments_with_author)}/{len(comments)}")
    print(f"✓ Comments with votes: {len(comments_with_votes)}/{len(comments)}")
    
    # Verify raw data is preserved
    comments_with_raw = [c for c in comments if c.raw is not None]
    assert len(comments_with_raw) == len(comments), "All comments should have raw data preserved"
    
    # Check that raw data contains expected fields
    if comments:
        first_raw = comments[0].raw
        assert "cid" in first_raw or "id" in first_raw, "Raw data should contain comment ID"
        assert "text" in first_raw, "Raw data should contain text"


def test_load_comments_file_not_found():
    """Test that FileNotFoundError is raised for non-existent files."""
    with pytest.raises(FileNotFoundError):
        load_comments("nonexistent_file.jsonl")


def test_load_comments_unsupported_format():
    """Test that ValueError is raised for unsupported formats."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        temp_path = f.name
        f.write(b"test content")
    
    try:
        with pytest.raises(ValueError, match="Unsupported file format"):
            load_comments(temp_path)
    finally:
        os.unlink(temp_path)


if __name__ == "__main__":
    # Allow running tests directly
    import tempfile
    pytest.main([__file__, "-v", "-s"])

