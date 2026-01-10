#!/usr/bin/env python3
"""
Week 5 Coverage: End-to-End Runner (Schema V1).
Production entrypoint for Text2Diag text classification.
"""
import sys
from pathlib import Path
import logging
import argparse
import json
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from text2diag.text.sanitize import sanitize_text
from text2diag.explain.attribution import compute_attributions
from text2diag.explain.spans import extract_spans
from text2diag.explain.faithfulness import verify_faithfulness
from text2diag.contract.schema_v1 import SCHEMA_V1
from text2diag.contract.validate import validate_output
from text2diag.contract.repair import repair_output
from text2diag.decision.abstain import decide_abstain

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(msg)s")
logger = logging.getLogger(__name__)

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def predict_example(
    model, 
    tokenizer, 
    text_raw, 
    id2label, 
    thresholds, 
    temperature, 
    sanitize_config, 
    max_len, 
    device,
    evidence_method="grad_x_input",
    ig_steps=16
):
    # 1. Preprocess
    text_clean, rules_applied = sanitize_text(text_raw, **sanitize_config)
    
    # 2. Forward Pass
    inputs = tokenizer(text_clean, return_tensors="pt", truncation=True, max_length=max_len).to(device)
    with torch.no_grad():
        logits = model(**inputs).logits
        
    logits = logits[0].cpu().numpy()
    
    # 3. Calibration & Decisions
    probs_cal = sigmoid(logits / temperature)
    
    labels_out = []
    
    # We explain top-2 predicted labels if they exceed some minimal floor (e.g. 0.1)
    # Or just explain predicted ones (decision=1).
    # Logic: Explain top-2 regardless, to give context.
    sorted_indices = np.argsort(probs_cal)[::-1]
    
    label_objs = []
    label_probs_map = {}
    
    # Process all labels
    for idx in range(len(id2label)):
        name = id2label[idx]
        p = float(probs_cal[idx])
        t = thresholds.get(name, thresholds.get("global", 0.5))
        d = 1 if p >= t else 0
        label_probs_map[name] = p
        
        lbl_obj = {
            "name": name,
            "prob_calibrated": round(p, 4),
            "decision": d,
            "threshold_used": t,
            "evidence_spans": [],
            "faithfulness": {"delta": 0.0, "is_faithful": False},
            "evidence_meta": {"method": evidence_method} # Optional W5.1
        }
        if evidence_method == "integrated_gradients":
            lbl_obj["evidence_meta"]["ig_steps"] = ig_steps
            
        label_objs.append(lbl_obj)
        
    # 4. Explain Top-K (Top-2)
    # We attach explanations to the label objects we just created
    top_k_indices = sorted_indices[:2]
    
    for idx in top_k_indices:
        # Find the label object
        name = id2label[idx]
        lbl_idx_in_list = next(i for i, l in enumerate(label_objs) if l["name"] == name)
        
        # Explain
        try:
            attrs = compute_attributions(
                model, tokenizer, text_clean, int(idx), 
                method=evidence_method, device=device, max_len=max_len, ig_steps=ig_steps
            )
            spans = extract_spans(attrs, text_clean, k=12, max_spans=3)
            
            if spans:
                faith = verify_faithfulness(model, tokenizer, text_clean, spans, int(idx), temperature=temperature, device=device)
                
                label_objs[lbl_idx_in_list]["evidence_spans"] = spans
                label_objs[lbl_idx_in_list]["faithfulness"] = {
                    "delta": faith["delta"],
                    "is_faithful": faith["is_faithful"]
                }
        except Exception as e:
            logger.warning(f"Explan error for {name}: {e}")
            
    # 5. Build Output Object
    out = {
        "version": "v1",
        "example_id": None, # Filled by caller
        "model_info": {
            "model_name": "distilbert-base",
            "checkpoint": str(model.name_or_path),
            "max_len": max_len,
            "window_size": 3 # Assumption for now
        },
        "calibration": {
            "method": "temperature_scaling",
            "temperature": temperature,
            "timestamp": "2026-01-10" # Placeholder
        },
        "labels": label_objs,
        "abstain": {
            "is_abstain": False,
            "reasons": []
        },
        "meta": {
            "created_at": "2026-01-10",
            "preprocessing": {
                "sanitized": True,
                "rules_applied": rules_applied
            }
        }
    }
    
    # 6. Validate & Repair
    ok, errors = validate_output(out)
    if not ok:
        out, repaired, rem_errors = repair_output(out, errors)
        if rem_errors:
             # If strictly failing, we abstain
             out["abstain"]["is_abstain"] = True
             out["abstain"]["reasons"].extend([f"Contract Error: {e}" for e in rem_errors])
             
    # 7. Decide Abstain (Logic Layer)
    is_abs, reasons = decide_abstain(
        label_probs_map, id2label, 
        contract_ok=(len(out["abstain"]["reasons"]) == 0),
        text_len=len(text_clean)
    )
    if is_abs:
        out["abstain"]["is_abstain"] = True
        out["abstain"]["reasons"].extend(reasons)
        
    return out

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--temperature_json", required=True)
    parser.add_argument("--label_map", required=True)
    parser.add_argument("--thresholds_json", help="Optional per-label thresholds")
    parser.add_argument("--text", type=str, help="Single text input")
    parser.add_argument("--input_jsonl", type=Path, help="Batch input")
    parser.add_argument("--out_jsonl", type=Path, default="output.jsonl")
    parser.add_argument("--max_len", type=int, default=512)
    parser.add_argument("--output_file", type=Path, help="Output file for single text mode")
    
    args = parser.parse_args()
    
    # Load Resources
    try:
        tokenizer = AutoTokenizer.from_pretrained(args.checkpoint, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(args.checkpoint, local_files_only=True)
    except:
        tokenizer = AutoTokenizer.from_pretrained(args.checkpoint)
        model = AutoModelForSequenceClassification.from_pretrained(args.checkpoint)
        
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    
    with open(args.label_map) as f:
        l2i = json.load(f)
    if isinstance(l2i, list): l2i = {l:i for i,l in enumerate(sorted(l2i))}
    id2label = {v:k for k,v in l2i.items()}
    
    with open(args.temperature_json) as f:
        temp = json.load(f).get("temperature", 1.0)
        
    thresholds = {"global": 0.5}
    if args.thresholds_json:
        with open(args.thresholds_json) as f:
            thresholds.update(json.load(f))
            
    sanitize_config = {
        "strip_urls": True,
        "strip_reddit_refs": True,
        "mask_diagnosis_words": False
    }
    
    # Mode Switch
    if args.text is not None:
        # Single Mode
        out = predict_example(
            model, tokenizer, args.text, id2label, thresholds, temp, 
            sanitize_config, args.max_len, device
        )
        if args.output_file:
            with open(args.output_file, "w") as f:
                json.dump(out, f, indent=2)
        else:
            print(json.dumps(out, indent=2))
        
    elif args.input_jsonl:
        # Batch Mode
        with open(args.input_jsonl) as f_in, open(args.out_jsonl, "w") as f_out:
            for line in f_in:
                if not line.strip(): continue
                item = json.loads(line)
                text = item.get("text", "")
                eid = item.get("example_id", None)
                
                out = predict_example(
                    model, tokenizer, text, id2label, thresholds, temp, 
                    sanitize_config, args.max_len, device
                )
                out["example_id"] = eid
                f_out.write(json.dumps(out) + "\n")
        logger.info(f"Batch complete. Output: {args.out_jsonl}")
    else:
        logger.error("Must provide --text or --input_jsonl")
        sys.exit(1)

if __name__ == "__main__":
    main()
