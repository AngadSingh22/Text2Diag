#!/usr/bin/env python3
"""
Step W1: Build Canonical Reddit Dataset (User Windows + Label Taxonomy).
"""

import argparse
import json
import sys
import yaml
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from text2diag.data.reddit_windows import (
    load_raw_reddit_dataset,
    build_user_windows,
    write_canonical
)

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def generate_report(records: List[Dict], out_dir: Path, report_data: Dict) -> None:
    """Generate Markdown and JSON reports."""
    ensure_dir(out_dir)
    
    # Calculate stats
    splits = Counter(r["split"] for r in records)
    label_counts = Counter()
    label_counts_by_split = defaultdict(Counter)
    
    has_condition = 0
    text_lengths = []
    
    user_leakage_check = defaultdict(set)
    
    for r in records:
        text_lengths.append(len(r["text"]))
        user_leakage_check[r["user_id"]].add(r["split"])
        
        for l in r["labels"]:
            label_counts[l] += 1
            label_counts_by_split[r["split"]][l] += 1
            
        if "condition" in r["label_types"]:
            has_condition += 1
            
    # Leakage Assertion
    leaky_users = [u for u, s in user_leakage_check.items() if len(s) > 1]
    leakage_status = "PASS" if not leaky_users else f"FAIL ({len(leaky_users)} users)"
    
    # Text length stats
    text_lengths.sort()
    n = len(text_lengths)
    stats = {
        "min": text_lengths[0] if n else 0,
        "median": text_lengths[n//2] if n else 0,
        "p95": text_lengths[int(n*0.95)] if n else 0,
        "max": text_lengths[-1] if n else 0,
    }
    
    # Top raw subreddits mapping
    # Assuming we can inspect metadata
    raw_sub_counts = Counter()
    for r in records:
        for s in r["meta"]["subreddits_raw"]:
            raw_sub_counts[s] += 1
            
    # Prepare JSON data
    report_json = {
        "timestamp": report_data["timestamp"],
        "counts": {
            "total_windows": len(records),
            "users": len(user_leakage_check),
            "by_split": dict(splits)
        },
        "leakage_check": leakage_status,
        "stats": {
            "text_length_chars": stats,
            "has_condition_pct": round(100 * has_condition / n, 2) if n else 0
        },
        "labels": {
            "overall": dict(label_counts.most_common(50)),
            "by_split": {k: dict(v.most_common(20)) for k, v in label_counts_by_split.items()}
        }
    }
    
    # Write JSON
    with open(out_dir / "report.json", "w", encoding="utf-8") as f:
        json.dump(report_json, f, indent=2)
        
    # Write Markdown
    with open(out_dir / "report.md", "w", encoding="utf-8") as f:
        f.write("# Reddit Canonical Dataset Report\n\n")
        f.write(f"**Generated**: {report_data['timestamp']}\n\n")
        
        f.write("> **Safety Note**: Subreddit labels are weak proxies; outputs are not diagnoses; "
                "generic subs are treated as general distress; condition labels are only for condition-specific subs; "
                "abstention will be used downstream.\n\n")
        
        f.write("## 1. Summary Counts\n\n")
        f.write(f"- **Total Windows**: {len(records)}\n")
        f.write(f"- **Unique Users**: {len(user_leakage_check)}\n")
        f.write(f"- **Splits**: {dict(splits)}\n")
        f.write(f"- **Leakage Check**: {leakage_status}\n\n")
        
        f.write("## 2. Text Statistics (Chars)\n\n")
        f.write(f"- **Min**: {stats['min']}\n")
        f.write(f"- **Median**: {stats['median']}\n")
        f.write(f"- **P95**: {stats['p95']}\n")
        f.write(f"- **Max**: {stats['max']}\n\n")
        
        f.write("## 3. Label Distribution (Top 20)\n\n")
        f.write("| Label | Count | % |\n|---|---|---|\n")
        for l, c in label_counts.most_common(20):
            pct = round(100 * c / n, 2)
            f.write(f"| `{l}` | {c} | {pct}% |\n")
        f.write("\n")
        
        f.write("## 4. Examples (Truncated)\n\n")
        for i, r in enumerate(records[:3]):
            text_snippet = r["text"].replace("\n", " ")[:200] + "..."
            f.write(f"**Example {i+1}** ({r['split']}):\n")
            f.write(f"- **Labels**: {r['labels']} ({r['label_types']})\n")
            f.write(f"- **Text**: `{text_snippet}`\n\n")

    print(f"Reports written to {out_dir}")

def main():
    parser = argparse.ArgumentParser(description="Build Canonical Reddit Dataset")
    parser.add_argument("--config", default="configs/data_reddit.yaml", help="Path to config")
    args = parser.parse_args()
    
    cfg = load_config(args.config)
    
    print(f"Loading raw data from: {cfg['raw_path']}")
    ds = load_raw_reddit_dataset(cfg['raw_path'])
    
    print(f"Building windows (N={cfg['window_size_posts']})...")
    records = build_user_windows(
        ds=ds,
        window_size=cfg['window_size_posts'],
        policy=cfg['label_policy'],
        whitelist_path=cfg['label_policy']['condition_whitelist'],
        separator=cfg['separator'],
        split_seed=cfg['split_seed'],
        split_fracs=cfg['split_fracs']
    )
    
    if not records:
        print("Error: No records generated.")
        return 1
    
    out_path = Path(cfg['out_path'])
    print(f"Writing canonical data to: {out_path}")
    write_canonical(records, out_path)
    
    # Reports
    from datetime import datetime
    report_data = {"timestamp": datetime.now().isoformat()}
    report_dir = Path(cfg.get("report_dir", "results/week1/reddit_canonical"))
    
    generate_report(records, report_dir, report_data)
    
    print("\nDone.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
