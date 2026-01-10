#!/usr/bin/env python3
"""
Week 5.1: Occlusion Audit.
Performs causal analysis of evidence spans by masking them individually and in union.
Comparisons against random baselines.
"""
import sys
import argparse
import logging
import json
import random
import numpy as np
import torch
from pathlib import Path
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from text2diag.explain.attribution import compute_attributions
from text2diag.explain.spans import extract_spans
from text2diag.explain.faithfulness import verify_faithfulness

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(msg)s")
logger = logging.getLogger(__name__)

def generate_random_spans(text, count, lengths):
    """
    Generates random spans with matching lengths.
    Naive approach: pick random start, check bounds, non-overlapping (harder).
    We allow overlaps for simplicity or retry?
    Let's try to be non-overlapping if possible, or just simple random.
    The baseline script used a simple approach. Reimplementing here.
    """
    # Simple random replacement
    # We want 'count' spans with specific 'lengths'
    # For a robust random baseline, we just pick random slice of length L.
    # To handle overlaps, we mask a consumed map.
    
    text_len = len(text)
    spans = []
    mask_map = np.zeros(text_len, dtype=bool)
    
    # Sort lengths largest to smallest to fit them easier
    sorted_lengths = sorted(lengths, reverse=True)
    
    for L in sorted_lengths:
        # Try finding a free spot
        attempts = 0
        while attempts < 50:
            if text_len - L <= 0: break
            start = random.randint(0, text_len - L)
            end = start + L
            
            # Check overlap
            if not np.any(mask_map[start:end]):
                spans.append({"start": start, "end": end, "score": 0.0, "snippet": text[start:end]})
                mask_map[start:end] = True
                break
            attempts += 1
            
    return spans

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--temperature_json", required=True)
    parser.add_argument("--label_map", required=True)
    parser.add_argument("--dataset_file", required=True)
    parser.add_argument("--preds_file", required=True)
    parser.add_argument("--out_dir", type=Path, default="results/week5_audit")
    parser.add_argument("--sample_n", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--evidence_method", type=str, default="grad_x_input", choices=["grad_x_input", "integrated_gradients"])
    parser.add_argument("--ig_steps", type=int, default=16)
    
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    # Reproducibility
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
    
    # Load Model
    logger.info("Loading resource...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(args.checkpoint, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(args.checkpoint, local_files_only=True)
    except:
        tokenizer = AutoTokenizer.from_pretrained(args.checkpoint)
        model = AutoModelForSequenceClassification.from_pretrained(args.checkpoint)
        
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    
    with open(args.temperature_json) as f:
        temp = json.load(f).get("temperature", 1.0)
    with open(args.label_map) as f:
        l2i = json.load(f)
        if isinstance(l2i, list): l2i = {l:i for i,l in enumerate(sorted(l2i))}
        id2label = {v:k for k,v in l2i.items()}
        
    # Load Data
    data_map = {}
    with open(args.dataset_file) as f:
        for line in f:
            item = json.loads(line)
            data_map[item["example_id"]] = item
            
    preds = []
    with open(args.preds_file) as f:
        for line in f:
            preds.append(json.loads(line))
            
    if args.sample_n < len(preds):
        preds = random.sample(preds, args.sample_n)
        
    logger.info(f"Auditing {len(preds)} examples... Method: {args.evidence_method}")
    
    audit_results = []
    
    for item in tqdm(preds):
        eid = item["example_id"]
        raw_text = data_map[eid]["text"]
        
        # Pred
        probs = item["probs"]
        pred_idx = int(np.argmax(probs))
        label_name = id2label[pred_idx]
        
        # Sanitize
        import re
        text_clean = raw_text
        text_clean = re.sub(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", "", text_clean)
        text_clean = re.sub(r"/?r/\w+", "", text_clean, flags=re.IGNORECASE)
        text_clean = " ".join(text_clean.split())
        
        try:
            # 1. Evidence
            attrs = compute_attributions(
                model, tokenizer, text_clean, pred_idx, 
                method=args.evidence_method, ig_steps=args.ig_steps, device=device
            )
            spans = extract_spans(attrs, text_clean, k=12, max_spans=3)
            
            if not spans: continue
            
            # 2. Individual Occlusion (Sensitivity)
            # Baseline: Full text prob
            # Note: verify_faithfulness returns p_full
            # We call it once to get p_full
            base_check = verify_faithfulness(model, tokenizer, text_clean, [], pred_idx, temperature=temp, device=device)
            p_full = base_check["p_full"]
            
            span_deltas = []
            for s in spans:
                # Mask just this span
                res = verify_faithfulness(model, tokenizer, text_clean, [s], pred_idx, temperature=temp, device=device)
                delta = p_full - res["p_masked"]
                span_deltas.append(delta)
                
            # 3. Union Occlusion (Sufficiency/Faithfulness)
            res_union = verify_faithfulness(model, tokenizer, text_clean, spans, pred_idx, temperature=temp, device=device)
            delta_union = p_full - res_union["p_masked"]
            
            # 4. Random Baseline (Control)
            lengths = [s["end"] - s["start"] for s in spans]
            rand_spans = generate_random_spans(text_clean, len(spans), lengths)
            
            res_rand = verify_faithfulness(model, tokenizer, text_clean, rand_spans, pred_idx, temperature=temp, device=device)
            delta_rand = p_full - res_rand["p_masked"]
            
            audit_results.append({
                "example_id": eid,
                "label": label_name,
                "p_full": p_full,
                "span_deltas": span_deltas,
                "delta_union": delta_union,
                "delta_random": delta_rand,
                "dominance_union": delta_union > delta_rand
            })
            
        except Exception as e:
            logger.warning(f"Error {eid}: {e}")
            
    # Report
    deltas = [r["delta_union"] for r in audit_results]
    rand_deltas = [r["delta_random"] for r in audit_results]
    dominance = np.mean([1 if r["dominance_union"] else 0 for r in audit_results])
    
    stats = {
        "n": len(audit_results),
        "mean_delta_union": float(np.mean(deltas)),
        "mean_delta_random": float(np.mean(rand_deltas)),
        "dominance_rate": float(dominance)
    }
    
    with open(args.out_dir / "occlusion_audit.json", "w") as f:
        json.dump(stats, f, indent=2)
        
    with open(args.out_dir / "occlusion_audit.md", "w") as f:
        f.write("# Occlusion Audit Report\n")
        f.write(f"- Method: {args.evidence_method}\n")
        f.write(f"- N: {stats['n']}\n")
        f.write(f"- Mean Delta (Evidence): {stats['mean_delta_union']:.4f}\n")
        f.write(f"- Mean Delta (Random): {stats['mean_delta_random']:.4f}\n")
        f.write(f"- Dominance Rate: {stats['dominance_rate']:.2%}\n")
        
    logger.info(f"Audit complete: {args.out_dir}")

if __name__ == "__main__":
    main()
