# Contributing to YouTube Data Scraper

Thank you for considering contributing to ytce! This document provides guidelines and instructions for contributing.

## Quick Start

1. **Fork and Clone**
   ```bash
   git fork https://github.com/makararena/youtube-data-scraper
   cd youtube-data-scraper
   ```

2. **Setup Development Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Run Tests**
   ```bash
   pytest tests/
   ```

4. **Make Your Changes**
   - Create a feature branch: `git checkout -b feature/my-feature`
   - Write code
   - Add tests if applicable
   - Run tests to ensure nothing broke

5. **Submit Pull Request**
   - Push to your fork
   - Open PR with clear description
   - Link any related issues

## Development Workflow

### Running Without Installation

For quick development iterations:

```bash
export PYTHONPATH=src
python -m ytce --help
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_paths.py

# Run with coverage
pytest --cov=ytce tests/
```

### Checking Your Changes

Before submitting:

```bash
# 1. Run tests
pytest tests/

# 2. Test CLI commands
ytce init
ytce channel @test --limit 1 --dry-run
ytce analyze questions.yaml --dry-run
ytce --version

# 3. Check help messages
ytce --help
ytce channel --help
ytce analyze --help
```

## Code Style

- **Type Hints**: Use type hints for all function signatures
- **Docstrings**: Add docstrings for public functions/classes
- **Format**: Follow PEP 8
- **Imports**: Use `from __future__ import annotations`

Example:

```python
from __future__ import annotations

from typing import Optional


def process_data(input_path: str, limit: Optional[int] = None) -> int:
    """
    Process data from input file.
    
    Args:
        input_path: Path to input file
        limit: Optional limit on number of items
    
    Returns:
        Number of items processed
    """
    # Implementation
    return 0
```

## Project Structure

```
youtube-data-scraper/
├── src/ytce/
│   ├── cli/              # Command-line interface
│   ├── pipelines/        # High-level workflows
│   ├── youtube/          # YouTube scraping core
│   ├── storage/          # File I/O
│   ├── models/           # Data structures
│   ├── ai/               # AI analysis engine
│   │   ├── domain/       # Domain models
│   │   ├── input/        # Input parsers
│   │   ├── models/       # LLM adapters
│   │   ├── promts/       # Prompt compilation
│   │   ├── runner/       # Orchestration
│   │   ├── tasks/        # Task executors
│   │   └── output/       # CSV export
│   ├── utils/            # Utilities
│   ├── config.py         # Configuration management
│   └── errors.py         # Error handling
├── examples/             # Example question files
│   └── questions/        # AI analysis templates
├── tests/                # Test suite
├── docs/                 # Documentation
└── README.md             # User documentation
```

## Adding Features

### Adding a New Command

1. Update `src/ytce/cli/main.py`:
   ```python
   p_newcmd = sub.add_parser("newcmd", help="Description")
   p_newcmd.add_argument("arg1", help="First argument")
   ```

2. Add handler in `main()`:
   ```python
   if args.cmd == "newcmd":
       run_newcmd(arg1=args.arg1)
       return EXIT_SUCCESS
   ```

3. Create pipeline in `src/ytce/pipelines/newcmd.py`:
   ```python
   def run(*, arg1: str) -> None:
       # Implementation
       pass
   ```

4. Add tests in `tests/test_newcmd.py`

### Adding YouTube Scrapers

Add new scrapers to `src/ytce/youtube/`:

1. Use existing utilities:
   - `session.py` for HTTP sessions
   - `html.py` for fetching pages
   - `extractors.py` for parsing YouTube data
   - `innertube.py` for API requests

2. Follow existing patterns (see `comments.py` or `channel_videos.py`)

3. Add tests for parsing logic

### Adding AI Analysis Features

The AI analysis engine (`src/ytce/ai/`) is modular and extensible:

**Adding a new task type:**

