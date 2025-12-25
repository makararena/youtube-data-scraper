# AI Feature Implementation - Next Steps

## Current Status

### ✅ COMPLETED

#### Domain Layer (100% Complete)
- ✅ `domain/task.py` - TaskType enum and TaskConfig dataclass
- ✅ `domain/result.py` - TaskResult and EnrichedComment models
- ✅ `domain/comment.py` - Comment domain model
- ✅ `domain/config.py` - RunConfig for runtime configuration

#### Input Layer (100% Complete)
- ✅ `input/comments.py` - Comment loader (CSV, JSONL, Parquet)
- ✅ `input/job.py` - JobSpec loader from questions.yaml
- ✅ `input/questions.py` - QuestionsConfig loader
- ✅ `input/config.py` - InputConfig model
- ✅ `input/validators.py` - Task validation logic

### ❌ NOT IMPLEMENTED (Empty Directories)

#### 1. Task Executors (`tasks/`) - **HIGH PRIORITY**
**Purpose:** Execute each task type using LLM calls

**Files to create:**
- `tasks/__init__.py` - Module exports
- `tasks/base.py` - Base executor interface
- `tasks/binary_classification.py` - Binary classification executor
- `tasks/multi_class.py` - Multi-class classification executor
- `tasks/multi_label.py` - Multi-label classification executor
- `tasks/scoring.py` - Scoring task executor

**Responsibilities:**
- Receive: TaskConfig + List[Comment]
- Return: Dict[comment_id, TaskResult]
- No file I/O, pure execution logic
- Call prompt compiler and model adapter

**Interface:**
```python
def execute_task(
    task: TaskConfig,
    comments: List[Comment],
    prompt_compiler: PromptCompiler,
    model: ModelAdapter,
    run_config: RunConfig
) -> Dict[str, TaskResult]:
    ...
```

---

#### 2. Prompt Layer (`promts/`) - **HIGH PRIORITY** 
**Note:** Directory name has typo (`promts` instead of `prompts`), but keep it for now to avoid breaking changes.

**Purpose:** Generate prompts for each task type and compile them with TaskConfig

**Files to create:**
- `promts/__init__.py` - Module exports
- `promts/compiler.py` - Main prompt compiler
- `promts/templates.py` - Prompt templates per TaskType
- `promts/formatter.py` - JSON output formatting helpers

**Responsibilities:**
- TaskConfig → final prompt string
- Enforce strict JSON output format
- Include custom_prompt context
- Versioned and deterministic prompts

**Key functions:**
```python
def compile_prompt(
    task: TaskConfig,
    comments: List[Comment],
    custom_prompt: Optional[str] = None
) -> str:
    """Generate prompt for batch of comments"""
    
def format_json_schema(task: TaskConfig) -> str:
    """Generate JSON schema description for output"""
```

---

#### 3. Model Layer (`models/`) - **HIGH PRIORITY**

**Purpose:** LLM provider adapters (OpenAI-compatible interface)

**Files to create:**
- `models/__init__.py` - Module exports
- `models/base.py` - Base model adapter interface
- `models/openai.py` - OpenAI API adapter
- `models/errors.py` - Model-specific errors

**Responsibilities:**
- Abstract LLM API calls
- Handle API keys, retries, rate limiting
- Return structured responses
- No domain logic

**Interface:**
```python
class ModelAdapter:
    def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2000
    ) -> str:
        """Call LLM and return raw response"""
```

---

#### 4. Runner Layer (`runner/`) - **HIGH PRIORITY**

**Purpose:** Orchestrate entire analysis pipeline

**Files to create:**
- `runner/__init__.py` - Module exports
- `runner/analysis.py` - Main run_analysis() function
- `runner/batching.py` - Batch management logic
- `runner/retries.py` - Retry logic for failed requests

**Responsibilities:**
- Load job specification
- Load comments
- Batch comments efficiently
- Execute all tasks
- Merge results into EnrichedComment objects
- Handle errors and retries
- Return AnalysisResult

**Main function:**
```python
def run_analysis(
    job: JobSpec,
    run_config: RunConfig
) -> AnalysisResult:
    """
    Main entry point for AI analysis.
    
    Pipeline:
    1. Load comments using job.input
    2. For each task in job.tasks:
       - Batch comments
       - Execute task on batches
       - Collect TaskResults
    3. Merge results into EnrichedComment objects
    4. Return AnalysisResult
    """
```

---

#### 5. Output Layer (`output/`) - **MEDIUM PRIORITY**

**Purpose:** Format results for CSV export

**Files to create:**
- `output/__init__.py` - Module exports
- `output/csv.py` - CSV writer
- `output/formatter.py` - Result flattening logic

**Responsibilities:**
- Convert EnrichedComment → CSV rows
- Flatten TaskResult into columns
- Preserve original comment metadata
- Handle different result types (str, List[str], float)

**Key function:**
```python
def write_csv(
    enriched_comments: List[EnrichedComment],
    output_path: str
) -> None:
    """
    Write enriched comments to CSV.
    
    Columns:
    - Original comment fields (id, text, author, etc.)
    - For each task: {task_id}_value, {task_id}_confidence
    """
```

---

## Implementation Order (Recommended)

Based on the feature plan, implement in this order:

1. **Prompt Layer** (`promts/`) - Needed by tasks
2. **Model Layer** (`models/`) - Needed by tasks
3. **Task Executors** (`tasks/`) - Core execution logic
4. **Runner Layer** (`runner/`) - Orchestration
5. **Output Layer** (`output/`) - Final formatting

---

## Integration Points

### CLI Integration (Future)
After all layers are complete, integrate with CLI:
- Add `ytce ai analyze` command
- Load `questions.yaml` and `ytce.yaml` config
- Call `run_analysis()` from runner
- Write results to CSV

### Testing Strategy
- Unit tests for each layer independently
- Integration tests for full pipeline
- Mock LLM calls for testing (use `dry_run` mode)

---

## Key Design Principles to Follow

1. **Separation of Concerns:** Each layer has single responsibility
2. **Immutability:** Domain objects are frozen dataclasses
3. **User Defines WHAT:** TaskConfig describes intent, not implementation
4. **Batch-First:** Optimize for cost-aware batch processing
5. **CSV-Friendly:** Outputs designed for BI tools

---

## Notes

- Directory name `promts/` has typo but should be kept for consistency
- All domain objects use `frozen=True` (immutable)
- No hardcoded sentiment/topics - everything driven by TaskConfig
- MVP excludes: free-form Q&A, arbitrary JSON extraction, reasoning chains

