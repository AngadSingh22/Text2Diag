#!/usr/bin/env python3
"""
W2.5 Audit B: Shortcut/Leakage Audit (Text Contains Labels?).

Scans text for:
1. Explicit subreddit strings like "r/adhd", "r/depression".
2. URLs and reddit-specific boilerplate.
3. Label names appearing in text.

Flags FAIL if >0.5% of examples contain explicit label strings.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

def load_jsonl(path: Path) -> list:
    """Load JSONL file."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

def main():
    parser = argparse.ArgumentParser(description="W2.5 Shortcut/Leakage Audit")
    parser.add_argument("--data_dir", type=Path, default=Path("data/processed/reddit_mh_windows"))
    parser.add_argument("--out_dir", type=Path, default=Path("results/week2/audits"))
    parser.add_argument("--sample", type=int, default=None, help="Sample size (None = full)")
    args = parser.parse_args()
    
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    # Load labels
    label_path = args.data_dir / "labels.json"
    with open(label_path, "r", encoding="utf-8") as f:
        labels_list = json.load(f)
    print(f"Labels to check: {labels_list}")
    
    # Load all splits
    all_records = []
    for split_name in ["train", "val", "test"]:
        split_path = args.data_dir / f"{split_name}.jsonl"
        if split_path.exists():
            records = load_jsonl(split_path)
            for r in records:
                r["_split"] = split_name
            all_records.extend(records)
    
    print(f"Total records: {len(all_records)}")
    
    # Sample if requested
    if args.sample and args.sample < len(all_records):
        import random
        random.seed(1337)
        all_records = random.sample(all_records, args.sample)
        print(f"Sampled to {len(all_records)} records")
    
    # Patterns to detect
    subreddit_pattern = re.compile(r"r/\w+", re.IGNORECASE)
    url_pattern = re.compile(r"https?://\S+", re.IGNORECASE)
    
    # Per-label patterns
    label_patterns = {}
    for lbl in labels_list:
        # Match label name case-insensitively, as whole word
        label_patterns[lbl] = re.compile(rf"\b{re.escape(lbl)}\b", re.IGNORECASE)
    
    # Scan
    results = {
        "total_scanned": len(all_records),
        "subreddit_mentions": 0,
        "url_mentions": 0,
        "label_in_text": defaultdict(int),
        "examples_with_any_leak": 0,
        "leak_rate_pct": 0.0,
        "passed": True,
        "remediation": []
    }
    
    examples_with_leak = set()
    
    for i, r in enumerate(all_records):
        text = r.get("text", "")
        example_id = r.get("example_id", str(i))
        
        has_leak = False
        
        # Check subreddit mentions
        if subreddit_pattern.search(text):
            results["subreddit_mentions"] += 1
            has_leak = True
        
        # Check URLs
        if url_pattern.search(text):
            results["url_mentions"] += 1
            has_leak = True
        
        # Check label names in text
        for lbl, pat in label_patterns.items():
            if pat.search(text):
                results["label_in_text"][lbl] += 1
                has_leak = True
        
        if has_leak:
            examples_with_leak.add(example_id)
    
    results["examples_with_any_leak"] = len(examples_with_leak)
    results["leak_rate_pct"] = round(100 * len(examples_with_leak) / len(all_records), 2) if all_records else 0
    results["label_in_text"] = dict(results["label_in_text"])
    
    # Threshold: >0.5% = FAIL
    if results["leak_rate_pct"] > 0.5:
        results["passed"] = False
        results["remediation"] = [
            "Strip 'r/<subreddit>' tokens from text",
            "Remove URLs",
            "Consider masking label names in text"
        ]
    
    # Write JSON
    json_path = args.out_dir / "shortcut_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {json_path}")
    
    # Write Markdown
    md_path = args.out_dir / "shortcut_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Shortcut/Leakage Audit Report\n\n")
        f.write(f"**Overall**: {'✅ PASS' if results['passed'] else '❌ FAIL'}\n\n")
        f.write("## Statistics\n\n")
        f.write(f"- Total Scanned: {results['total_scanned']}\n")
        f.write(f"- Subreddit Mentions: {results['subreddit_mentions']}\n")
        f.write(f"- URL Mentions: {results['url_mentions']}\n")
        f.write(f"- Examples with Any Leak: {results['examples_with_any_leak']} ({results['leak_rate_pct']}%)\n\n")
        f.write("## Label Mentions in Text\n\n")
        for lbl, count in sorted(results["label_in_text"].items()):
            pct = round(100 * count / results["total_scanned"], 2) if results["total_scanned"] else 0
            f.write(f"- `{lbl}`: {count} ({pct}%)\n")
        if results["remediation"]:
            f.write("\n## Remediation Suggestions\n\n")
            for r in results["remediation"]:
                f.write(f"- {r}\n")
    print(f"Wrote {md_path}")
    
    print(f"\nLeak Rate: {results['leak_rate_pct']}% -> {'PASS' if results['passed'] else 'FAIL'}")
    return 0 if results["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
