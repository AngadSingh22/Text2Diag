"""
Reddit Dataset Canonicalization Module.

Handles loading, windowing, labeling, and Splitting for Reddit Mental Health data.
"""

import hashlib
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple, Optional

# Third-party imports
try:
    from datasets import load_from_disk, Dataset, DatasetDict
except ImportError:
    Dataset = Any  # type: ignore
    DatasetDict = Any # type: ignore

def load_raw_reddit_dataset(raw_path: str) -> Dataset:
    """Load the raw HuggingFace dataset from disk."""
    try:
        ds = load_from_disk(raw_path)
        return ds
    except Exception as e:
        raise ValueError(f"Failed to load dataset from {raw_path}: {e}")

def normalize_text(title: Optional[str], body: Optional[str]) -> str:
    """Normalize and combine title and body."""
    t = (title or "").strip()
    b = (body or "").strip()
    if t and b:
        return f"{t}\n{b}"
    return t or b

def load_whitelist(path: str) -> Set[str]:
    """Load lowercase whitelist from file."""
    with open(path, "r", encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip()}

def get_label_info(subreddit: str, policy: Dict[str, Any], whitelist: Set[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Determine (label_name, label_type) for a given subreddit.
    
    Types: condition, generic, other
    """
    if not subreddit:
        return None, None
        
    sub_lower = subreddit.lower().replace("r/", "")
    
    # 1. Condition Whitelist
    if sub_lower in whitelist:
        return sub_lower, "condition"
    
    # 2. Generic Map
    generic_map = policy.get("generic_map", {})
    # Normalize map keys to lower just in case
    generic_map_lower = {k.lower(): v for k, v in generic_map.items()}
    
    if sub_lower in generic_map_lower:
        return generic_map_lower[sub_lower], "generic"
        
    # 3. Unknown Policy
    action = policy.get("unknown_subreddit_action", "other")
    if action == "drop":
        return None, None
    elif action == "keep_as_other":
        return policy.get("other_label", "other"), "other"
    else:
        # 'keep' raw name (not recommended but supported)
        return sub_lower, "other"

def derive_labels(window_subreddits: List[str], policy: Dict[str, Any], whitelist: Set[str]) -> Tuple[List[str], List[str], List[str]]:
    """
    Derive final labels for a window.
    
    Returns:
        (labels, label_types, labels_source)
    """
    final_labels = set()
    final_types = set()
    sources = set()
    
    for sub in window_subreddits:
        res = get_label_info(sub, policy, whitelist)
        if res == (None, None):
            continue
            
        label, ltype = res
        if label and ltype:
            final_labels.add(label)
            final_types.add(ltype)
            sources.add(sub)
            
    return sorted(list(final_labels)), sorted(list(final_types)), sorted(list(sources))

def assign_user_split(user_id: str, seed: int, fracs: Dict[str, float]) -> str:
    """Deterministic hash-based split assignment."""
    # Create deterministic hash
    hash_input = f"{user_id}-{seed}".encode("utf-8")
    hash_val = int(hashlib.sha256(hash_input).hexdigest(), 16)
    
    # Normalize to [0, 1]
    norm_val = (hash_val % 100000) / 100000.0
    
    train_frac = fracs.get("train", 0.8)
    val_frac = fracs.get("val", 0.1)
    
    if norm_val < train_frac:
        return "train"
    elif norm_val < (train_frac + val_frac):
        return "val"
    else:
        return "test"

def build_user_windows(
    ds: Any, 
    window_size: int, 
    policy: Dict[str, Any],
    whitelist_path: str,
    separator: str,
    split_seed: int,
    split_fracs: Dict[str, float]
) -> List[Dict[str, Any]]:
    """
    Process dataset into canonical windows grouped by user.
    """
    whitelist = load_whitelist(whitelist_path)
    
    # 1. Group by author
    user_posts = {}
    
    print("Grouping posts by user...")
    
    # Handle DatasetDict or Dataset
    iterator = ds
    if hasattr(ds, "values"): # HF DatasetDict
         import itertools
         iterator = itertools.chain(*ds.values())
    elif isinstance(ds, dict): 
        import itertools
        iterator = itertools.chain(*ds.values())

    count = 0
    # Optimization: If dataset is large, we should not load all into memory.
    # W1 restriction: "dataset size allows it". 
    # solomonk/reddit_mental_health_posts is ~150k rows. 
    # Text can be large but likely fits in 16GB RAM easily.
    
    for row in iterator:
        author = row.get("author")
        if not author or author == "[deleted]":
            continue
            
        # Normalize text
        text = normalize_text(row.get("title"), row.get("body"))
        if not text:
            continue
            
        if author not in user_posts:
            user_posts[author] = []
            
        try:
            created = float(row.get("created_utc", 0.0))
        except (ValueError, TypeError):
            created = 0.0

        user_posts[author].append({
            "text": text,
            "subreddit": row.get("subreddit"),
            "created_utc": created,
            "id": str(row.get("id", str(count)))
        })
        count += 1
        
    print(f"Found {len(user_posts)} unique authors.")
    
    canonical_records = []
    
    # 2. Create windows (Last N)
    for author, posts in user_posts.items():
        # Sort by time
        posts.sort(key=lambda x: x["created_utc"])
        
        N = window_size
        if len(posts) < 1:
            continue
            
        # Take LAST N posts
        window_posts = posts[-N:]
        
        # Concat text
        full_text = separator.join([p["text"] for p in window_posts])
        
        # Derive labels
        subs = [p["subreddit"] for p in window_posts]
        labels, ltypes, sources = derive_labels(subs, policy, whitelist)
        
        # Check label validity
        if not labels:
             # Check if we should Drop
             if policy.get("unknown_subreddit_action") == "drop":
                 continue
        
        # Assign split
        split = assign_user_split(author, split_seed, split_fracs)
        
        # Create Record
        newest_post = window_posts[-1]
        rec = {
            "example_id": f"{author}:{newest_post['id']}",
            "user_id": author,
            "created_utc_max": newest_post["created_utc"],
            "text": full_text,
            "labels": labels,
            "labels_source": sources,
            "label_types": ltypes,
            "split": split,
            "meta": {
                "window_size": len(window_posts),
                "post_ids": [p["id"] for p in window_posts],
                "subreddits_raw": subs
            }
        }
        canonical_records.append(rec)

    return canonical_records

def write_canonical(records: List[Dict], out_dir: Path):
    """Write records to JSONL files by split."""
    out_dir.mkdir(parents=True, exist_ok=True)
    
    splits = {"train": [], "val": [], "test": []}
    
    for r in records:
        if r["split"] in splits:
            splits[r["split"]].append(r)
        else:
            print(f"Warning: Unknown split {r['split']}")
        
    for s_name, s_recs in splits.items():
        path = out_dir / f"{s_name}.jsonl"
        print(f"Writing {len(s_recs)} records to {path}")
        with open(path, "w", encoding="utf-8") as f:
            for r in s_recs:
                f.write(json.dumps(r) + "\n")
                
    # Also write a label index
    all_labels = set()
    for r in records:
        all_labels.update(r["labels"])
    
    label_path = out_dir / "labels.json"
    with open(label_path, "w", encoding="utf-8") as f:
        json.dump(sorted(list(all_labels)), f, indent=2)
    print(f"Labels written to {label_path}")
