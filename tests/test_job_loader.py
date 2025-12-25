"""Tests for job loader (JobSpec and load_job)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from ytce.ai.domain.task import TaskType
from ytce.ai.input.config import InputConfig
from ytce.ai.input.job import JobSpec, load_job


def test_load_job_from_questions_yaml():
    """Test loading job from existing questions.yaml."""
    questions_path = Path(__file__).parent.parent / "questions.yaml"
    
    if not questions_path.exists():
        pytest.skip(f"questions.yaml not found: {questions_path}")
    
    job = load_job(str(questions_path))
    
    assert isinstance(job, JobSpec)
    assert isinstance(job.input, InputConfig)
    assert len(job.tasks) > 0
    assert all(task.id for task in job.tasks)
    assert all(task.question for task in job.tasks)
    
    # Check input config
    assert job.input.path == "./comments.csv"
    assert job.input.format == "csv"
    assert job.input.id_field == "id"
    assert job.input.text_field == "text"
    
    # Check tasks
    assert len(job.tasks) == 4
    
    # Verify task types
    task_types = {task.type for task in job.tasks}
    assert TaskType.MULTI_CLASS in task_types
    assert TaskType.BINARY_CLASSIFICATION in task_types
    assert TaskType.MULTI_LABEL in task_types
    assert TaskType.SCORING in task_types


def test_load_job_minimal():
    """Test loading minimal valid job spec."""
    job_yaml = """
input:
  path: "./test.csv"
  format: csv
  id_field: cid
  text_field: text
tasks:
  - id: test_task
    type: binary_classification
    question: "Is this test?"
    labels: ["yes", "no"]
"""
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(job_yaml)
        temp_path = f.name
    
    try:
        job = load_job(temp_path)
        
        assert job.input.path == "./test.csv"
        assert job.input.format == "csv"
        assert job.input.id_field == "cid"
        assert job.input.text_field == "text"
        
        assert len(job.tasks) == 1
        assert job.tasks[0].id == "test_task"
        assert job.tasks[0].type == TaskType.BINARY_CLASSIFICATION
        assert job.tasks[0].question == "Is this test?"
        assert job.tasks[0].labels == ["yes", "no"]
        
        assert job.custom_prompt is None
    finally:
        Path(temp_path).unlink()


def test_load_job_with_custom_prompt():
    """Test loading job with custom_prompt."""
    job_yaml = """
input:
  path: "./test.csv"
  format: csv
  id_field: id
  text_field: text
custom_prompt: "This is a test channel about technology"
tasks:
  - id: sentiment
    type: multi_class
    question: "What is the sentiment?"
    labels: ["positive", "neutral", "negative"]
"""
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(job_yaml)
        temp_path = f.name
    
    try:
        job = load_job(temp_path)
        
        assert job.custom_prompt == "This is a test channel about technology"
    finally:
        Path(temp_path).unlink()


def test_load_job_empty_custom_prompt():
    """Test that empty custom_prompt is normalized to None."""
    job_yaml = """
input:
  path: "./test.csv"
  format: csv
  id_field: id
  text_field: text
custom_prompt: ""
tasks:
  - id: test
    type: binary_classification
    question: "Test?"
    labels: ["yes", "no"]
"""
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(job_yaml)
        temp_path = f.name
    
    try:
        job = load_job(temp_path)
        assert job.custom_prompt is None
    finally:
        Path(temp_path).unlink()


def test_load_job_missing_input():
    """Test error when input section is missing."""
    job_yaml = """
tasks:
  - id: test
    type: binary_classification
    question: "Test?"
    labels: ["yes", "no"]
"""
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(job_yaml)
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="missing 'input' section"):
            load_job(temp_path)
    finally:
        Path(temp_path).unlink()


def test_load_job_missing_tasks():
    """Test error when tasks section is missing."""
    job_yaml = """
input:
  path: "./test.csv"
  format: csv
  id_field: id
  text_field: text
"""
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(job_yaml)
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="missing 'tasks' section"):
            load_job(temp_path)
    finally:
        Path(temp_path).unlink()


def test_load_job_empty_tasks():
    """Test error when tasks list is empty."""
    job_yaml = """
input:
  path: "./test.csv"
  format: csv
  id_field: id
  text_field: text
tasks: []
"""
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(job_yaml)
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="must be a non-empty list"):
            load_job(temp_path)
    finally:
        Path(temp_path).unlink()


def test_load_job_missing_input_field():
    """Test error when required input field is missing."""
    job_yaml = """
input:
  path: "./test.csv"
  format: csv
  id_field: id
  # text_field missing
tasks:
  - id: test
    type: binary_classification
    question: "Test?"
    labels: ["yes", "no"]
"""
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(job_yaml)
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="missing 'text_field'"):
            load_job(temp_path)
    finally:
        Path(temp_path).unlink()


def test_load_job_file_not_found():
    """Test error when file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        load_job("nonexistent_file.yaml")


def test_load_job_invalid_yaml():
    """Test error when YAML is invalid."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("invalid: yaml: content: [")
        temp_path = f.name
    
    try:
        with pytest.raises(yaml.YAMLError):
            load_job(temp_path)
    finally:
        Path(temp_path).unlink()


def test_load_job_not_a_dict():
    """Test error when YAML root is not a dict."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("- item1\n- item2")
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="expected YAML mapping"):
            load_job(temp_path)
    finally:
        Path(temp_path).unlink()


def test_job_spec_immutable():
    """Test that JobSpec is immutable."""
    input_cfg = InputConfig(
        path="./test.csv",
        format="csv",
        id_field="id",
        text_field="text",
    )
    
    from ytce.ai.domain.task import TaskConfig, TaskType
    
    task = TaskConfig(
        id="test",
        type=TaskType.BINARY_CLASSIFICATION,
        question="Test?",
        labels=["yes", "no"],
    )
    
    job = JobSpec(
        input=input_cfg,
        tasks=[task],
        custom_prompt="test",
    )
    
    # Verify immutability
    with pytest.raises(Exception):  # dataclass frozen raises FrozenInstanceError
        job.custom_prompt = "changed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

