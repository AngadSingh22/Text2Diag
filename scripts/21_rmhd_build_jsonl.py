"""
Scripts/21_rmhd_build_jsonl.py
Parses downloaded RMHD CSVs and builds a unified JSONL.
"""
import argparse
import pandas as pd
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_rmhd(data_dir, output_file, label_map_file, sample_n=None):
    with open(label_map_file) as f:
        label_map = json.load(f)
        
    # Invert map for quick lookup: {subreddit: [labels]}
    sub_to_labels = {}
    for lbl, subs in label_map.items():
        for s in subs:
            if s not in sub_to_labels:
                sub_to_labels[s] = []
            if lbl != "control" and lbl != "other":
                sub_to_labels[s].append(lbl)
    
    files = list(Path(data_dir).glob("*.csv"))
    logger.info(f"Found {len(files)} CSVs in {data_dir}")
    
    records = []
    
    for csv_file in files:
        # Infer subreddit from filename usually
        # Filename might be "adhd.csv" or similar
        subreddit = csv_file.stem.lower()
        
        try:
            df = pd.read_csv(csv_file)
        except Exception as e:
            logger.warning(f"Failed to read {csv_file}: {e}")
            continue
            
        # Detect text columns
        # Expected: title, selftext OR post_title, post_body
        text_cols = []
        if "title" in df.columns: text_cols.append("title")
        elif "post_title" in df.columns: text_cols.append("post_title")
        
        if "selftext" in df.columns: text_cols.append("selftext")
        elif "body" in df.columns: text_cols.append("body")
        elif "post_body" in df.columns: text_cols.append("post_body")
        
        if not text_cols:
            logger.warning(f"No text columns found in {csv_file}. Columns: {df.columns}")
            continue
            
        # Sample if needed
        if sample_n and len(df) > sample_n:
            df = df.sample(sample_n, random_state=42)
            
        for _, row in df.iterrows():
            parts = [str(row[c]) for c in text_cols if pd.notna(row[c])]
            text = "\n".join(parts).strip()
            
            if not text or text == "nan" or text == "[deleted]" or text == "[removed]":
                continue
                
            labels = sub_to_labels.get(subreddit, [])
            # If not in map, might be skipped or handled?
            # User requirement: "If RMHD lacks ocd... do not pretend". 
            # If subreddit not in label map, we might default to empty?
            # BUT: Label Mapping has "control" and "other".
            # If subreddit matches nothing, we probably skip it.
            if subreddit not in sub_to_labels and subreddit not in label_map["control"] and subreddit not in label_map["other"]:
                 # Check if the filename IS the label?
                 # Assume map is exhaustive for what we want.
                 pass
            
            # Construct example
            rec = {
                "example_id": f"{subreddit}_{_}", # simple ID
                "text": text,
                "subreddit": subreddit,
                "labels": labels # List of true positive strings
            }
            records.append(rec)
            
    logger.info(f"Compiled {len(records)} records.")
    
    with open(output_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
            
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", required=True)
    parser.add_argument("--out_file", required=True)
    parser.add_argument("--label_map", required=True)
    parser.add_argument("--sample_n", type=int, default=None)
    args = parser.parse_args()
    
    parse_rmhd(args.data_dir, args.out_file, args.label_map, args.sample_n)

if __name__ == "__main__":
    main()
