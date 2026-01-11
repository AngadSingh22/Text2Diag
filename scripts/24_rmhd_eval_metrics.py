"""
Scripts/24_rmhd_eval_metrics.py
Computes metrics for RMHD external validation.
"""
import argparse
import json
import logging
import numpy as np
from sklearn.metrics import f1_score, roc_auc_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pred_file", required=True)
    parser.add_argument("--gold_file", required=True) # The JSONL built by script 21
    parser.add_argument("--out_dir", required=True)
    args = parser.parse_args()
    
    # Load Gold
    gold_map = {}
    with open(args.gold_file, "r") as f:
        for line in f:
            x = json.loads(line)
            gold_map[x["example_id"]] = x["labels"] # List of true labels
            
    # Load Preds
    preds = []
    golds = []
    
    # We focus on the core labels we care about
    CORE_LABELS = ["adhd", "depression", "ptsd", "ocd"]
    # Dynamic: Only those present in gold set?
    
    present_labels = set()
    for labels in gold_map.values():
        present_labels.update(labels)
        
    # Intersect with CORE
    eval_labels = [l for l in CORE_LABELS if l in present_labels]
    
    y_true = [] # [N, K]
    y_score = [] # [N, K]
    y_pred = [] # [N, K]
    
    with open(args.pred_file, "r") as f:
        for line in f:
            p = json.loads(line)
            eid = p["example_id"]
            if eid not in gold_map: continue
            
            # True vector
            true_lbls = gold_map[eid]
            vec_true = [1 if l in true_lbls else 0 for l in eval_labels]
            y_true.append(vec_true)
            
            # Pred vector
            vec_score = []
            vec_pred = []
            
            # Parsing "labels" list in output
            # p["labels"] is list of objects with "name", "prob_calibrated", "decision"
            
            p_map = {l["name"]: l for l in p["labels"]}
            
            for l in eval_labels:
                if l in p_map:
                    vec_score.append(p_map[l]["prob_calibrated"])
                    vec_pred.append(p_map[l]["decision"])
                else:
                    vec_score.append(0.0)
                    vec_pred.append(0)
            
            y_score.append(vec_score)
            y_pred.append(vec_pred)
            
    y_true = np.array(y_true)
    y_score = np.array(y_score)
    y_pred = np.array(y_pred)
    
    # Metrics
    metrics = {}
    
    # Micro F1
    metrics["micro_f1"] = f1_score(y_true, y_pred, average="micro")
    
    # Macro F1
    metrics["macro_f1"] = f1_score(y_true, y_pred, average="macro")
    
    # Macro AUC
    try:
        metrics["macro_auc"] = roc_auc_score(y_true, y_score, average="macro")
    except:
        metrics["macro_auc"] = None
        
    metrics["per_label"] = {}
    for i, lbl in enumerate(eval_labels):
        metrics["per_label"][lbl] = {
            "f1": f1_score(y_true[:, i], y_pred[:, i]),
            "support": int(y_true[:, i].sum())
        }
        
    print(json.dumps(metrics, indent=2))
    

if __name__ == "__main__":
    main()
