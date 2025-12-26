# Tests

This directory contains the test suite for ytce.

## Running Tests

```bash
# Install pytest if not already installed
pip install pytest

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_paths.py

# Run with verbose output
pytest -v tests/

# Run with coverage
pip install pytest-cov
pytest --cov=ytce tests/
```

## Test Structure

- `test_paths.py` - Storage path generation
- `test_config.py` - Configuration management
- `test_cli.py` - CLI argument parsing (includes AI analyze command)
- `test_errors.py` - Error handling
- `test_version.py` - Version information
- `test_job_loader.py` - AI job specification loading
- `test_ai_loader.py` - AI input/comment loading

## Writing Tests

Follow the existing patterns:

```python
def test_feature_name():
    """Test description."""
    # Arrange
    input_data = "test"
    
    # Act
    result = process(input_data)
    
    # Assert
    assert result == expected
```

## What We Test

- ✅ Path generation
- ✅ Argument parsing
- ✅ Configuration loading
- ✅ Error handling
- ✅ Exit codes
- ✅ AI job specification loading
- ✅ AI comment input loading
- ✅ AI analysis CLI command (with `--dry-run`)

## What We Don't Test

- ❌ Actual YouTube scraping (too fragile, requires network)
- ❌ HTML parsing (YouTube structure changes frequently)
- ❌ Real file I/O in pipelines (tested via integration tests)
- ❌ Real LLM API calls (use `--dry-run` mode or mocks)

## Mocking

Use mocks for external dependencies:

```python
from unittest.mock import Mock, patch

@patch("ytce.youtube.html.fetch_html")
def test_scraper(mock_fetch):
    mock_fetch.return_value = "<html>...</html>"
    # Your test here

# For AI analysis tests, use --dry-run mode or mock ModelAdapter
from ytce.ai.models.base import ModelAdapter

class MockModelAdapter(ModelAdapter):
    def generate(self, prompt: str, **kwargs) -> str:
        return '{"results": []}'
```

## CI Integration

These tests run automatically on:
- Pull requests
- Commits to main
- Release tags

All tests must pass before merging.

