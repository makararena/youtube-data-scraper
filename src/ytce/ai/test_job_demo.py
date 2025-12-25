#!/usr/bin/env python3
"""
Demonstration script for testing the job loader.

Shows how to load a job specification from questions.yaml and use it.
"""

from ytce.ai.input.job import load_job
from ytce.ai.input.comments import load_comments


def main():
    """Demonstrate loading and using a job specification."""
    print("=" * 60)
    print("Job Loader Demonstration")
    print("=" * 60)
    print()
    
    # Load job specification
    print("Loading job from questions.yaml...")
    try:
        job = load_job("questions.yaml")
    except FileNotFoundError:
        print("⚠ questions.yaml not found in current directory")
        print("  Run 'ytce init' to create it")
        return
    
    print(f"✓ Loaded job specification")
    print()
    
    # Display input configuration
    print("Input Configuration:")
    print(f"  Path: {job.input.path}")
    print(f"  Format: {job.input.format}")
    print(f"  ID Field: {job.input.id_field}")
    print(f"  Text Field: {job.input.text_field}")
    print()
    
    # Display tasks
    print(f"Tasks ({len(job.tasks)}):")
    for i, task in enumerate(job.tasks, 1):
        print(f"  {i}. {task.id} ({task.type.value})")
        print(f"     Question: {task.question}")
        if task.labels:
            print(f"     Labels: {task.labels}")
        if task.max_labels:
            print(f"     Max labels: {task.max_labels}")
        if task.scale:
            print(f"     Scale: {task.scale}")
    print()
    
    # Display custom prompt
    if job.custom_prompt:
        print(f"Custom Prompt: {job.custom_prompt[:100]}...")
    else:
        print("Custom Prompt: (none)")
    print()
    
    # Demonstrate how runner would use this
    print("=" * 60)
    print("Usage Example (for runner):")
    print("=" * 60)
    print()
    print("# Load job specification")
    print("job = load_job('questions.yaml')")
    print()
    print("# Load comments using job.input configuration")
    print("# comments = load_comments(job.input.path)")
    print()
    print("# Run analysis")
    print("# results = run_analysis(")
    print("#     comments=comments,")
    print("#     job=job,")
    print("#     run_config=run_config,")
    print("# )")
    print()
    
    # Try to load comments if path exists
    import os
    if os.path.exists(job.input.path):
        print(f"✓ Found comment file: {job.input.path}")
        try:
            comments = load_comments(job.input.path)
            print(f"✓ Loaded {len(comments)} comments")
        except Exception as e:
            print(f"⚠ Error loading comments: {e}")
    else:
        print(f"⚠ Comment file not found: {job.input.path}")


if __name__ == "__main__":
    main()

