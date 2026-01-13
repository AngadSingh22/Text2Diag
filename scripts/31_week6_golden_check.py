#!/usr/bin/env python3
"""
Week 6 Golden Regression Check.
Runs inputs from data/golden/week6_inputs.jsonl using the release config,
computes hashes of the outputs, and compares against data/golden/golden_hashes.json.
"""
import sys
import argparse
import json
import logging
import hashlib
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from text2diag.release.load_release_config import load_release_config
# Use importlib to import the freeze runner logic to avoid code duplication 
# logic is in scripts/30_week6_freeze_run.py but main there is a script.
# We'll re-import predict_example from the E2E runner (via importlib wrapper used in 30)
# actually, better to import directly from script 14 wrapper like we did in script 30.

import importlib.util
spec = importlib.util.spec_from_file_location("runner_v1", str(Path(__file__).parent / "14_run_e2e_contract_v1.py"))
runner_v1 = importlib.util.module_from_spec(spec)
sys.modules["runner_v1"] = runner_v1
spec.loader.exec_module(runner_v1)
predict_example = runner_v1.predict_example

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(msg)s")
logger = logging.getLogger(__name__)

def compute_obj_hash(obj):
    # Deterministic JSON dump
    s = json.dumps(obj, sort_keys=True)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release_config", required=True)
    parser.add_argument("--golden_inputs", default="data/golden/week6_inputs.jsonl")
    parser.add_argument("--golden_hashes", default="data/golden/week6_hashes.json")
    parser.add_argument("--generate_hashes", action="store_true", help="Overwrite the golden hash file")
    args = parser.parse_args()
    
    cfg = load_release_config(args.release_config)
    
    # Load Model
    checkpoint = cfg["paths"]["checkpoint"]
    tokenizer = AutoTokenizer.from_pretrained(checkpoint, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(checkpoint, local_files_only=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    
    # Load Configs
    with open(cfg["paths"]["label_map"]) as f:
        l2i = json.load(f)
    if isinstance(l2i, list): l2i = {l:i for i,l in enumerate(sorted(l2i))}
    id2label = {v:k for k,v in l2i.items()}
    
    with open(cfg["paths"]["temperature_json"]) as f:
        temp = json.load(f).get("temperature", 1.0)
        
    thresholds = {"global": 0.5}
    with open(cfg["paths"]["thresholds_json"]) as f:
        thresholds.update(json.load(f))
        
    # Process Golden Inputs
    hashes = {}
    
    if not Path(args.golden_inputs).exists():
        logger.error(f"Golden inputs not found: {args.golden_inputs}")
        sys.exit(1)
        
    logger.info(f"Running golden inputs from: {args.golden_inputs}")
    
    line_hashes = []
    
    with open(args.golden_inputs, "r") as f:
        for line in f:
            if not line.strip(): continue
            item = json.loads(line)
            eid = item["example_id"]
            
            out = predict_example(
                model=model,
                tokenizer=tokenizer,
                text_raw=item["text"],
                id2label=id2label,
                thresholds=thresholds,
                temperature=temp,
                sanitize_config=cfg["sanitization"]["config"],
                max_len=cfg["model"]["max_len"],
                device=device,
                evidence_method=cfg["inference"]["evidence_method"],
                ig_steps=cfg["inference"]["ig_steps"],
                include_dependency_graph=cfg["inference"]["include_dependency_graph"],
                skip_sanitization=not cfg["sanitization"]["enabled"],
                provided_example_id=eid
            )
            # out["example_id"] = eid # Handled inside
            
            # Remove timestamp for hashing stability
            if "meta" in out and "created_at" in out["meta"]:
                out["meta"]["created_at"] = "MASKED"
            if "calibration" in out and "timestamp" in out["calibration"]:
                out["calibration"]["timestamp"] = "MASKED"
                
            h = compute_obj_hash(out)
            line_hashes.append((eid, h))
            
    # Compute Master Hash
    master_hash_input = "".join([h for _, h in line_hashes])
    master_hash = hashlib.sha256(master_hash_input.encode("utf-8")).hexdigest()
    
    current_hashes = {
        "master_hash": master_hash,
        "examples": {eid: h for eid, h in line_hashes}
    }
    
    if args.generate_hashes:
        logger.info(f"Generating new golden hashes to {args.golden_hashes}")
        with open(args.golden_hashes, "w") as f:
            json.dump(current_hashes, f, indent=2)
        logger.info("Done.")
        return
        
    # Verify
    if not Path(args.golden_hashes).exists():
        logger.error(f"Golden hashes not found: {args.golden_hashes}. Run with --generate_hashes first.")
        sys.exit(1)
        
    with open(args.golden_hashes, "r") as f:
        expected_hashes = json.load(f)
        
    if current_hashes["master_hash"] == expected_hashes["master_hash"]:
        logger.info("Golden Regression PASSED. Hashes match.")
    else:
        logger.error("Golden Regression FAILED.")
        logger.error(f"Expected Master: {expected_hashes['master_hash']}")
        logger.error(f"Got Master:      {current_hashes['master_hash']}")
        # Diff
        for eid, h in current_hashes["examples"].items():
            exp = expected_hashes["examples"].get(eid)
            if h != exp:
                logger.error(f"Mismatch {eid}: Expected {exp}, Got {h}")
        sys.exit(1)

if __name__ == "__main__":
    main()
