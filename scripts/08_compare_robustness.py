#!/usr/bin/env python3
"""
Week 3: Comparative Robustness Evaluation.

Compares two models:
1. Baseline (Week 2): Potentially shortcut-reliant.
2. Robust (Week 3): Trained on sanitized/masked data.

Evaluates both on:
- Original Test Set (Has shortcuts)
- Sanitized Test Set (Shortcuts masked)

Goal: Prove that W3 model is stable (robust) while W2 model crashes when shortcuts are removed.
"""
import argparse
import json
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import f1_score, roc_auc_score
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from text2diag.data.cleaning import sanitize_text, load_sanitize_config

def load_jsonl(path: Path) -> list:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

def load_model(path: Path):
    print(f"Loading model from {path}...")
    tokenizer = AutoTokenizer.from_pretrained(path)
    model = AutoModelForSequenceClassification.from_pretrained(path)
    model.eval()
    if torch.cuda.is_available():
        model.cuda()
    return tokenizer, model

def run_inference(model, tokenizer, texts, batch_size=32):
    device = model.device
    all_probs = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        inputs = tokenizer(batch, padding=True, truncation=True, max_length=256, return_tensors="pt").to(device)
        with torch.no_grad():
            logits = model(**inputs).logits
            probs = torch.sigmoid(logits).cpu().numpy()
            all_probs.append(probs)
            
    return np.vstack(all_probs)

def compute_metrics(probs, labels, threshold=0.5):
    preds = (probs > threshold).astype(int)
    return {
        "micro_f1": round(f1_score(labels, preds, average="micro", zero_division=0), 4),
        "macro_f1": round(f1_score(labels, preds, average="macro", zero_division=0), 4),
        "micro_auc": round(roc_auc_score(labels, probs, average="micro"), 4)
    }

def main():
    parser = argparse.ArgumentParser(description="Compare W2 vs W3 Models")
    # Checkpoints
    parser.add_argument("--ckpt_w2", type=Path, required=True, help="Path to Week 2 (Shortcut) checkpoint")
    parser.add_argument("--ckpt_w3", type=Path, required=True, help="Path to Week 3 (Robust) checkpoint")
    
    # Data
    parser.add_argument("--data_dir", type=Path, default=Path("data/processed/reddit_mh_windows"))
    parser.add_argument("--clean_config", type=Path, default=Path("configs/text_cleaning.yaml"))
    parser.add_argument("--out_dir", type=Path, default=Path("results/week3/comparison"))
    
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Load Data (Use Original Test Set from W2 context as ground truth source)
    # We want to see how they behave on REAL data (original) and BLIND data (sanitized)
    test_path = args.data_dir / "test.jsonl"
    print(f"Loading test data from {test_path}")
    records = load_jsonl(test_path)
    
    # Prepare Labels
    with open(args.data_dir / "labels.json", "r") as f:
        labels_list = sorted(json.load(f))
    label2id = {l: i for i, l in enumerate(labels_list)}
    
    y_true = np.zeros((len(records), len(labels_list)), dtype=int)
    for i, r in enumerate(records):
        for l in r.get("labels", []):
            if l in label2id:
                y_true[i, label2id[l]] = 1
                
    # Prepare Texts
    texts_orig = [r["text"] for r in records]
    
    # Prepare Sanitized Texts (Masked)
    clean_cfg = load_sanitize_config(args.clean_config)
    clean_cfg["mask_diagnosis_words"] = True # FORCE masking for comparison
    print("Sanitizing test set (Masked)...")
    texts_masked = [sanitize_text(t, clean_cfg)[0] for t in texts_orig]
    
    datasets = {
        "Original (Shortcuts)": texts_orig,
        "Masked (Blind)": texts_masked
    }
    
    results = []
    
    # 2. Evaluate Models
    for model_name, ckpt_path in [("W2 (Baseline)", args.ckpt_w2), ("W3 (Robust)", args.ckpt_w3)]:
        tokenizer, model = load_model(ckpt_path)
        
        for data_name, texts in datasets.items():
            print(f"Evaluatinig {model_name} on {data_name}...")
            probs = run_inference(model, tokenizer, texts)
            metrics = compute_metrics(probs, y_true)
            
            res = {
                "Model": model_name,
                "Dataset": data_name,
                **metrics
            }
            results.append(res)
            print(f"  -> {metrics}")
            
    # 3. Save & Report
    df = pd.DataFrame(results)
    print("\n=== FINAL COMPARISON ===")
    print(df.to_markdown(index=False))
    
    df.to_csv(args.out_dir / "comparison_table.csv", index=False)
    with open(args.out_dir / "report.md", "w") as f:
        f.write("# Robustness Comparison: Week 2 vs Week 3\n\n")
        f.write(df.to_markdown(index=False))
        f.write("\n\n## Interpretation\n")
        f.write("- **W2 Model** should drop significantly on 'Masked' data (Constraint failure).\n")
        f.write("- **W3 Model** should be stable across both (Robustness success).\n")
        
    print(f"\nSaved to {args.out_dir}")

if __name__ == "__main__":
    main()
