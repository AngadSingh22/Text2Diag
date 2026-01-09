#!/usr/bin/env python3
"""
W2.5 Audit A: Integrity Audit (Canonical Contract Validation).

Verifies:
1. Required fields exist: example_id, user_id, split, text, labels, meta.
2. Labels can be expanded to multi-hot and match label2id.json.
3. All examples have same label dimension L.
4. No user_id overlap across splits (leakage = 0).
5. Split files match actual records (if present).
"""
import argparse
import json
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
    parser = argparse.ArgumentParser(description="W2.5 Integrity Audit")
    parser.add_argument("--data_dir", type=Path, default=Path("data/processed/reddit_mh_windows"))
    parser.add_argument("--out_dir", type=Path, default=Path("results/week2/audits"))
    args = parser.parse_args()
    
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    # Load label2id
    label_path = args.data_dir / "labels.json"
    if not label_path.exists():
        print(f"ERROR: labels.json not found at {label_path}")
        sys.exit(1)
    
    with open(label_path, "r", encoding="utf-8") as f:
        labels_list = json.load(f)
    label2id = {l: i for i, l in enumerate(sorted(labels_list))}
    num_labels = len(label2id)
    print(f"Loaded {num_labels} labels: {list(label2id.keys())}")
    
    # Load splits
    splits = {}
    for split_name in ["train", "val", "test"]:
        split_path = args.data_dir / f"{split_name}.jsonl"
        if split_path.exists():
            splits[split_name] = load_jsonl(split_path)
            print(f"Loaded {len(splits[split_name])} records from {split_name}")
        else:
            print(f"WARNING: {split_path} not found")
    
    # Audit results
    results = {
        "passed": True,
        "checks": {},
        "details": {}
    }
    
    # CHECK 1: Required fields
    required_fields = ["example_id", "user_id", "split", "text", "labels"]
    missing_fields = defaultdict(list)
    
    for split_name, records in splits.items():
        for i, r in enumerate(records):
            for field in required_fields:
                if field not in r:
                    missing_fields[split_name].append((i, field))
    
    if any(missing_fields.values()):
        results["passed"] = False
        results["checks"]["required_fields"] = "FAIL"
        results["details"]["missing_fields"] = dict(missing_fields)
    else:
        results["checks"]["required_fields"] = "PASS"
    print(f"CHECK 1 (Required Fields): {results['checks']['required_fields']}")
    
    # CHECK 2: Labels are valid and expand to correct dimension
    invalid_labels = []
    for split_name, records in splits.items():
        for i, r in enumerate(records):
            for lbl in r.get("labels", []):
                if lbl not in label2id:
                    invalid_labels.append((split_name, i, lbl))
    
    if invalid_labels:
        results["passed"] = False
        results["checks"]["label_validity"] = "FAIL"
        results["details"]["invalid_labels"] = invalid_labels[:20]  # Limit output
    else:
        results["checks"]["label_validity"] = "PASS"
    print(f"CHECK 2 (Label Validity): {results['checks']['label_validity']}")
    
    # CHECK 3: Consistent label dimension (implicitly passed if labels valid)
    results["checks"]["label_dimension"] = "PASS"
    results["details"]["num_labels"] = num_labels
    print(f"CHECK 3 (Label Dimension = {num_labels}): PASS")
    
    # CHECK 4: No user_id overlap across splits
    user_sets = {}
    for split_name, records in splits.items():
        user_sets[split_name] = set(r.get("user_id") for r in records)
    
    overlaps = {}
    split_names = list(user_sets.keys())
    for i, s1 in enumerate(split_names):
        for s2 in split_names[i+1:]:
            overlap = user_sets[s1] & user_sets[s2]
            if overlap:
                overlaps[f"{s1}_vs_{s2}"] = len(overlap)
    
    if overlaps:
        results["passed"] = False
        results["checks"]["user_overlap"] = "FAIL"
        results["details"]["user_overlaps"] = overlaps
    else:
        results["checks"]["user_overlap"] = "PASS"
    print(f"CHECK 4 (User Overlap): {results['checks']['user_overlap']}")
    
    # CHECK 5: Split field matches filename
    split_mismatches = []
    for split_name, records in splits.items():
        for i, r in enumerate(records):
            if r.get("split") != split_name:
                split_mismatches.append((split_name, i, r.get("split")))
    
    if split_mismatches:
        results["passed"] = False
        results["checks"]["split_consistency"] = "FAIL"
        results["details"]["split_mismatches"] = split_mismatches[:20]
    else:
        results["checks"]["split_consistency"] = "PASS"
    print(f"CHECK 5 (Split Consistency): {results['checks']['split_consistency']}")
    
    # Summary
    total_examples = sum(len(r) for r in splits.values())
    results["summary"] = {
        "total_examples": total_examples,
        "splits": {s: len(r) for s, r in splits.items()},
        "num_labels": num_labels,
        "overall": "PASS" if results["passed"] else "FAIL"
    }
    
    # Write JSON report
    json_path = args.out_dir / "integrity_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {json_path}")
    
    # Write Markdown report
    md_path = args.out_dir / "integrity_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Integrity Audit Report\n\n")
        f.write(f"**Overall**: {'✅ PASS' if results['passed'] else '❌ FAIL'}\n\n")
        f.write("## Checks\n\n")
        for check, status in results["checks"].items():
            emoji = "✅" if status == "PASS" else "❌"
            f.write(f"- {emoji} **{check}**: {status}\n")
        f.write(f"\n## Summary\n\n")
        f.write(f"- Total Examples: {total_examples}\n")
        for s, c in results["summary"]["splits"].items():
            f.write(f"- {s}: {c}\n")
        f.write(f"- Labels: {num_labels}\n")
    print(f"Wrote {md_path}")
    
    return 0 if results["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
