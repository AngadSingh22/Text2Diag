#!/usr/bin/env python3
"""
Post-Train Evaluation Pack for Week 2 Sanitized (Week 3 Robust) Model.

Usage:
    python scripts/11_posttrain_pack_sanitized.py \
        --checkpoint_path results/week3/robust_baseline/checkpoints/checkpoint-X \
        --data_dir data/processed/reddit_mh_sanitized \
        --label_map data/processed/reddit_mh_sanitized/label2id.json \
        --out_dir results/week2_sanitized

Options:
    --smoke: Run on limited subset for testing.
"""
import argparse
import json
import re
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import f1_score, roc_auc_score
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def load_jsonl(path: Path) -> list:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

def run_inference(model, tokenizer, texts, batch_size=32, max_len=256):
    device = model.device
    all_probs = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        inputs = tokenizer(batch, padding=True, truncation=True, max_length=max_len, return_tensors="pt").to(device)
        with torch.no_grad():
            logits = model(**inputs).logits
            probs = torch.sigmoid(logits).cpu().numpy()
            all_probs.append(probs)
            
    return np.vstack(all_probs)

def compute_metrics(probs, labels, threshold=0.5):
    preds = (probs > threshold).astype(int)
    res = {
        "micro_f1": round(f1_score(labels, preds, average="micro", zero_division=0), 4),
        "macro_f1": round(f1_score(labels, preds, average="macro", zero_division=0), 4)
    }
    try:
        res["micro_auc"] = round(roc_auc_score(labels, probs, average="micro"), 4)
        res["macro_auc"] = round(roc_auc_score(labels, probs, average="macro"), 4)
    except ValueError:
        pass
    return res

def audit_shortcuts(texts):
    """Check for URLs and Reddit refs."""
    url_pattern = re.compile(r'https?://\S+|www\.\S+')
    reddit_pattern = re.compile(r'\br/[A-Za-z0-9_]+')
    
    stats = {
        "total": len(texts),
        "has_url": sum(1 for t in texts if url_pattern.search(t)),
        "has_reddit": sum(1 for t in texts if reddit_pattern.search(t))
    }
    stats["clean"] = stats["total"] - (stats["has_url"] + stats["has_reddit"])
    return stats

def analyze_sensitivity(probs, labels, texts, num_labels):
    """Analyze by length."""
    lengths = [len(t) for t in texts]
    df = pd.DataFrame({"len": lengths})
    # Probs is (N, C), Labels is (N, C)
    # Simple F1 per quartile
    df["q"] = pd.qcut(df["len"], 4, labels=["Q1", "Q2", "Q3", "Q4"])
    
    res = {}
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        indices = df[df["q"] == q].index
        if len(indices) == 0: continue
        q_probs = probs[indices]
        q_labels = labels[indices]
        m = compute_metrics(q_probs, q_labels)
        res[f"len_{q}"] = m
        
    return res

def get_label_vectors(records, label2id):
    num_labels = len(label2id)
    y_true = np.zeros((len(records), num_labels), dtype=int)
    for i, r in enumerate(records):
        for l in r.get("labels", []):
            if l in label2id:
                y_true[i, label2id[l]] = 1
    return y_true

def main():
    parser = argparse.ArgumentParser(description="Post-Train Pack Sanitized")
    parser.add_argument("--checkpoint_path", type=Path, required=True)
    parser.add_argument("--data_dir", type=Path, required=True)
    parser.add_argument("--label_map", type=Path, required=True)
    parser.add_argument("--out_dir", type=Path, default=Path("results/week2_sanitized"))
    parser.add_argument("--baseline_dir", type=Path, default=Path("results/week2"))
    parser.add_argument("--smoke", action="store_true")
    
    args = parser.parse_args()
    
    # Setup Dirs
    dirs = {
        "root": args.out_dir,
        "preds": args.out_dir / "preds",
        "metrics": args.out_dir / "metrics",
        "audits": args.out_dir / "audits",
        "compare": args.out_dir / "compare"
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
        
    print(f"Starting Post-Train Pack for {args.checkpoint_path}")
    
    # 1. Load Labels
    with open(args.label_map, "r") as f:
        label2id = json.load(f)
        if isinstance(label2id, list): # Handle list vs dict
            label2id = {l: i for i, l in enumerate(sorted(label2id))}
    id2label = {i: l for l, i in label2id.items()}
    num_labels = len(label2id)
    
    # 2. Load Model
    print("Loading Model...")
    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint_path)
    model = AutoModelForSequenceClassification.from_pretrained(args.checkpoint_path)
    model.eval()
    if torch.cuda.is_available():
        model.cuda()
        
    # 3. Process Splits
    final_metrics = {}
    
    for split in ["val", "test"]:
        print(f"\nProcessing {split}...")
        data_path = args.data_dir / f"{split}.jsonl"
        records = load_jsonl(data_path)
        
        if args.smoke:
            print("SMOKE MODE: Limiting to 200 examples")
            records = records[:200]
            
        texts = [r["text"] for r in records]
        y_true = get_label_vectors(records, label2id)
        
        # Inference
        probs = run_inference(model, tokenizer, texts)
        
        # Save Preds
        pred_path = dirs["preds"] / f"preds_{split}.jsonl"
        with open(pred_path, "w", encoding="utf-8") as f:
            for i, r in enumerate(records):
                out = {
                    "example_id": r.get("example_id", str(i)),
                    "split": split,
                    "y_true": y_true[i].tolist(),
                    "probs": probs[i].tolist()
                }
                f.write(json.dumps(out) + "\n")
        print(f"Preds saved to {pred_path}")
        
        # Metrics
        m = compute_metrics(probs, y_true)
        final_metrics[split] = m
        print(f"Metrics ({split}): {m}")
        
        # Audits (Test Only usually, but doing both for thoroughness)
        if split == "test":
            print("Running Audits...")
            # Shortcut Audit
            s_stats = audit_shortcuts(texts)
            with open(dirs["audits"] / "shortcut_report.json", "w") as f:
                json.dump(s_stats, f, indent=2)
                
            # Sensitivity Audit
            sens_stats = analyze_sensitivity(probs, y_true, texts, num_labels)
            with open(dirs["audits"] / "sensitivity_report.json", "w") as f:
                json.dump(sens_stats, f, indent=2)

    # 4. Save Final Metrics
    with open(dirs["metrics"] / "metrics.json", "w") as f:
        json.dump(final_metrics, f, indent=2)
        
    # 5. Compare with Baseline
    baseline_metrics_path = args.baseline_dir / "metrics.json"
    if baseline_metrics_path.exists():
        with open(baseline_metrics_path, "r") as f:
            base_m = json.load(f)
        
        deltas = {}
        for split in ["val", "test"]:
            if split in base_m and split in final_metrics:
                deltas[split] = {
                    "delta_micro_f1": round(final_metrics[split]["micro_f1"] - base_m[split]["micro_f1"], 4),
                    "delta_macro_f1": round(final_metrics[split]["macro_f1"] - base_m[split]["macro_f1"], 4)
                }
        
        with open(dirs["compare"] / "delta_metrics.json", "w") as f:
            json.dump(deltas, f, indent=2)
        print(f"Comparison saved. Delta (Test Micro F1): {deltas.get('test', {}).get('delta_micro_f1')}")
    else:
        print("WARNING: Baseline metrics not found. Skipping comparison.")
        
    print(f"\n[DONE] Pack Complete. Results in {args.out_dir}")

if __name__ == "__main__":
    main()
