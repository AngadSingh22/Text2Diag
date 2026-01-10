#!/usr/bin/env python3
"""
Week 4.1: Faithfulness Baselines.
Compares Evidence Spans vs Random Spans vs Label Shuffle.
"""
import sys
from pathlib import Path
import logging
import argparse
import json
import random
import numpy as np
import torch
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from text2diag.explain.attribution import compute_input_gradients
from text2diag.explain.spans import extract_spans
from text2diag.explain.faithfulness import verify_faithfulness

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def load_jsonl(path):
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def generate_random_spans(text_len, ref_spans):
    """Generates random spans matching count and approx length of ref_spans."""
    if not ref_spans:
        return []
    
    count = len(ref_spans)
    rand_spans = []
    
    for ref in ref_spans:
        span_len = ref["end"] - ref["start"]
        
        # Try finding a random start
        # We try 10 times to find a non-overlapping valid spot, otherwise force or skip
        for _ in range(10):
            if text_len <= span_len:
                start = 0
            else:
                start = random.randint(0, text_len - span_len)
            end = start + span_len
            
            # Simple check to ensure we generate output matching format
            # Creating dummy snippet/score
            cand = {"start": start, "end": end, "score": 0.0, "snippet": "[RANDOM]"}
            break # Just take the first valid bound
            
        rand_spans.append(cand)
        
    return rand_spans

