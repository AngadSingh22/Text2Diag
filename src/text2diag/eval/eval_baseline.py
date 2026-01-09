"""
Evaluation Logic for Baseline Model.

Metrics calculation and prediction dumps.
"""
import json
import numpy as np
import torch
from pathlib import Path
from typing import Dict, Any, List
from tqdm import tqdm
from torch.utils.data import DataLoader
from sklearn.metrics import f1_score, roc_auc_score, accuracy_score

def evaluate_and_dump(
    model: Any, 
    dataset: Any, 
    split_name: str, 
    out_dir: Path,
    id2label: Dict[int, str]
) -> Dict[str, float]:
    """
    Run inference, save dumps (JSONL), and return aggregated metrics.
    """
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    
    # DataLoader
    loader = DataLoader(dataset, batch_size=16, shuffle=False, num_workers=0)
    
    all_logits = []
    all_labels = []
    all_ids = []
    
    print(f"Running evaluation on {split_name}...")
    with torch.no_grad():
        for batch in tqdm(loader):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)
            ids = batch["example_id"]
            
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            
            all_logits.append(logits.cpu().numpy())
            all_labels.append(labels.cpu().numpy())
            all_ids.extend(ids)
            
    # Concatenate
    all_logits = np.concatenate(all_logits, axis=0)
    all_labels = np.concatenate(all_labels, axis=0) # [N, num_labels]
    
    # Probs
    all_probs = 1.0 / (1.0 + np.exp(-all_logits))
    
    # Helper for JSON safe values
    def safe_float(val):
        if val is None:
            return None
        if isinstance(val, (int, float, np.number)):
            if np.isnan(val) or np.isinf(val):
                return None
            return float(val)
        return val

    # 1. Write Dumps (JSONL)
    dump_path = out_dir / f"preds_{split_name}.jsonl"
    print(f"Writing dump to {dump_path}")
    
    with open(dump_path, "w", encoding="utf-8") as f:
        for i, example_id in enumerate(all_ids):
            # Get active label names for ground truth
            true_indices = np.where(all_labels[i] == 1.0)[0]
            true_names = [id2label[idx] for idx in true_indices]
            
            record = {
                "example_id": example_id,
                "split": split_name,
                "y_true": true_names,
                "logits": [round(float(x), 4) for x in all_logits[i]],
                "probs": [round(float(x), 4) for x in all_probs[i]]
            }
            f.write(json.dumps(record) + "\n")
            
    # 2. Calculate Metrics
    results = {}
    
    # Threshold 0.5 metrics
    preds_05 = (all_probs > 0.5).astype(int)
    
    results["micro_f1"] = float(f1_score(all_labels, preds_05, average="micro", zero_division=0))
    results["macro_f1"] = float(f1_score(all_labels, preds_05, average="macro", zero_division=0))
    
    # AUC (if possible)
    try:
        results["micro_roc_auc"] = safe_float(roc_auc_score(all_labels, all_probs, average="micro"))
        results["macro_roc_auc"] = safe_float(roc_auc_score(all_labels, all_probs, average="macro"))
    except ValueError:
        # Happens if a class has no positive examples in split
        results["micro_roc_auc"] = None
        results["macro_roc_auc"] = None
        
    # Per-label metrics
    per_label = {}
    for idx, label_name in id2label.items():
        y_true = all_labels[:, idx]
        y_score = all_probs[:, idx]
        y_pred = preds_05[:, idx]
        
        support = int(y_true.sum())
        if support > 0:
            f1 = f1_score(y_true, y_pred, zero_division=0)
            try:
                auc = roc_auc_score(y_true, y_score)
            except ValueError:
                auc = None
        else:
            f1 = 0.0
            auc = 0.0
            
        per_label[label_name] = {
            "support": support,
            "f1": round(float(f1), 4),
            "roc_auc": safe_float(auc)
        }
    
    results["per_label"] = per_label
    
    return results
