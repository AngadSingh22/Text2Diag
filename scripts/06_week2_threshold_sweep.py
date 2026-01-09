#!/usr/bin/env python3
"""
W2.5 Audit C: Threshold Sweep (No Calibration).

Loads val predictions and sweeps thresholds to find optimal F1.
Produces global and per-label threshold recommendations.
"""
import argparse
import json
import sys
import numpy as np
from pathlib import Path
from sklearn.metrics import f1_score

def load_preds_jsonl(path: Path, label2id: dict) -> tuple:
    """Load predictions JSONL and return probs, labels (multi-hot), example_ids."""
    probs_list = []
    labels_list = []
    ids_list = []
    num_labels = len(label2id)
    
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                probs_list.append(r["probs"])
                
                # Convert y_true (list of label names) to multi-hot
                y_true = r.get("y_true", [])
                multi_hot = [0] * num_labels
                for lbl in y_true:
                    if lbl in label2id:
                        multi_hot[label2id[lbl]] = 1
                labels_list.append(multi_hot)
                ids_list.append(r.get("example_id", ""))
    
    return np.array(probs_list), np.array(labels_list), ids_list

def main():
    parser = argparse.ArgumentParser(description="W2.5 Threshold Sweep")
    parser.add_argument("--preds_dir", type=Path, default=Path("results_week2/results/week2"))
    parser.add_argument("--out_dir", type=Path, default=Path("results/week2/audits"))
    parser.add_argument("--labels_path", type=Path, default=Path("data/processed/reddit_mh_windows/labels.json"))
    args = parser.parse_args()
    
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    with open(args.labels_path, "r", encoding="utf-8") as f:
        labels_list = sorted(json.load(f))
    label2id = {l: i for i, l in enumerate(labels_list)}
    id2label = {i: l for i, l in enumerate(labels_list)}
    print(f"Labels: {labels_list}")
    
    # Load val predictions
    val_path = args.preds_dir / "preds_val.jsonl"
    if not val_path.exists():
        print(f"ERROR: {val_path} not found")
        sys.exit(1)
    
    probs, labels, _ = load_preds_jsonl(val_path, label2id)
    print(f"Loaded {len(probs)} val predictions, shape: {probs.shape}")
    
    # Global threshold sweep
    thresholds = np.arange(0.05, 1.0, 0.05)
    global_results = []
    
    for t in thresholds:
        preds = (probs > t).astype(int)
        micro = f1_score(labels, preds, average="micro", zero_division=0)
        macro = f1_score(labels, preds, average="macro", zero_division=0)
        global_results.append({
            "threshold": round(t, 2),
            "micro_f1": round(micro, 4),
            "macro_f1": round(macro, 4)
        })
    
    # Find best global threshold
    best_micro = max(global_results, key=lambda x: x["micro_f1"])
    best_macro = max(global_results, key=lambda x: x["macro_f1"])
    
    print(f"Best Global (Micro F1): t={best_micro['threshold']}, F1={best_micro['micro_f1']}")
    print(f"Best Global (Macro F1): t={best_macro['threshold']}, F1={best_macro['macro_f1']}")
    
    # Per-label threshold sweep
    per_label_thresholds = {}
    per_label_details = {}
    
    for i, lbl in enumerate(labels_list):
        y_true = labels[:, i]
        y_prob = probs[:, i]
        
        best_t = 0.5
        best_f1 = 0.0
        
        for t in thresholds:
            y_pred = (y_prob > t).astype(int)
            f1 = f1_score(y_true, y_pred, zero_division=0)
            if f1 > best_f1:
                best_f1 = f1
                best_t = t
        
        per_label_thresholds[lbl] = round(best_t, 2)
        per_label_details[lbl] = {"threshold": round(best_t, 2), "f1": round(best_f1, 4)}
    
    print(f"Per-label thresholds: {per_label_thresholds}")
    
    # Write results
    results = {
        "global_sweep": global_results,
        "best_global_micro": best_micro,
        "best_global_macro": best_macro,
        "per_label": per_label_details
    }
    
    json_path = args.out_dir / "threshold_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {json_path}")
    
    # Write global thresholds
    global_thresh_path = args.out_dir / "thresholds_global.json"
    with open(global_thresh_path, "w", encoding="utf-8") as f:
        json.dump({"micro_optimized": best_micro["threshold"], "macro_optimized": best_macro["threshold"]}, f, indent=2)
    print(f"Wrote {global_thresh_path}")
    
    # Write per-label thresholds
    per_label_path = args.out_dir / "thresholds_per_label.json"
    with open(per_label_path, "w", encoding="utf-8") as f:
        json.dump(per_label_thresholds, f, indent=2)
    print(f"Wrote {per_label_path}")
    
    # Write Markdown
    md_path = args.out_dir / "threshold_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Threshold Sweep Report\n\n")
        f.write("## Best Global Thresholds\n\n")
        f.write(f"- **Micro F1 Optimized**: t={best_micro['threshold']} (F1={best_micro['micro_f1']})\n")
        f.write(f"- **Macro F1 Optimized**: t={best_macro['threshold']} (F1={best_macro['macro_f1']})\n\n")
        f.write("## Per-Label Thresholds\n\n")
        f.write("| Label | Threshold | F1 |\n")
        f.write("|-------|-----------|----|\n")
        for lbl, d in sorted(per_label_details.items()):
            f.write(f"| {lbl} | {d['threshold']} | {d['f1']} |\n")
        f.write("\n## Global Sweep\n\n")
        f.write("| Threshold | Micro F1 | Macro F1 |\n")
        f.write("|-----------|----------|----------|\n")
        for r in global_results:
            f.write(f"| {r['threshold']} | {r['micro_f1']} | {r['macro_f1']} |\n")
    print(f"Wrote {md_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
