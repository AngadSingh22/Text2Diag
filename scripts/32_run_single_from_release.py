#!/usr/bin/env python3
"""
Week 6 Ad-hoc Single Runner.
Runs a single input using the frozen Week 6 release configuration.
"""
import sys
import argparse
import json
import logging
from pathlib import Path
import torch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from text2diag.release.load_release_config import load_release_config

# Import E2E Runner Logic using importlib
import importlib.util
spec = importlib.util.spec_from_file_location("runner_v1", str(Path(__file__).parent / "14_run_e2e_contract_v1.py"))
runner_v1 = importlib.util.module_from_spec(spec)
sys.modules["runner_v1"] = runner_v1
spec.loader.exec_module(runner_v1)
predict_example = runner_v1.predict_example

from transformers import AutoTokenizer, AutoModelForSequenceClassification

logging.basicConfig(level=logging.ERROR) # Quiet logs for cleaner stdout summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release_config", default="configs/release/week6_freeze.json", help="Path to release config")
    parser.add_argument("--text", required=True, help="Input text")
    parser.add_argument("--out_file", default="results/ad_hoc/out.json", help="Output JSON file")
    args = parser.parse_args()
    
    # 1. Load Config
    cfg = load_release_config(args.release_config)
    
    # 2. Load Resources
    # Label Map
    with open(cfg["paths"]["label_map"]) as f:
        l2i = json.load(f)
    if isinstance(l2i, list): l2i = {l:i for i,l in enumerate(sorted(l2i))}
    id2label = {v:k for k,v in l2i.items()}
    
    # Model/Tokenizer
    checkpoint = cfg["paths"]["checkpoint"]
    tokenizer = AutoTokenizer.from_pretrained(checkpoint, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(checkpoint, local_files_only=True)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    
    # Calibration & Thresholds
    with open(cfg["paths"]["temperature_json"]) as f:
        temp = json.load(f).get("temperature", 1.0)
        
    thresholds = {"global": 0.5}
    with open(cfg["paths"]["thresholds_json"]) as f:
        thresholds.update(json.load(f))
        
    # 3. Run Inference
    out = predict_example(
        model=model,
        tokenizer=tokenizer,
        text_raw=args.text,
        id2label=id2label,
        thresholds=thresholds,
        temperature=temp,
        sanitize_config=cfg["sanitization"]["config"],
        max_len=cfg["model"]["max_len"],
        device=device,
        evidence_method=cfg["inference"]["evidence_method"],
        ig_steps=cfg["inference"]["ig_steps"],
        include_dependency_graph=cfg["inference"]["include_dependency_graph"],
        skip_sanitization=not cfg["sanitization"]["enabled"]
    )
    
    # 4. Save Output
    out_path = Path(args.out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
        
    # 5. Print Summary
    top_label = "None"
    top_score = 0.0
    
    # Find active label with highest score
    active_labels = [l for l in out["labels"] if l["decision"] == 1]
    if active_labels:
        best = max(active_labels, key=lambda x: x["prob_calibrated"])
        top_label = best["name"]
        top_score = best["prob_calibrated"]
    else:
        # Fallback to highest prob even if not active
        best = max(out["labels"], key=lambda x: x["prob_calibrated"])
        top_score = best["prob_calibrated"]
        
    status = "ABSTAIN" if out["abstain"]["is_abstain"] else "OK"
    has_graph = "dependency_graph" in out
    
    print("=== Single Run Summary ===")
    print(f"Status: {status}")
    print(f"Top Label: {top_label} (Score: {top_score:.4f})")
    print(f"Graph Included: {has_graph}")
    print(f"Output Saved: {out_path}")

if __name__ == "__main__":
    main()
