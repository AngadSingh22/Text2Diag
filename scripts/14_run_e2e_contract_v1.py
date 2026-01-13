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

from text2diag.explain.dependency import build_dependency_graph

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(msg)s")
logger = logging.getLogger(__name__)

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

import hashlib

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
    ig_steps=16,
    include_dependency_graph=False,
    skip_sanitization=False,
    provided_example_id=None
):
    # 1. Preprocess
    if skip_sanitization:
        text_clean = text_raw
        rules_applied = ["skipped"]
        audit_meta = {"version": "skipped", "sha256": "none"}
    else:
        text_clean, rules_applied, audit_meta = sanitize_text(text_raw, **sanitize_config)
    
    # 2. Forward Pass
    inputs = tokenizer(text_clean, return_tensors="pt", truncation=True, max_length=max_len).to(device)
    with torch.no_grad():
        logits = model(**inputs).logits
        
    logits = logits[0].cpu().numpy()
    
    # 3. Calibration & Decisions
    probs_cal = sigmoid(logits / temperature)
    
    sorted_indices = np.argsort(probs_cal)[::-1]
    
    label_objs = []
    label_probs_map = {}
    active_labels = []
    
    # Process all labels
    for idx in range(len(id2label)):
        name = id2label[idx]
        p = float(probs_cal[idx])
        
        # Threshold Logic & Provenance
        if name in thresholds:
            t = thresholds[name]
            src = "per_label"
        elif "global" in thresholds:
            t = thresholds["global"]
            src = "global"
        else:
            t = 0.5
            src = "default_0.5"
            
        d = 1 if p >= t else 0
        label_probs_map[name] = p
        
        if d == 1:
            active_labels.append(name)
        
        lbl_obj = {
            "name": name,
            "prob_calibrated": round(p, 4),
            "decision": d,
            "threshold_used": t,
            "threshold_source": src,
            "evidence_spans": [],
            "faithfulness": {"delta": 0.0, "is_faithful": False},
            "evidence_meta": {"method": evidence_method}
        }
        if evidence_method == "integrated_gradients":
            lbl_obj["evidence_meta"]["ig_steps"] = ig_steps
            
        label_objs.append(lbl_obj)
        
    # 4. Explain Top-K (Top-2)
    top_k_indices = sorted_indices[:2]
    EVIDENCE_MIN_PROB = 0.10
    
    for idx in top_k_indices:
        name = id2label[idx]
        lbl_obj = next(l for l in label_objs if l["name"] == name)
        
        # SKIP if prob too low
        if lbl_obj["prob_calibrated"] < EVIDENCE_MIN_PROB:
            lbl_obj["evidence_meta"]["skipped_reason"] = "low_prob"
            lbl_obj["evidence_meta"]["min_prob"] = EVIDENCE_MIN_PROB
            lbl_obj["faithfulness"]["faithfulness_status"] = "skipped_low_prob"
            continue
            
        try:
            attrs = compute_attributions(
                model, tokenizer, text_clean, int(idx), 
                method=evidence_method, device=device, max_len=max_len, ig_steps=ig_steps
            )
            spans = extract_spans(attrs, text_clean, k=12, max_spans=3)
            
            if spans:
                faith = verify_faithfulness(model, tokenizer, text_clean, spans, int(idx), temperature=temperature, device=device)
                
                lbl_obj["evidence_spans"] = spans
                lbl_obj["faithfulness"] = faith
            else:
                 lbl_obj["faithfulness"]["faithfulness_status"] = "skipped_no_spans"
                 
        except Exception as e:
            logger.warning(f"Explan error for {name}: {e}")
            
    # 5. Example ID Logic
    if provided_example_id:
        final_eid = provided_example_id
    else:
        # Deterministic fallback: "gen_" + first 12 chars of sha256(text_clean)
        # We assume audit_meta might have it, or we compute valid one
        if "sha256" in audit_meta and audit_meta["sha256"] != "none":
            h = audit_meta["sha256"]
        else:
            h = hashlib.sha256(text_clean.encode("utf-8")).hexdigest()
        final_eid = f"gen_{h[:12]}"

    # Build Output Object
    out = {
        "version": "v1",
        "example_id": final_eid, 
        "model_info": {
            "model_name": "distilbert-base",
            "checkpoint": str(model.name_or_path),
            "max_len": max_len,
            "window_size": 3
        },
        "calibration": {
            "method": "temperature_scaling",
            "temperature": temperature,
            "timestamp": "2026-01-10"
        },
        "labels": label_objs,
        "abstain": {
            "is_abstain": False,
            "reasons": []
        },
        "meta": {
            "created_at": "2026-01-14",
            "preprocessing": {
                "sanitized": not skip_sanitization,
                "rules_applied": rules_applied,
                "sanitization_audit": audit_meta
            }
        }
    }
    
    if include_dependency_graph:
        # Emit both active and topk graphs
        # Active: decision=1
        out["dependency_graph_active"] = build_dependency_graph(active_labels, label_probs_map, mode="active")
        
        # Top-K: top 3
        out["dependency_graph_topk"] = build_dependency_graph(active_labels, label_probs_map, mode="topk", k=3)
        
        # Backward compatibility shim
        out["dependency_graph"] = out["dependency_graph_topk"]
    
    # 6. Validate & Repair
    ok, errors = validate_output(out)
    if not ok:
        out, repaired, rem_errors = repair_output(out, errors)
        if rem_errors:
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
    parser.add_argument("--include_dependency_graph", action="store_true", help="Generate dependency graph")
    parser.add_argument("--skip_sanitization", action="store_true", help="Skip internal sanitization")
    
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
            sanitize_config, args.max_len, device,
            include_dependency_graph=args.include_dependency_graph,
            skip_sanitization=args.skip_sanitization
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
                    sanitize_config, args.max_len, device,
                    include_dependency_graph=args.include_dependency_graph,
                    skip_sanitization=args.skip_sanitization,
                    provided_example_id=eid
                )
                # out["example_id"] = eid # Handled inside now
                f_out.write(json.dumps(out) + "\n")
        logger.info(f"Batch complete. Output: {args.out_jsonl}")
    else:
        logger.error("Must provide --text or --input_jsonl")
        sys.exit(1)

if __name__ == "__main__":
    main()
