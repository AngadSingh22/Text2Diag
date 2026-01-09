#!/usr/bin/env python3
"""
W2.5 Audit E: Sensitivity Smoke Tests.

Stratifies metrics by:
1. Text length quartiles
2. Label cardinality (number of labels per example)
3. Label type (condition vs generic) if available
"""
import argparse
import json
import sys
import numpy as np
from pathlib import Path
from collections import defaultdict
from sklearn.metrics import f1_score

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

def load_data_jsonl(path: Path) -> dict:
    """Load data JSONL and return dict keyed by example_id."""
    data = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                data[r.get("example_id", "")] = r
    return data

def compute_f1(labels, probs, threshold=0.5):
    """Compute micro and macro F1."""
    preds = (np.array(probs) > threshold).astype(int)
    labels = np.array(labels)
    if len(labels) == 0:
        return 0.0, 0.0
    micro = f1_score(labels, preds, average="micro", zero_division=0)
    macro = f1_score(labels, preds, average="macro", zero_division=0)
    return micro, macro

def main():
    parser = argparse.ArgumentParser(description="W2.5 Sensitivity Smoke")
    parser.add_argument("--preds_dir", type=Path, default=Path("results_week2/results/week2"))
    parser.add_argument("--data_dir", type=Path, default=Path("data/processed/reddit_mh_windows"))
    parser.add_argument("--out_dir", type=Path, default=Path("results/week2/audits"))
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()
    
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    # Load labels
    with open(args.data_dir / "labels.json", "r", encoding="utf-8") as f:
        labels_list = sorted(json.load(f))
    label2id = {l: i for i, l in enumerate(labels_list)}
    
    # Load val data and preds
    val_data = load_data_jsonl(args.data_dir / "val.jsonl")
    val_preds = load_preds_jsonl(args.preds_dir / "preds_val.jsonl", label2id)
    
    print(f"Loaded {len(val_data)} val data records, {len(val_preds)} predictions")
    
    # Merge data with preds
    merged = []
    for p in val_preds:
        eid = p.get("example_id", "")
        if eid in val_data:
            d = val_data[eid]
            merged.append({
                "example_id": eid,
                "text_len": len(d.get("text", "")),
                "label_cardinality": sum(p["labels"]),
                "label_types": d.get("label_types", []),
                "probs": p["probs"],
                "labels": p["labels"]
            })
    
    print(f"Merged {len(merged)} records")
    
    results = {"by_text_length": {}, "by_cardinality": {}, "by_label_type": {}}
    
    # 1. Stratify by text length quartiles
    lengths = [m["text_len"] for m in merged]
    if lengths:
        q25, q50, q75 = np.percentile(lengths, [25, 50, 75])
        
        bins = {
            "Q1 (short)": [m for m in merged if m["text_len"] <= q25],
            "Q2": [m for m in merged if q25 < m["text_len"] <= q50],
            "Q3": [m for m in merged if q50 < m["text_len"] <= q75],
            "Q4 (long)": [m for m in merged if m["text_len"] > q75]
        }
        
        for bin_name, records in bins.items():
            if records:
                all_labels = [r["labels"] for r in records]
                all_probs = [r["probs"] for r in records]
                micro, macro = compute_f1(all_labels, all_probs, args.threshold)
                results["by_text_length"][bin_name] = {
                    "count": len(records),
                    "micro_f1": round(micro, 4),
                    "macro_f1": round(macro, 4)
                }
    
    # 2. Stratify by label cardinality
    card_bins = {
        "1 label": [m for m in merged if m["label_cardinality"] == 1],
        "2 labels": [m for m in merged if m["label_cardinality"] == 2],
        "3+ labels": [m for m in merged if m["label_cardinality"] >= 3]
    }
    
    for bin_name, records in card_bins.items():
        if records:
            all_labels = [r["labels"] for r in records]
            all_probs = [r["probs"] for r in records]
            micro, macro = compute_f1(all_labels, all_probs, args.threshold)
            results["by_cardinality"][bin_name] = {
                "count": len(records),
                "micro_f1": round(micro, 4),
                "macro_f1": round(macro, 4)
            }
    
    # 3. Stratify by label type (if available)
    type_bins = defaultdict(list)
    for m in merged:
        types = m.get("label_types", [])
        if "condition" in types and "generic" not in types:
            type_bins["condition_only"].append(m)
        elif "generic" in types and "condition" not in types:
            type_bins["generic_only"].append(m)
        elif "condition" in types and "generic" in types:
            type_bins["mixed"].append(m)
        else:
            type_bins["other"].append(m)
    
    for bin_name, records in type_bins.items():
        if records:
            all_labels = [r["labels"] for r in records]
            all_probs = [r["probs"] for r in records]
            micro, macro = compute_f1(all_labels, all_probs, args.threshold)
            results["by_label_type"][bin_name] = {
                "count": len(records),
                "micro_f1": round(micro, 4),
                "macro_f1": round(macro, 4)
            }
    
    # Write JSON
    json_path = args.out_dir / "sensitivity_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {json_path}")
    
    # Write Markdown
    md_path = args.out_dir / "sensitivity_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Sensitivity Analysis Report\n\n")
        f.write(f"**Threshold**: {args.threshold}\n\n")
        
        f.write("## By Text Length Quartile\n\n")
        f.write("| Quartile | Count | Micro F1 | Macro F1 |\n")
        f.write("|----------|-------|----------|----------|\n")
        for q, stats in results["by_text_length"].items():
            f.write(f"| {q} | {stats['count']} | {stats['micro_f1']} | {stats['macro_f1']} |\n")
        
        f.write("\n## By Label Cardinality\n\n")
        f.write("| Cardinality | Count | Micro F1 | Macro F1 |\n")
        f.write("|-------------|-------|----------|----------|\n")
        for c, stats in results["by_cardinality"].items():
            f.write(f"| {c} | {stats['count']} | {stats['micro_f1']} | {stats['macro_f1']} |\n")
        
        f.write("\n## By Label Type\n\n")
        f.write("| Type | Count | Micro F1 | Macro F1 |\n")
        f.write("|------|-------|----------|----------|\n")
        for t, stats in results["by_label_type"].items():
            f.write(f"| {t} | {stats['count']} | {stats['micro_f1']} | {stats['macro_f1']} |\n")
    
    print(f"Wrote {md_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
