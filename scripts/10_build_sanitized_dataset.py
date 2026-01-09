#!/usr/bin/env python3
"""
Week 3: Build Sanitized (Blind) Dataset.

This script rebuilds the canonical dataset but applies STRICT sanitization:
1. Strips URLs and Reddit references
2. MASKS diagnosis words (e.g., "ADHD" -> "[MASK]")

The goal is to force the model to learn symptom patterns, not self-labeling shortcuts.
Output: data/processed/reddit_mh_sanitized
"""
import sys
import yaml
import shutil
import argparse
from pathlib import Path
from datasets import load_from_disk

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from text2diag.data.reddit_windows import (
    load_raw_reddit_dataset, 
    build_user_windows, 
    write_canonical
)
from text2diag.data.cleaning import sanitize_text

def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def clean_batch(examples, cfg):
    """
    Sanitize text and prepare for build_user_windows.
    We combine title+body, sanitize, then set title='' and body=cleaned.
    """
    titles = examples.get("title", [""] * len(examples["author"]))
    bodies = examples.get("body", [""] * len(examples["author"]))
    
    cleaned_bodies = []
    cleaned_titles = []
    
    # Enable masking
    sanitize_cfg = {**cfg, "mask_diagnosis_words": True}
    
    for t, b in zip(titles, bodies):
        full_text = f"{t or ''}\n{b or ''}".strip()
        # Sanitize
        clean_text, _ = sanitize_text(full_text, sanitize_cfg)
        
        # Override for build_user_windows
        cleaned_titles.append("")
        cleaned_bodies.append(clean_text)
        
    return {"title": cleaned_titles, "body": cleaned_bodies}

def filter_dataset(ds, min_sents, max_sents):
    """Simple length filter."""
    def _filter(x):
        # Rough heuristic: split by newline or dot
        text = f"{x.get('title') or ''}\n{x.get('body') or ''}"
        # Very rough sentence count
        count = text.count('.') + text.count('!') + text.count('?')
        # Also check length > 0
        if len(text.strip()) < 10: return False
        if max_sents and count > max_sents: return False
        if min_sents and count < min_sents: return False
        return True
    
    return ds.filter(_filter)

def main():
    parser = argparse.ArgumentParser(description="Build Sanitized Dataset (Week 3)")
    parser.add_argument("--config", type=Path, default=Path("configs/data_reddit.yaml"))
    parser.add_argument("--clean_config", type=Path, default=Path("configs/text_cleaning.yaml"))
    parser.add_argument("--raw_path", type=Path, help="Override raw path in config")
    parser.add_argument("--out_dir", type=Path, default=Path("data/processed/reddit_mh_sanitized"))
    parser.add_argument("--limit", type=int, help="Limit examples for smoke testing")
    parser.add_argument("--num_proc", type=int, default=4, help="Number of processes")
    args = parser.parse_args()

    # Load configs
    cfg = load_config(args.config)
    clean_cfg = load_config(args.clean_config)
    if args.raw_path:
        cfg["raw_path"] = str(args.raw_path)
    
    print(f"Building SANITIZED dataset from: {cfg['raw_path']}")
    print(f"Output: {args.out_dir}")
    print("NOTE: Diagnosis masking is FORCED to True")

    # 1. Load Raw
    ds = load_raw_reddit_dataset(cfg["raw_path"])
    
    # Handle DatasetDict
    if hasattr(ds, "keys") and "train" in ds:
        ds = ds["train"]
    elif hasattr(ds, "keys"):
        ds = ds[list(ds.keys())[0]]
        
    if args.limit:
        print(f"Limiting to {args.limit} examples")
        ds = ds.select(range(args.limit))

    # 2. Filter (Re-implemented here)
    print("Filtering dataset...")
    ds_filtered = filter_dataset(ds, cfg.get("min_sents", 0), cfg.get("max_sents", 0))
    
    # 3. Apply Sanitization
    print("Applying text sanitization (URLs, Reddit Refs, MASKING)...")
    ds_cleaned = ds_filtered.map(
        lambda b: clean_batch(b, clean_cfg),
        batched=True,
        num_proc=args.num_proc,
        desc="Sanitizing"
    )

    # 4. Build Windows
    print("Creating windows...")
    
    # Extract config values
    window_size = cfg.get("window_size_posts", 3)
    whitelist_path = cfg["label_policy"]["condition_whitelist"]
    seed = cfg.get("split_seed", 1337)
    
    # Splits from config
    raw_fracs = cfg.get("split_fracs", {"train": 0.8, "val": 0.1, "test": 0.1})
    
    windows = build_user_windows(
        ds=ds_cleaned,
        window_size=window_size,
        policy=cfg["label_policy"],
        whitelist_path=whitelist_path,
        separator=cfg.get("separator", "\n\n---POST---\n\n"),
        split_seed=seed,
        split_fracs=raw_fracs
    )

    # 5. Save
    print(f"Saving {len(windows)} windows to {args.out_dir}...")
    if args.out_dir.exists():
        shutil.rmtree(args.out_dir)
    write_canonical(windows, args.out_dir)

    print("✅ Sanitized dataset built successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