1. Add task type to `domain/task.py` (`TaskType` enum)
2. Create executor in `tasks/` (e.g., `tasks/new_task.py`)
3. Add prompt template in `promts/templates.py`
4. Update validators in `input/validators.py`
5. Add example to `examples/questions/`

**Adding a new model adapter:**

1. Implement `ModelAdapter` interface from `models/base.py`
2. Add to `models/__init__.py`
3. Update `runner/analysis.py` to support new adapter

**Adding input format support:**

1. Extend `input/comments.py` to support new format
2. Update `InputConfig` in `input/config.py` if needed
3. Add tests for new format

See `src/ytce/ai/README.md` and `src/ytce/ai/ARCHITECTURE.md` for detailed architecture documentation.

## Testing Guidelines

### What to Test

- ✅ Argument parsing
- ✅ Path generation
- ✅ Error handling
- ✅ Data format output
- ✅ AI analysis pipeline (use `--dry-run` mode)
- ❌ Actual YouTube scraping (too fragile)
- ❌ Real LLM API calls (use mocks or `--dry-run`)

### Test Structure

```python
def test_feature():
    # Arrange
    input_data = "test"
    
    # Act
    result = process(input_data)
    
    # Assert
    assert result == expected
```

### Mocking YouTube Responses

```python
from unittest.mock import Mock, patch

@patch("ytce.youtube.html.fetch_html")
def test_scraper(mock_fetch):
    mock_fetch.return_value = "<html>...</html>"
    # Test your scraper
```

## Reporting Issues

When reporting issues, please include:

1. **YouTube URL** - Channel or video link
2. **Command Used** - Exact command you ran
3. **Expected Behavior** - What should happen
4. **Actual Behavior** - What actually happened
5. **Debug Log** - Output with `--debug` flag

Example:

```
**URL**: https://www.youtube.com/@channelname

**Command**:
ytce channel @channelname --limit 5

**Expected**: Download 5 videos + comments

**Actual**: Failed with KeyError

**Debug Log**:
```
(paste output with --debug)
```
```

## Pull Request Guidelines

### Before Submitting

- [ ] Tests pass (`pytest tests/`)
- [ ] Code follows style guidelines
- [ ] Docstrings added for new functions
- [ ] CHANGELOG.md updated (if applicable)
- [ ] No breaking changes (or clearly documented)

### PR Description Template

```markdown
## What Changed

Brief description of changes.

## Why

Explanation of motivation/problem solved.

## How to Test

1. Step 1
2. Step 2
3. Expected result

## Related Issues

Closes #123
```

### Review Process

1. Automated checks must pass
2. At least one maintainer review
3. No unresolved comments
4. Clean commit history (squash if needed)

## Common Tasks

### Adding a New Flag

1. Add to argument parser:
   ```python
   parser.add_argument("--new-flag", help="Description")
   ```

2. Use in pipeline:
   ```python
   run_pipeline(new_flag=args.new_flag)
   ```

3. Update help documentation
4. Add example to README

### Fixing YouTube Parser

If YouTube changes their page structure:

1. Enable debug mode: `--debug`
2. Check `/tmp/youtube_debug.html`
3. Find new selector/pattern
4. Update `src/ytce/youtube/extractors.py`
5. Test with real data
6. Submit PR with explanation

### Updating Dependencies

1. Update `requirements.txt`
2. Update `pyproject.toml`
3. Test that everything still works
4. Document any breaking changes

## Version Numbers

We use Semantic Versioning (semver):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Version is stored in `src/ytce/__version__.py`.

## Documentation

### Updating README

- Keep user-focused
- TL;DR section first
- Examples before technical details

### Adding to docs/

- Quick references
- Migration guides
- Detailed tutorials

## Questions?

- Open an issue for questions
- Tag with `question` label
- Be specific and provide context

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Assume good intentions

## Thank You!

Every contribution helps make ytce better. Whether it's:
- Reporting bugs
- Suggesting features
- Fixing typos
- Writing code
- Improving documentation

...your help is appreciated! 🙏