def main():
    parser = argparse.ArgumentParser(description="Week 4.1: Faithfulness Baselines")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--temperature_json", type=Path, required=True)
    parser.add_argument("--label_map", type=Path, required=True)
    parser.add_argument("--dataset_file", type=Path, required=True)
    parser.add_argument("--preds_file", type=Path, required=True)
    parser.add_argument("--out_dir", type=Path, required=True)
    parser.add_argument("--sample_n", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--top_labels", type=int, default=2)
    
    args = parser.parse_args()
    
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Load Resources
    logger.info("Loading model/tokenizer...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(str(args.checkpoint), local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(str(args.checkpoint), local_files_only=True)
    except:
        tokenizer = AutoTokenizer.from_pretrained(str(args.checkpoint))
        model = AutoModelForSequenceClassification.from_pretrained(str(args.checkpoint))
        
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    
    with open(args.label_map, "r") as f:
        label2id = json.load(f)
    if isinstance(label2id, list): label2id = {l:i for i,l in enumerate(sorted(label2id))}
    id2label = {int(v): k for k,v in label2id.items()}
    all_label_ids = list(id2label.keys())
    
    with open(args.temperature_json, "r") as f:
        temperature = json.load(f).get("temperature", 1.0)
        
    # 2. Load Data
    data = load_jsonl(args.dataset_file)
    data_map = {r["example_id"]: r for r in data if "example_id" in r}
    
    preds = load_jsonl(args.preds_file)
    valid_preds = [p for p in preds if p.get("example_id") in data_map]
    
    # 3. Sample
    if args.sample_n < len(valid_preds):
        sampled = random.sample(valid_preds, args.sample_n)
    else:
        sampled = valid_preds
        
    results = []
    
    MAX_LEN = 512
    
    logger.info("Running Baselines...")
    for item in tqdm(sampled):
        eid = item["example_id"]
        text = data_map[eid]["text"]
        
        # Skip if too short
        if len(text) < 10:
            continue
            
        probs = item["probs"]
        top_indices = np.argsort(probs)[::-1][:args.top_labels]
        
        for idx in top_indices:
            label_idx = int(idx)
            
            try:
                # A. Evidence Spans
                # Note: using max_len=512 via new signature
                attrs = compute_input_gradients(model, tokenizer, text, label_idx, device=device, max_len=MAX_LEN)
                spans_A = extract_spans(attrs, text, k=12, max_spans=3)
                
                if not spans_A:
                    continue
                    
                faith_A = verify_faithfulness(model, tokenizer, text, spans_A, label_idx, temperature=temperature, device=device)
                
                # B. Random Spans
                spans_B = generate_random_spans(len(text), spans_A)
                faith_B = verify_faithfulness(model, tokenizer, text, spans_B, label_idx, temperature=temperature, device=device)
                
                # C. Label Shuffle
                # Verify efficacy of spans_A on a different random label
                other_labels = [l for l in all_label_ids if l != label_idx]
                if other_labels:
                    shuffle_idx = random.choice(other_labels)
                    faith_C = verify_faithfulness(model, tokenizer, text, spans_A, shuffle_idx, temperature=temperature, device=device)
                else:
                    faith_C = {"delta": 0.0, "p_full": 0.0, "name": "N/A"} # 1-class edge case
                
                results.append({
                    "example_id": eid,
                    "target_label": label_idx,
                    "delta_A_evidence": faith_A["delta"],
                    "delta_B_random": faith_B["delta"],
                    "delta_C_shuffle": faith_C["delta"],
                    "spans_count": len(spans_A)
                })
                
            except Exception as e:
                logger.warning(f"Error on {eid}: {e}")
                continue

    # 4. Report
    if not results:
        logger.error("No results!")
        return
        
    deltas_A = np.array([r["delta_A_evidence"] for r in results])
    deltas_B = np.array([r["delta_B_random"] for r in results])
    deltas_C = np.array([r["delta_C_shuffle"] for r in results])
    
    # Paired Differences (Evidence vs Random)
    diffs_AB = deltas_A - deltas_B
    diffs_AC = deltas_A - deltas_C
    
    # Metrics
    mean_diff_AB = np.mean(diffs_AB)
    dominance_rate = np.mean(deltas_A > deltas_B)
    
    # Bootstrap CI for mean_diff_AB
    n_boot = 1000
    boot_means = []
    rng = np.random.RandomState(args.seed)
    for _ in range(n_boot):
        sample = rng.choice(diffs_AB, size=len(diffs_AB), replace=True)
        boot_means.append(np.mean(sample))
    
    ci_lower = float(np.percentile(boot_means, 2.5))
    ci_upper = float(np.percentile(boot_means, 97.5))
    
    stats = {
        "sample_size": len(results),
        "A_mean_delta": float(np.mean(deltas_A)),
        "B_mean_delta": float(np.mean(deltas_B)),
        "C_mean_delta": float(np.mean(deltas_C)),
        "paired_mean_diff_AB": float(mean_diff_AB),
        "paired_dominance_rate": float(dominance_rate),
        "paired_diff_AB_ci95": [ci_lower, ci_upper],
        "masking_mode": "whitespace_replacement" # Hardcoded based on verified faithfulness.py logic
    }
    
    # Save Report
    with open(args.out_dir / "paired_faithfulness_report.json", "w") as f:
        json.dump(stats, f, indent=2)
        
    md_path = args.out_dir / "paired_faithfulness_report.md"
    with open(md_path, "w") as f:
        f.write("# Paired Faithfulness Report (Week 4.2)\n\n")
        f.write(f"- **Sample Size**: {len(results)}\n")
        f.write(f"- **Masking Mode**: {stats['masking_mode']}\n\n")
        f.write("## Paired Metrics (Evidence vs Random)\n")
        f.write(f"- **Dominance Rate**: {stats['paired_dominance_rate']:.2%} (Fraction where Evid > Rand)\n")
        f.write(f"- **Mean Difference**: {stats['paired_mean_diff_AB']:.4f}\n")
        f.write(f"- **95% CI**: [{ci_lower:.4f}, {ci_upper:.4f}]\n\n")
        f.write("## Raw Means\n")
        f.write(f"- Evidence (A): {stats['A_mean_delta']:.4f}\n")
        f.write(f"- Random (B): {stats['B_mean_delta']:.4f}\n")
        f.write(f"- Shuffle (C): {stats['C_mean_delta']:.4f}\n")
        
    logger.info(f"Baselines complete. Results in {args.out_dir}")

if __name__ == "__main__":
    main()
