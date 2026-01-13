#!/usr/bin/env python3
"""
Week 6 Freeze Runner.
Executing the canonical, reproducible evaluation run.
"""
import sys
import argparse
import json
import logging
import hashlib
import torch
import numpy as np
import random
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from text2diag.release.load_release_config import load_release_config
from text2diag.contract.schema_v1 import SCHEMA_V1 # Ensure schema is loaded
from text2diag.text.sanitize import sanitize_text

# Import E2E Runner Logic (reuse predict_example but wrap for strict config)
# We import the main run logic or reimplement the loop to ensure strict config adherence
# It is safer to import the function to avoid code duplication, but we must control the args strictly.
# from scripts_14_run_e2e_contract_v1 import predict_example # Removed invalid import 
# Note: we need to handle the import name properly. 
# Since 14_run... has a digit, it might not be importable directly nicely.
# Let's use importlib or just reimplement the batch loop which is simple.
# Reimplementing loop is safer to guarantee we don't accidentally use default args from script 14.
# We will reuse the `predict_example` logic by importing it carefully.

import importlib.util
spec = importlib.util.spec_from_file_location("runner_v1", str(Path(__file__).parent / "14_run_e2e_contract_v1.py"))
runner_v1 = importlib.util.module_from_spec(spec)
sys.modules["runner_v1"] = runner_v1
spec.loader.exec_module(runner_v1)
predict_example = runner_v1.predict_example

from transformers import AutoTokenizer, AutoModelForSequenceClassification

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(msg)s")
logger = logging.getLogger(__name__)

def set_seeds(seed_py, seed_np, seed_torch):
    random.seed(seed_py)
    np.random.seed(seed_np)
    torch.manual_seed(seed_torch)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed_torch)
    logger.info(f"Seeds set: Py={seed_py}, NP={seed_np}, Torch={seed_torch}")

def compute_file_hash(path):
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release_config", required=True, help="Path to Week 6 Freeze JSON config")
    parser.add_argument("--out_dir", default="results/week6_frozen", help="Output directory")
    parser.add_argument("--sample_n", type=int, help="Limit examples for smoke testing")
    args = parser.parse_args()
    
    # 1. Load Config
    cfg = load_release_config(args.release_config)
    
    # 2. Setup Output
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. Set Determinism
    set_seeds(
        cfg["reproducibility"]["seed_python"],
        cfg["reproducibility"]["seed_numpy"],
        cfg["reproducibility"]["seed_torch"]
    )
    
    # 4. Load Resources
    # Load Label Map
    with open(cfg["paths"]["label_map"]) as f:
        l2i = json.load(f)
    if isinstance(l2i, list): l2i = {l:i for i,l in enumerate(sorted(l2i))}
    id2label = {v:k for k,v in l2i.items()}
    
    # Load Model/Tokenizer
    checkpoint = cfg["paths"]["checkpoint"]
    tokenizer = AutoTokenizer.from_pretrained(checkpoint, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(checkpoint, local_files_only=True)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    
    # Load Calibration & Thresholds
    with open(cfg["paths"]["temperature_json"]) as f:
        temp = json.load(f).get("temperature", 1.0)
        
    thresholds = {"global": 0.5}
    with open(cfg["paths"]["thresholds_json"]) as f:
        thresholds.update(json.load(f))
        
    # 5. Run Batch Inference (Val + Test)
    # Only assuming we have processed data in known locations or we use the config to find it?
    # Week 1 data is at data/processed/reddit_mh_sanitized/ (based on recent RUNLOG)
    # Let's assume standard paths or verify. The config pointed to label_map in data/processed/reddit_mh_sanitized/
    # So we look there.
    data_dir = Path(cfg["paths"]["label_map"]).parent
    
    manifest = {}
    
    for split in ["val", "test"]:
        input_file = data_dir / f"{split}.jsonl"
        output_file = out_dir / f"preds_{split}.jsonl"
        
        logger.info(f"Processing {split} from {input_file}")
        
        count = 0
        with open(input_file, "r") as f_in, open(output_file, "w") as f_out:
            for line in f_in:
                if not line.strip(): continue
                if args.sample_n and count >= args.sample_n: break
                
                item = json.loads(line)
                text = item.get("text", "")
                eid = item.get("example_id", None)
                
                # Call E2E Runner Logic
                # Mapped from Config
                out = predict_example(
                    model=model,
                    tokenizer=tokenizer,
                    text_raw=text,
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
                out["example_id"] = eid
                
                f_out.write(json.dumps(out) + "\n")
                count += 1
                
        logger.info(f"Finished {split}: {count} examples.")
        
        # Manifest
        manifest[f"preds_{split}"] = {
            "path": str(output_file),
            "sha256": compute_file_hash(output_file)
        }
        
    # 6. Save Manifest
    manifest_path = out_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        
    logger.info(f"Freeze run complete. Artifacts in {out_dir}")
    logger.info(f"Manifest saved to {manifest_path}")

if __name__ == "__main__":
    main()
