# Question Examples

This folder contains example `questions.yaml` files demonstrating different use cases for AI comment analysis.

## Examples

### Basic Sentiment (`basic-sentiment.yaml`)
Simple sentiment analysis using multi-class classification. Perfect for getting started.

**Use cases:**
- Quick sentiment overview
- Simple positive/neutral/negative classification
- Learning the basics

### Translation (`translation-multilanguage.yaml`)
Translate comments to multiple languages. Useful for:
- Analyzing international audience feedback
- Preparing data for multilingual teams
- Cross-language content analysis

**Features:**
- Multiple translation tasks (Russian, Spanish, French)
- Preserves technical terms and product names
- Maintains original tone and meaning

### Language Detection (`language-detection.yaml`)
Detect the primary language of each comment using ISO 639 language codes. Useful for:
- Understanding geographic distribution of viewers
- Planning localization efforts
- Filtering comments by language
- Analyzing international audience composition

**Features:**
- Returns ISO 639-1 or ISO 639-2 language codes (e.g., "en", "ru", "es")
- Includes confidence scores for language detection
- Handles mixed-language content gracefully

### Product Feedback (`product-feedback.yaml`)
Comprehensive product feedback analysis combining:
- Translation to Russian
- Sentiment analysis
- Feature request detection
- Topic classification
- Importance scoring

**Use cases:**
- Product launch feedback analysis
- Feature request prioritization
- User pain point identification
- International market insights

### Content Moderation (`content-moderation.yaml`)
Identify problematic content:
- Spam detection
- Toxicity scoring
- Inappropriate content detection
- Off-topic filtering

**Use cases:**
- Automated moderation
- Community health monitoring
- Quality filtering

### Comprehensive Analysis (`comprehensive-analysis.yaml`)
Full-featured analysis combining multiple task types:
- Translation
- Sentiment (5-level)
- Question detection
- Multi-topic classification
- Engagement quality scoring
- User type classification

**Use cases:**
- Deep audience insights
- Content strategy planning
- Community understanding
- Product development research

## How to Use

1. Copy an example file to your project root:
   ```bash
   cp examples/questions/basic-sentiment.yaml questions.yaml
   ```

2. Update the `input.path` to point to your comments file:
   ```yaml
   input:
     path: "./data/YOUR_VIDEO_ID/comments.jsonl"
   ```

3. Customize tasks and questions for your needs

4. Run the analysis:
   ```bash
   ytce analyze questions.yaml --max-comments 100
   ```

## Task Types Reference

### Language Detection (`language_detection`)
Detect the primary language of each comment.

**Required fields:**
- None (language detection doesn't require additional configuration)

**Example:**
```yaml
- id: language
  type: language_detection
  question: "What is the primary language of this comment?"
```

**Output:** ISO 639-1 or ISO 639-2 language code string in `{task_id}_value` column (e.g., "en", "ru", "es", "fr")

**Common ISO codes:**
- `en` = English
- `ru` = Russian
- `es` = Spanish
- `fr` = French
- `de` = German
- `zh` = Chinese
- `ja` = Japanese
- `ko` = Korean
- `und` = Undetermined (for unclear/mixed content)

### Translation (`translation`)
Translate comments to a target language.

**Required fields:**
- `target_language`: Target language name (e.g., "Russian", "Spanish", "French")

**Example:**
```yaml
- id: translation_ru
  type: translation
  question: "Translate this comment to Russian..."
  target_language: "Russian"
```

**Output:** Translated text string in `{task_id}_value` column

### Binary Classification (`binary_classification`)
Classify into one of two categories.

**Required fields:**
- `labels`: Exactly 2 labels

**Example:**
```yaml
- id: spam
  type: binary_classification
  question: "Is this spam?"
  labels: ["yes", "no"]
```

### Multi-Class Classification (`multi_class`)
Classify into exactly one category from multiple options.

**Required fields:**
- `labels`: List of 3+ labels

**Example:**
```yaml
- id: sentiment
  type: multi_class
  question: "What is the sentiment?"
  labels: ["positive", "neutral", "negative"]
```

### Multi-Label Classification (`multi_label`)
Assign multiple labels to each comment.

**Required fields:**
- `labels`: List of labels
- `max_labels`: Maximum number of labels (optional)

**Example:**
```yaml
- id: topics
  type: multi_label
  question: "What topics are mentioned?"
  labels: ["topic1", "topic2", "topic3"]
  max_labels: 2
```

### Scoring (`scoring`)
Assign a numeric score within a range.

**Required fields:**
- `scale`: [min, max] numeric range

**Example:**
```yaml
- id: toxicity
  type: scoring
  question: "How toxic is this comment?"
  scale: [0.0, 1.0]
```

## Tips

- **Start simple**: Begin with `basic-sentiment.yaml` to understand the workflow
- **Use translation**: Add translation tasks to analyze international audiences
- **Combine tasks**: Mix different task types for comprehensive insights
- **Custom prompts**: Add context in `custom_prompt` to improve accuracy
- **Batch size**: Adjust `--batch-size` (default: 20) based on comment length
- **Dry run**: Test with `--dry-run` first to preview without API costs

## Output Structure

Results are automatically saved to:
```
data/results/{VIDEO_ID}/results.csv
```

Each task creates two columns:
- `{task_id}_value`: The result value
- `{task_id}_confidence`: Confidence score (0.0-1.0)

