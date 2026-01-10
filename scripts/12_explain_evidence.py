#!/usr/bin/env python3
"""
Week 4: Evidence Extraction Runner.
Computes gradients, extracts spans, and verifies faithfulness via deletion.
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

# Setup logging
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

def main():
    parser = argparse.ArgumentParser(description="Week 4: Evidence Extraction")
    parser.add_argument("--checkpoint", type=Path, required=True, help="Path to model checkpoint")
    parser.add_argument("--temperature_json", type=Path, required=True, help="Path to calibration scaling json")
    parser.add_argument("--label_map", type=Path, required=True, help="Path to label2id.json")
    parser.add_argument("--dataset_file", type=Path, required=True, help="Path to dataset jsonl (with text)")
    parser.add_argument("--preds_file", type=Path, required=True, help="Path to predictions jsonl (for selection)")
    parser.add_argument("--out_dir", type=Path, required=True, help="Output directory")
    parser.add_argument("--top_labels", type=int, default=2, help="Number of labels to explain per example")
    parser.add_argument("--sample_n", type=int, default=500, help="Number of examples to process")
    parser.add_argument("--seed", type=int, default=1337)
    
    args = parser.parse_args()
    
    # 0. Reproducibility
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Load Resources
    logger.info(f"Loading model from {args.checkpoint}")
    try:
        # Use local_files_only to behave nicely on Windows/Airgapped
        tokenizer = AutoTokenizer.from_pretrained(str(args.checkpoint), local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(str(args.checkpoint), local_files_only=True)
    except Exception as e:
        logger.error(f"Failed to load model locally: {e}. Trying without local_files_only...")
        tokenizer = AutoTokenizer.from_pretrained(str(args.checkpoint))
        model = AutoModelForSequenceClassification.from_pretrained(str(args.checkpoint))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")
    model.to(device)
    model.eval()
    
    # Load Labels
    logger.info(f"Loading labels from {args.label_map}")
    with open(args.label_map, "r") as f:
        label2id = json.load(f)
    if isinstance(label2id, list):
        label2id = {l: i for i, l in enumerate(sorted(label2id))}
    id2label = {int(v): k for k, v in label2id.items()}
    
    # Load Temperature
    logger.info(f"Loading temperature from {args.temperature_json}")
    with open(args.temperature_json, "r") as f:
        temp_data = json.load(f)
    temperature = temp_data.get("temperature", 1.0)
    logger.info(f"Calibration Temperature: {temperature}")
    
    # 2. Load Data
    logger.info("Loading dataset and predictions...")
    dataset_records = load_jsonl(args.dataset_file)
    # create index
    dataset_map = {r["example_id"]: r for r in dataset_records if "example_id" in r}
    
    preds_records = load_jsonl(args.preds_file)
    valid_preds = [p for p in preds_records if p.get("example_id") in dataset_map]
    
    if len(valid_preds) == 0:
        logger.error("No matching example_ids found between dataset and preds!")
        sys.exit(1)
        
    # 3. Sample
    if args.sample_n < len(valid_preds):
        logger.info(f"Sampling {args.sample_n} examples from {len(valid_preds)}")
        sampled_preds = random.sample(valid_preds, args.sample_n)
    else:
        logger.info(f"Using all {len(valid_preds)} examples")
        sampled_preds = valid_preds
        
    # 4. Run Pipeline
    results = []
    
    logger.info("Running Evidence Extraction Pipeline...")
    for item in tqdm(sampled_preds):
        eid = item["example_id"]
        raw_text = dataset_map[eid]["text"]
        
        # Get probs to decide which labels to explain
        if "probs" not in item:
            continue
        probs = item["probs"]
        
        # Get top-K labels
        top_indices = np.argsort(probs)[::-1][:args.top_labels]
        
        for idx in top_indices:
            label_idx = int(idx)
            label_name = id2label.get(label_idx, f"Label_{label_idx}")
            
            try:
                # A. Attribution
                # Hardcoded max_len to 512 as per model baseline
                MAX_LEN = 512 
                attrs = compute_input_gradients(model, tokenizer, raw_text, label_idx, device=device, max_len=MAX_LEN)
                
                # B. Spans
                spans = extract_spans(attrs, raw_text, k=12, max_spans=3)
                
                # C. Faithfulness
                faith = verify_faithfulness(model, tokenizer, raw_text, spans, label_idx, temperature=temperature, device=device)
                
                # Metadata
                # Assuming data in dataset_file IS the inference-ready text (sanitized if needed)
                # We record this assumption.
                meta = {
                    "max_len": MAX_LEN,
                    "sanitization_applied": "implicit_in_dataset_file", 
                    "input_length_chars": len(raw_text)
                }
                
                # Record
                res = {
                    "example_id": eid,
                    "label": label_name,
                    "prob_calibrated": faith["p_full"], # Use realtime computation
                    "faithfulness": faith,
                    "metadata": meta,
                    "spans": [
                        {
                            "start": s["start"], 
                            "end": s["end"], 
                            "score": round(float(s["score"]), 4), 
                            "snippet": s["snippet"]
                        }
                        for s in spans
                    ]
                }
                results.append(res)
                
            except Exception as e:
                logger.warning(f"Error processing {eid} label {label_name}: {e}")
                continue
                
    # 5. Save Outputs
    out_path = args.out_dir / "evidence.jsonl"
    logger.info(f"Writing results to {out_path}")
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
            
    # 6. Report
    if not results:
        logger.warning("No results generated!")
        return

    pass_count = sum(1 for r in results if r["faithfulness"]["is_faithful"])
    total = len(results)
    pass_rate = pass_count / total
    
    # Delta Stats
    deltas = [r["faithfulness"]["delta"] for r in results]
    delta_stats = {
        "mean": float(np.mean(deltas)),
        "median": float(np.median(deltas)),
        "p90": float(np.percentile(deltas, 90)),
        "min": float(np.min(deltas)),
        "max": float(np.max(deltas))
    }
    
    report = {
        "sample_size": args.sample_n,
        "total_explanations": total,
        "pass_count": pass_count,
        "pass_rate": round(pass_rate, 4),
        "delta_stats": {k: round(v, 4) for k, v in delta_stats.items()}
    }
    
    report_path = args.out_dir / "evidence_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
        
    # Markdown Report
    md_path = args.out_dir / "evidence_report.md"
    with open(md_path, "w") as f:
        f.write(f"# Week 4 Evidence Report\n\n")
        f.write(f"- **Sample Size**: {args.sample_n}\n")
        f.write(f"- **Explanations Generated**: {total}\n")
        f.write(f"- **Faithfulness Pass Rate**: {pass_rate:.2%} ({pass_count}/{total})\n\n")
        f.write(f"### Delta Distribution (Prob Drop)\n")
        f.write(f"- Mean: {delta_stats['mean']:.4f}\n")
        f.write(f"- Median: {delta_stats['median']:.4f}\n")
        f.write(f"- Max Drop: {delta_stats['max']:.4f}\n")
    
    logger.info(f"Report saved to {md_path}")

if __name__ == "__main__":
    main()
