#!/usr/bin/env python3
"""
W2.6: Leakage-Controlled Evaluation.

Compares model performance on:
- Original text (baseline)
- Sanitized text (URLs + reddit refs stripped)
- Sanitized + masked (optional)
"""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
import torch
from sklearn.metrics import f1_score, roc_auc_score

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from text2diag.text.sanitize import sanitize_text, load_sanitize_config

def load_jsonl(path: Path) -> list:
    """Load JSONL file."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

def load_model_and_tokenizer(checkpoint_path: Path):
    """Load trained model and tokenizer from checkpoint."""
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    
    tokenizer = AutoTokenizer.from_pretrained(checkpoint_path)
    model = AutoModelForSequenceClassification.from_pretrained(checkpoint_path)
    model.eval()
    
    # Move to GPU if available
    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(f"✅ GPU Available: {torch.cuda.get_device_name(0)}")
        model.cuda()
    else:
        device = torch.device("cpu")
        print("⚠️ GPU NOT Available. Using CPU (this will be slow).")
        
    model.to(device)
    
    return tokenizer, model, device

def run_inference(model, tokenizer, device, texts: list, max_len: int = 256, batch_size: int = 16) -> np.ndarray:
    """Run inference on texts, return probabilities."""
    all_probs = []
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        
        inputs = tokenizer(
            batch_texts,
            padding=True,
            truncation=True,
            max_length=max_len,
            return_tensors="pt"
        ).to(device)
        
        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.sigmoid(outputs.logits).cpu().numpy()
            all_probs.append(probs)
    
    return np.vstack(all_probs)

def compute_metrics(probs: np.ndarray, labels: np.ndarray, threshold: float = 0.5) -> dict:
    """Compute F1 and AUC metrics."""
    preds = (probs > threshold).astype(int)
    
    micro_f1 = f1_score(labels, preds, average="micro", zero_division=0)
    macro_f1 = f1_score(labels, preds, average="macro", zero_division=0)
    
    try:
        micro_auc = roc_auc_score(labels, probs, average="micro")
        macro_auc = roc_auc_score(labels, probs, average="macro")
    except ValueError:
        micro_auc = None
        macro_auc = None
    
    return {
        "micro_f1": round(micro_f1, 4),
        "macro_f1": round(macro_f1, 4),
        "micro_auc": round(micro_auc, 4) if micro_auc else None,
        "macro_auc": round(macro_auc, 4) if macro_auc else None
    }

def main():
    parser = argparse.ArgumentParser(description="W2.6 Leakage-Controlled Evaluation")
    parser.add_argument("--checkpoint", type=Path, default=Path("results_week2/results/week2/checkpoints/checkpoint-4332"))
    parser.add_argument("--data_dir", type=Path, default=Path("data/processed/reddit_mh_windows"))
    parser.add_argument("--out_dir", type=Path, default=Path("results/week2/remediation"))
    parser.add_argument("--sanitize_config", type=Path, default=Path("configs/sanitize.yaml"))
    parser.add_argument("--enable_masked", action="store_true", help="Also eval with diagnosis word masking")
    parser.add_argument("--max_len", type=int, default=256)
    parser.add_argument("--batch_size", type=int, default=16)
    args = parser.parse_args()
    
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    # Load labels
    with open(args.data_dir / "labels.json", "r", encoding="utf-8") as f:
        labels_list = sorted(json.load(f))
    label2id = {l: i for i, l in enumerate(labels_list)}
    num_labels = len(labels_list)
    print(f"Labels: {labels_list}")
    
    # Load sanitize config
    sanitize_cfg = load_sanitize_config(args.sanitize_config)
    print(f"Sanitize config: {sanitize_cfg}")
    
    # Load model
    print(f"Loading model from {args.checkpoint}")
    tokenizer, model, device = load_model_and_tokenizer(args.checkpoint)
    print(f"Model loaded on {device}")
    
    results = {}
    
    for split in ["val", "test"]:
        data_path = args.data_dir / f"{split}.jsonl"
        if not data_path.exists():
            print(f"WARNING: {data_path} not found")
            continue
        
        records = load_jsonl(data_path)
        print(f"\nProcessing {split}: {len(records)} examples")
        
        # Extract texts and labels
        texts_original = [r["text"] for r in records]
        labels_list_raw = []
        for r in records:
            multi_hot = [0] * num_labels
            for lbl in r.get("labels", []):
                if lbl in label2id:
                    multi_hot[label2id[lbl]] = 1
            labels_list_raw.append(multi_hot)
        labels_arr = np.array(labels_list_raw)
        
        # Mode 1: Original
        print("  Running inference on original text...")
        probs_original = run_inference(model, tokenizer, device, texts_original, args.max_len, args.batch_size)
        metrics_original = compute_metrics(probs_original, labels_arr)
        print(f"  Original: {metrics_original}")
        
        # Mode 2: Sanitized
        print("  Sanitizing texts (no diagnosis masking)...")
        cfg_sanitized = {**sanitize_cfg, "mask_diagnosis_words": False}
        texts_sanitized = []
        total_stats = {"urls_removed": 0, "reddit_refs_removed": 0}
        for t in texts_original:
            clean_t, stats = sanitize_text(t, cfg_sanitized)
            texts_sanitized.append(clean_t)
            total_stats["urls_removed"] += stats["urls_removed"]
            total_stats["reddit_refs_removed"] += stats["reddit_refs_removed"]
        
        print(f"  Sanitization stats: {total_stats}")
        
        print("  Running inference on sanitized text...")
        probs_sanitized = run_inference(model, tokenizer, device, texts_sanitized, args.max_len, args.batch_size)
        metrics_sanitized = compute_metrics(probs_sanitized, labels_arr)
        print(f"  Sanitized: {metrics_sanitized}")
        
        # Compute deltas
        delta_micro_f1 = metrics_sanitized["micro_f1"] - metrics_original["micro_f1"]
        delta_macro_f1 = metrics_sanitized["macro_f1"] - metrics_original["macro_f1"]
        
        results[split] = {
            "original": metrics_original,
            "sanitized": metrics_sanitized,
            "sanitization_stats": total_stats,
            "delta_micro_f1": round(delta_micro_f1, 4),
            "delta_macro_f1": round(delta_macro_f1, 4)
        }
        
        # Mode 3: Sanitized + Masked (optional)
        if args.enable_masked:
            print("  Running with diagnosis word masking...")
            cfg_masked = {**sanitize_cfg, "mask_diagnosis_words": True}
            texts_masked = [sanitize_text(t, cfg_masked)[0] for t in texts_original]
            probs_masked = run_inference(model, tokenizer, device, texts_masked, args.max_len, args.batch_size)
            metrics_masked = compute_metrics(probs_masked, labels_arr)
            print(f"  Masked: {metrics_masked}")
            results[split]["masked"] = metrics_masked
            results[split]["delta_masked_micro_f1"] = round(metrics_masked["micro_f1"] - metrics_original["micro_f1"], 4)
        
        # Save predictions
        preds_path = args.out_dir / f"preds_{split}_sanitized.jsonl"
        with open(preds_path, "w", encoding="utf-8") as f:
            for i, r in enumerate(records):
                out = {
                    "example_id": r.get("example_id", str(i)),
                    "probs_original": probs_original[i].tolist(),
                    "probs_sanitized": probs_sanitized[i].tolist(),
                    "y_true": r.get("labels", [])
                }
                f.write(json.dumps(out) + "\n")
        print(f"  Wrote {preds_path}")
    
    # Assess PASS/FAIL
    val_results = results.get("val", {})
    delta_micro = val_results.get("delta_micro_f1", 0)
    
    if abs(delta_micro) > 0.10:
        verdict = "LIKELY SHORTCUT DEPENDENCE"
        recommendation = "Dataset rebuild with sanitization recommended"
        passed = False
    else:
        verdict = "SHORTCUT ROBUST (provisionally)"
        recommendation = "Proceed without retraining"
        passed = True
    
    results["verdict"] = verdict
    results["recommendation"] = recommendation
    results["passed"] = passed
    
    print(f"\n=== VERDICT: {verdict} ===")
    print(f"Delta Micro F1: {delta_micro}")
    print(f"Recommendation: {recommendation}")
    
    # Write JSON
    json_path = args.out_dir / "leakage_eval_metrics.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {json_path}")
    
    # Write Markdown
    md_path = args.out_dir / "leakage_eval_metrics.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Leakage-Controlled Evaluation Report\n\n")
        f.write(f"**Verdict**: {'✅' if passed else '❌'} {verdict}\n\n")
        f.write(f"**Recommendation**: {recommendation}\n\n")
        
        for split, data in results.items():
            if split in ["verdict", "recommendation", "passed"]:
                continue
            f.write(f"## {split.upper()}\n\n")
            f.write("| Mode | Micro F1 | Macro F1 | Micro AUC |\n")
            f.write("|------|----------|----------|----------|\n")
            for mode in ["original", "sanitized", "masked"]:
                if mode in data:
                    m = data[mode]
                    f.write(f"| {mode} | {m['micro_f1']} | {m['macro_f1']} | {m.get('micro_auc', 'N/A')} |\n")
            f.write(f"\n**Delta Micro F1**: {data.get('delta_micro_f1', 'N/A')}\n")
            f.write(f"**Delta Macro F1**: {data.get('delta_macro_f1', 'N/A')}\n\n")
    print(f"Wrote {md_path}")
    
    return 0 if passed else 1

if __name__ == "__main__":
    sys.exit(main())
