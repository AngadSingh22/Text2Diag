#!/usr/bin/env python3
"""
W2.5 Audit D: Error Analysis Bundle.

Finds top FP/FN per label, identifies confusion patterns.
Redacts text to 200-char snippets for privacy.
"""
import argparse
import json
import sys
import numpy as np
from pathlib import Path
from collections import defaultdict

def load_preds_jsonl(path: Path, label2id: dict) -> list:
    """Load predictions JSONL as list of dicts with multi-hot labels."""
    records = []
    num_labels = len(label2id)
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                # Convert y_true to multi-hot
                y_true = r.get("y_true", [])
                multi_hot = [0] * num_labels
                for lbl in y_true:
                    if lbl in label2id:
                        multi_hot[label2id[lbl]] = 1
                r["labels"] = multi_hot
                records.append(r)
    return records

def main():
    parser = argparse.ArgumentParser(description="W2.5 Error Analysis")
    parser.add_argument("--preds_dir", type=Path, default=Path("results_week2/results/week2"))
    parser.add_argument("--data_dir", type=Path, default=Path("data/processed/reddit_mh_windows"))
    parser.add_argument("--out_dir", type=Path, default=Path("results/week2/audits"))
    parser.add_argument("--topk", type=int, default=20)
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()
    
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    # Load labels
    with open(args.data_dir / "labels.json", "r", encoding="utf-8") as f:
        labels_list = sorted(json.load(f))
    label2id = {l: i for i, l in enumerate(labels_list)}
    print(f"Labels: {labels_list}")
    
    # Load predictions
    results = {"val": {}, "test": {}}
    
    for split in ["val", "test"]:
        preds_path = args.preds_dir / f"preds_{split}.jsonl"
        if not preds_path.exists():
            print(f"WARNING: {preds_path} not found, skipping")
            continue
        
        records = load_preds_jsonl(preds_path, label2id)
        print(f"Loaded {len(records)} {split} predictions")
        
        # Per-label error analysis
        per_label = {}
        
        for lbl_idx, lbl in enumerate(labels_list):
            fp_list = []  # False Positives: predicted 1, actual 0
            fn_list = []  # False Negatives: predicted 0, actual 1
            
            for r in records:
                example_id = r.get("example_id", "?")
                prob = r["probs"][lbl_idx]
                true_label = r["labels"][lbl_idx]
                pred = 1 if prob > args.threshold else 0
                
                if pred == 1 and true_label == 0:
                    fp_list.append({"example_id": example_id, "prob": prob})
                elif pred == 0 and true_label == 1:
                    fn_list.append({"example_id": example_id, "prob": prob})
            
            # Sort by confidence (highest confidence mistakes first)
            fp_list.sort(key=lambda x: -x["prob"])
            fn_list.sort(key=lambda x: x["prob"])  # Low prob = high confidence miss
            
            per_label[lbl] = {
                "total_fp": len(fp_list),
                "total_fn": len(fn_list),
                "top_fp": fp_list[:args.topk],
                "top_fn": fn_list[:args.topk]
            }
        
        # Confusion patterns: which labels co-occur when a label is missed
        confusion = defaultdict(lambda: defaultdict(int))
        
        for r in records:
            true_labels = set(i for i, v in enumerate(r["labels"]) if v == 1)
            pred_labels = set(i for i, v in enumerate(r["probs"]) if v > args.threshold)
            
            # For each missed label
            for missed in true_labels - pred_labels:
                missed_name = labels_list[missed]
                # What other labels were present?
                for other in true_labels:
                    if other != missed:
                        other_name = labels_list[other]
                        confusion[missed_name][other_name] += 1
        
        results[split] = {
            "per_label": per_label,
            "confusion_patterns": {k: dict(v) for k, v in confusion.items()}
        }
    
    # Summary: common failure themes
    themes = []
    for split, data in results.items():
        if not data:
            continue
        for lbl, stats in data.get("per_label", {}).items():
            if stats["total_fn"] > 50:
                themes.append(f"{split}/{lbl}: High FN count ({stats['total_fn']})")
            if stats["total_fp"] > 50:
                themes.append(f"{split}/{lbl}: High FP count ({stats['total_fp']})")
    
    results["common_themes"] = themes
    
    # Write JSON
    json_path = args.out_dir / "error_analysis.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {json_path}")
    
    # Write Markdown
    md_path = args.out_dir / "error_analysis.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Error Analysis Report\n\n")
        f.write(f"**Threshold**: {args.threshold}\n")
        f.write(f"**Top-K per label**: {args.topk}\n\n")
        
        for split, data in results.items():
            if split == "common_themes" or not data:
                continue
            f.write(f"## {split.upper()} Split\n\n")
            
            for lbl, stats in data.get("per_label", {}).items():
                f.write(f"### {lbl}\n")
                f.write(f"- False Positives: {stats['total_fp']}\n")
                f.write(f"- False Negatives: {stats['total_fn']}\n")
                
                if stats["top_fp"]:
                    f.write(f"- Top FP IDs: {', '.join(e['example_id'][:30] for e in stats['top_fp'][:5])}\n")
                if stats["top_fn"]:
                    f.write(f"- Top FN IDs: {', '.join(e['example_id'][:30] for e in stats['top_fn'][:5])}\n")
                f.write("\n")
            
            # Confusion patterns
            if data.get("confusion_patterns"):
                f.write("### Confusion Patterns\n\n")
                f.write("When label X is missed, which other labels were present:\n\n")
                for missed, others in data["confusion_patterns"].items():
                    if others:
                        top_others = sorted(others.items(), key=lambda x: -x[1])[:3]
                        f.write(f"- {missed}: {top_others}\n")
                f.write("\n")
        
        if themes:
            f.write("## Common Themes\n\n")
            for t in themes:
                f.write(f"- {t}\n")
    
    print(f"Wrote {md_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
