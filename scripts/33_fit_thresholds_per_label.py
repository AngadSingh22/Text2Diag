#!/usr/bin/env python3
"""
Fit Per-Label Thresholds (Week 6+).
Tunes classification thresholds on validation set to maximize F1.
"""
import argparse
import json
import logging
import numpy as np
from pathlib import Path
from sklearn.metrics import f1_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(msg)s")
logger = logging.getLogger(__name__)

def load_predictions(preds_file):
    y_true_list = []
    y_score_list = []
    label_names = None
    
    with open(preds_file) as f:
        for line in f:
            if not line.strip(): continue
            item = json.loads(line)
            
            # Extract labels
            if label_names is None:
                label_names = [l["name"] for l in item["labels"]]
                
            y_true_row = [1 if l["decision"] == 1 else 0 for l in item.get("ground_truth", [])] # This assumes GT is in output? 
            # Wait, contract output usually doesn't have GT unless we injected it. 
            # We usually need a separate GT file or the input had GT.
            # Week 6 freeze run inputs (val.jsonl) have 'labels' (ints).
            # But the OUTPUT (preds_val.jsonl) typically doesn't copy GT unless modified.
            # Let's check schemas. E2E runner doesn't output GT.
            # So we need to join with input file.
            pass

    return None

# Re-implementing correctly: Need GT from input file and Preds from output file
def load_data(preds_file, truth_file, label_map):
    # Load Label Map
    with open(label_map) as f:
        l2i = json.load(f)
    if isinstance(l2i, list): l2i = {l:i for i,l in enumerate(sorted(l2i))}
    id2label = {v:k for k,v in l2i.items()}
    num_labels = len(id2label)
    
    # Load Truth
    eid_to_truth = {}
    with open(truth_file) as f:
        for line in f:
            if not line.strip(): continue
            item = json.loads(line)
            eid = item.get("example_id")
            labels = item.get("labels", [])
            # Labels might be ints or strings (names)
            # Week 1 `build_jsonl` produced "labels": [0, 5, ...] (indices)
            # But let's be robust
            vec = np.zeros(num_labels, dtype=int)
            for l in labels:
                if isinstance(l, int):
                    if l < num_labels: vec[l] = 1
                elif isinstance(l, str):
                    idx = l2i.get(l)
                    if idx is not None: vec[idx] = 1
            eid_to_truth[eid] = vec
            
    # Load Preds
    y_trues = []
    y_scores = []
    
    with open(preds_file) as f:
        for line in f:
            if not line.strip(): continue
            item = json.loads(line)
            eid = item.get("example_id")
            
            if eid not in eid_to_truth: continue
            
            truth = eid_to_truth[eid]
            
            # Scores
            scores = np.zeros(num_labels)
            for lbl in item["labels"]:
                idx = l2i.get(lbl["name"])
                if idx is not None:
                    scores[idx] = lbl["prob_calibrated"]
            
            y_trues.append(truth)
            y_scores.append(scores)
            
    return np.array(y_trues), np.array(y_scores), id2label

def fit_thresholds(y_true, y_score, num_labels):
    thresholds = []
    scores = []
    
    for i in range(num_labels):
        yt = y_true[:, i]
        ys = y_score[:, i]
        
        best_t = 0.5
        best_f1 = 0.0
        
        # Sweep
        search_space = np.linspace(0.01, 0.99, 99)
        for t in search_space:
            yp = (ys >= t).astype(int)
            if np.sum(yp) == 0: f1 = 0
            else: f1 = f1_score(yt, yp)
            
            if f1 > best_f1:
                best_f1 = f1
                best_t = t
                
        thresholds.append(round(best_t, 2))
        scores.append(round(best_f1, 4))
        
    return thresholds, scores

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preds_val", required=True)
    parser.add_argument("--truth_val", required=True)
    parser.add_argument("--label_map", required=True)
    parser.add_argument("--out_file", required=True)
    args = parser.parse_args()
    
    y_true, y_score, id2label = load_data(args.preds_val, args.truth_val, args.label_map)
    logger.info(f"Loaded {len(y_true)} matched examples.")
    
    thresholds, f1s = fit_thresholds(y_true, y_score, len(id2label))
    
    out_dict = {}
    for i in range(len(id2label)):
        name = id2label[i]
        out_dict[name] = thresholds[i]
        logger.info(f"Label {name}: Best F1={f1s[i]} at T={thresholds[i]}")
        
    final = {
        "method": "val_tuned_f1",
        "thresholds": out_dict
    }
    
    with open(args.out_file, "w") as f:
        json.dump(out_dict, f, indent=2) # Save simple dict for easy loading
        
    logger.info(f"Saved thresholds to {args.out_file}")

if __name__ == "__main__":
    main()
