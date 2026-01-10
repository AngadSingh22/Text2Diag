import json
import numpy as np
import argparse
from pathlib import Path
from sklearn.metrics import f1_score

def load_preds(path):
    y_true = []
    probs = []
    with open(path, "r") as f:
        for line in f:
            d = json.loads(line)
            y_true.append(d["y_true"])
            probs.append(d["probs"])
    return np.array(y_true), np.array(probs)

def tune_global(y_true, probs):
    best_t = 0.5
    best_f1 = 0.0
    for t in np.arange(0.1, 0.9, 0.01):
        preds = (probs > t).astype(int)
        f1 = f1_score(y_true, preds, average="micro", zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_t = t
    return best_t, best_f1

def tune_per_label(y_true, probs, id2label):
    thresholds = {}
    for i in range(y_true.shape[1]):
        best_t = 0.5
        best_f1 = 0.0
        # Check if label has any positives
        if y_true[:, i].sum() == 0:
            thresholds[id2label[i]] = 0.5
            continue
            
        for t in np.arange(0.1, 0.9, 0.05):
            p = (probs[:, i] > t).astype(int)
            f1 = f1_score(y_true[:, i], p, zero_division=0)
            if f1 > best_f1:
                best_f1 = f1
                best_t = t
        thresholds[str(i)] = round(float(best_t), 3) # Using ID as key for now
        if id2label:
             thresholds[id2label[str(i)]] = round(float(best_t), 3)
    return thresholds

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preds_file", type=Path, required=True)
    parser.add_argument("--label_map", type=Path, required=True)
    parser.add_argument("--out_dir", type=Path, required=True)
    args = parser.parse_args()
    
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    print("Loading preds...")
    y_true, probs = load_preds(args.preds_file)
    
    print("Loading labels...")
    with open(args.label_map, "r") as f:
        l2id = json.load(f)
        # Handle list or dict
        if isinstance(l2id, list):
            l2id = {l: i for i, l in enumerate(sorted(l2id))}
    id2label = {str(v): k for k, v in l2id.items()}
    
    print("Tuning Global...")
    g_t, g_f1 = tune_global(y_true, probs)
    print(f"Best Global T: {g_t:.3f} (F1: {g_f1:.4f})")
    
    print("Tuning Per-Label...")
    pl_t = tune_per_label(y_true, probs, id2label)
    
    # Save
    with open(args.out_dir / "thresholds_global.json", "w") as f:
        json.dump({"global_threshold": round(g_t, 3)}, f, indent=2)
        
    with open(args.out_dir / "thresholds_per_label.json", "w") as f:
        json.dump(pl_t, f, indent=2)
        
    print(f"Saved to {args.out_dir}")

if __name__ == "__main__":
    main()
