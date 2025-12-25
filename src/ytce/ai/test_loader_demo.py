#!/usr/bin/env python3
"""
Demonstration script for testing the AI comment loader with different formats.

This script loads comments from JSONL, CSV, and Parquet formats and displays
summary statistics to verify the loader works correctly.
"""

from pathlib import Path

from ytce.ai.input.comments import load_comments


def main():
    """Test loading comments from all supported formats."""
    # Path to test data files
    data_dir = Path(__file__).parent.parent.parent.parent / "data"
    
    formats = [
        ("JSONL", data_dir / "test_comments.jsonl"),
        ("CSV", data_dir / "test_comments.csv"),
        ("Parquet", data_dir / "test_comments.parquet"),
    ]
    
    print("=" * 60)
    print("AI Comment Loader Test - All Formats")
    print("=" * 60)
    print()
    
    results = {}
    
    for format_name, file_path in formats:
        if not file_path.exists():
            print(f"⚠ {format_name}: File not found: {file_path}")
            continue
        
        try:
            print(f"Loading {format_name} from: {file_path.name}")
            comments = load_comments(str(file_path))
            
            # Calculate statistics
            total = len(comments)
            with_author = sum(1 for c in comments if c.author)
            with_votes = sum(1 for c in comments if c.votes is not None)
            with_channel = sum(1 for c in comments if c.channel)
            
            avg_text_length = sum(len(c.text) for c in comments) / total if total > 0 else 0
            
            results[format_name] = {
                "count": total,
                "with_author": with_author,
                "with_votes": with_votes,
                "with_channel": with_channel,
                "avg_text_length": avg_text_length,
            }
            
            print(f"  ✓ Loaded {total} comments")
            print(f"  ✓ Comments with author: {with_author} ({with_author/total*100:.1f}%)")
            print(f"  ✓ Comments with votes: {with_votes} ({with_votes/total*100:.1f}%)")
            print(f"  ✓ Comments with channel: {with_channel} ({with_channel/total*100:.1f}%)")
            print(f"  ✓ Average text length: {avg_text_length:.1f} characters")
            
            # Show first comment as example
            if comments:
                first = comments[0]
                print(f"  ✓ First comment:")
                print(f"    ID: {first.id[:30]}...")
                print(f"    Text: {first.text[:60]}...")
                if first.author:
                    print(f"    Author: {first.author}")
                if first.votes is not None:
                    print(f"    Votes: {first.votes}")
            
            print()
            
        except ImportError as e:
            print(f"  ✗ {format_name}: Import error - {e}")
            print(f"    Install required packages: pip install pandas pyarrow")
            print()
        except Exception as e:
            print(f"  ✗ {format_name}: Error - {e}")
            print()
    
    # Compare results across formats
    if len(results) > 1:
        print("=" * 60)
        print("Format Comparison")
        print("=" * 60)
        
        counts = [r["count"] for r in results.values()]
        if len(set(counts)) == 1:
            print(f"✓ All formats loaded the same number of comments: {counts[0]}")
        else:
            print("⚠ Warning: Different formats loaded different numbers of comments:")
            for format_name, stats in results.items():
                print(f"  {format_name}: {stats['count']} comments")
        
        print()
        print("Summary:")
        for format_name, stats in results.items():
            print(f"  {format_name:10} | Count: {stats['count']:4} | "
                  f"Avg length: {stats['avg_text_length']:6.1f}")


if __name__ == "__main__":
    main()

