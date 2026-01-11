#!/usr/bin/env python3
"""
Scripts/22_rmhd_leakage_report.py
Computes leakage metrics for external dataset validation.
"""
import sys
import argparse
import json
import logging
import re
from pathlib import Path
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from text2diag.preprocess.sanitize_external import sanitize_text_strict, LABEL_SYNONYMS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def count_hits(text, patterns):
    count = 0
    text_lower = text.lower()
    for p in patterns:
        if re.search(r'\b' + re.escape(p) + r'\b', text_lower):
            count += 1
    return count

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", type=Path, required=True, help="Raw JSONL")
    parser.add_argument("--out_dir", type=Path, required=True)
    args = parser.parse_args()
    
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    # regex for url/reddit
    url_re = re.compile(r"http[s]?://")
    reddit_re = re.compile(r"/?r/\w+")
    
    stats = {
        "total": 0,
        "url_hits_before": 0,
        "reddit_hits_before": 0,
        "label_hits_before": {k: 0 for k in LABEL_SYNONYMS},
        "url_hits_after": 0,
        "reddit_hits_after": 0,
        "label_hits_after": {k: 0 for k in LABEL_SYNONYMS}
    }
    
    with open(args.input_file, "r", encoding="utf-8") as f:
        for line in tqdm(f):
            if not line.strip(): continue
            row = json.loads(line)
            text_raw = row.get("text", "")
            if not text_raw: continue
            
            stats["total"] += 1
            
            # BEFORE
            if url_re.search(text_raw): stats["url_hits_before"] += 1
            if reddit_re.search(text_raw): stats["reddit_hits_before"] += 1
            
            for label, syns in LABEL_SYNONYMS.items():
                if count_hits(text_raw, syns) > 0:
                    stats["label_hits_before"][label] += 1
                    
            # SANITIZE
            text_clean = sanitize_text_strict(text_raw)
            
            # AFTER
            if url_re.search(text_clean): stats["url_hits_after"] += 1
            if reddit_re.search(text_clean): stats["reddit_hits_after"] += 1
             
            for label, syns in LABEL_SYNONYMS.items():
                if count_hits(text_clean, syns) > 0:
                    stats["label_hits_after"][label] += 1
                    
    # Save Report
    with open(args.out_dir / "leakage_report.json", "w") as f:
        json.dump(stats, f, indent=2)
        
    # MD
    with open(args.out_dir / "leakage_report.md", "w") as f:
        f.write("# Leakage Report (RMHD)\n\n")
        f.write(f"Total Examples: {stats['total']}\n\n")
        f.write("| Metric | Before | After | Reduction |\n")
        f.write("|---|---|---|---|\n")
        f.write(f"| URL Hits | {stats['url_hits_before']} | {stats['url_hits_after']} | - |\n")
        f.write(f"| Reddit Hits | {stats['reddit_hits_before']} | {stats['reddit_hits_after']} | - |\n")
        for k in stats["label_hits_before"]:
            b = stats["label_hits_before"][k]
            a = stats["label_hits_after"][k]
            f.write(f"| Label: {k} | {b} | {a} | - |\n")

if __name__ == "__main__":
    main()
