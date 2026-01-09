#!/usr/bin/env python3
"""
W2.6: Leakage Analysis (Lightweight - No Inference).

Since we cannot re-run inference locally (no GPU), this script:
1. Analyzes how sanitization would change the text
2. Documents sanitization statistics
3. Provides a "simulation" of expected impact based on W2.5 shortcut report

For actual leakage-controlled eval with inference, run on Colab.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from text2diag.text.sanitize import sanitize_text, load_sanitize_config

def load_jsonl(path: Path) -> list:
    """Load JSONL file."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

def main():
    parser = argparse.ArgumentParser(description="W2.6 Leakage Analysis (Lightweight)")
    parser.add_argument("--data_dir", type=Path, default=Path("data/processed/reddit_mh_windows"))
    parser.add_argument("--out_dir", type=Path, default=Path("results/week2/remediation"))
    parser.add_argument("--sanitize_config", type=Path, default=Path("configs/sanitize.yaml"))
    args = parser.parse_args()
    
    args.out_dir.mkdir(parents=True, exist_ok=True)
    
    # Load config
    cfg = load_sanitize_config(args.sanitize_config)
    print(f"Sanitize config: {cfg}")
    
    results = {"config": cfg, "splits": {}}
    
    for split in ["val", "test"]:
        data_path = args.data_dir / f"{split}.jsonl"
        if not data_path.exists():
            print(f"WARNING: {data_path} not found")
            continue
        
        records = load_jsonl(data_path)
        print(f"\nAnalyzing {split}: {len(records)} examples")
        
        total_stats = {"urls_removed": 0, "reddit_refs_removed": 0, "examples_affected": 0}
        char_reduction = []
        
        for r in records:
            text = r.get("text", "")
            original_len = len(text)
            
            clean_text, stats = sanitize_text(text, cfg)
            new_len = len(clean_text)
            
            if stats["urls_removed"] > 0 or stats["reddit_refs_removed"] > 0:
                total_stats["examples_affected"] += 1
            
            total_stats["urls_removed"] += stats["urls_removed"]
            total_stats["reddit_refs_removed"] += stats["reddit_refs_removed"]
            
            if original_len > 0:
                char_reduction.append((original_len - new_len) / original_len * 100)
        
        avg_reduction = sum(char_reduction) / len(char_reduction) if char_reduction else 0
        
        results["splits"][split] = {
            "total_examples": len(records),
            "examples_affected": total_stats["examples_affected"],
            "affected_pct": round(100 * total_stats["examples_affected"] / len(records), 2),
            "total_urls_removed": total_stats["urls_removed"],
            "total_reddit_refs_removed": total_stats["reddit_refs_removed"],
            "avg_char_reduction_pct": round(avg_reduction, 2)
        }
        
        print(f"  Affected: {total_stats['examples_affected']} ({results['splits'][split]['affected_pct']}%)")
        print(f"  URLs removed: {total_stats['urls_removed']}")
        print(f"  Reddit refs removed: {total_stats['reddit_refs_removed']}")
        print(f"  Avg char reduction: {avg_reduction:.2f}%")
    
    # Expected impact analysis (based on W2.5 shortcut report: 62% leakage)
    results["expected_impact"] = {
        "note": "Cannot compute actual F1 delta without re-running inference (requires GPU)",
        "shortcut_report_leak_rate": 62.39,
        "recommendation": "Run scripts/09_eval_sanitized.py on Colab with GPU for actual metrics",
        "provisional_verdict": "LIKELY SHORTCUT DEPENDENCE (based on 62% leak rate)"
    }
    
    # Write JSON
    json_path = args.out_dir / "leakage_analysis_lightweight.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {json_path}")
    
    # Write Markdown
    md_path = args.out_dir / "leakage_analysis_lightweight.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Leakage Analysis Report (Lightweight)\n\n")
        f.write("> **Note**: This is a text-only analysis. Actual F1 deltas require GPU inference.\n\n")
        
        f.write("## Sanitization Impact\n\n")
        for split, data in results["splits"].items():
            f.write(f"### {split.upper()}\n")
            f.write(f"- Total examples: {data['total_examples']}\n")
            f.write(f"- Examples affected by sanitization: {data['examples_affected']} ({data['affected_pct']}%)\n")
            f.write(f"- Reddit refs removed: {data['total_reddit_refs_removed']}\n")
            f.write(f"- URLs removed: {data['total_urls_removed']}\n")
            f.write(f"- Avg character reduction: {data['avg_char_reduction_pct']}%\n\n")
        
        f.write("## Expected Impact\n\n")
        f.write(f"Based on W2.5 shortcut audit, **{results['expected_impact']['shortcut_report_leak_rate']}%** of examples contained shortcuts.\n\n")
        f.write("> [!WARNING]\n")
        f.write("> **Provisional Verdict**: LIKELY SHORTCUT DEPENDENCE\n")
        f.write(">\n")
        f.write("> The high leak rate suggests the model may be relying on reddit-specific cues.\n")
        f.write("> Run full evaluation with GPU to measure actual F1 drop.\n\n")
        
        f.write("## Next Steps\n\n")
        f.write("1. Run `scripts/09_eval_sanitized.py` on **Google Colab** (with GPU)\n")
        f.write("2. If F1 drops >10%, rebuild dataset with sanitization baked in\n")
        f.write("3. Retrain model on sanitized data\n")
    
    print(f"Wrote {md_path}")
    print(f"\n=== PROVISIONAL VERDICT: LIKELY SHORTCUT DEPENDENCE ===")
    print("Run full eval on Colab for actual metrics.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
