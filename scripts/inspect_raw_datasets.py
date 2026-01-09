#!/usr/bin/env python3
"""
Step W1: Download and inspect raw datasets (no cleaning).

Downloads:
1. solomonk/reddit_mental_health_posts from HuggingFace
2. MentalHelp from GitHub (cloned)

Outputs:
- Console: split sizes, columns, dtypes, missingness, sample rows
- Markdown report: results/week1/raw_inspection/report.md
- JSON report: results/week1/raw_inspection/report.json
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def get_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> None:
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)


def inspect_hf_dataset(out_dir: Path) -> dict[str, Any]:
    """
    Download and inspect solomonk/reddit_mental_health_posts.
    
    Returns dict with dataset metadata.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        print("ERROR: 'datasets' package not installed. Run: pip install datasets")
        return {"error": "datasets package not installed"}
    
    dataset_id = "solomonk/reddit_mental_health_posts"
    print(f"\n{'='*60}")
    print(f"Downloading HuggingFace dataset: {dataset_id}")
    print("="*60)
    
    try:
        ds = load_dataset(dataset_id)
    except Exception as e:
        print(f"ERROR loading dataset: {e}")
        return {"error": str(e), "dataset_id": dataset_id}
    
    result = {
        "dataset_id": dataset_id,
        "source": "huggingface",
        "splits": {},
        "local_path": None,
    }
    
    # Inspect each split
    for split_name in ds.keys():
        split = ds[split_name]
        num_rows = len(split)
        columns = split.column_names
        
        # Get dtypes
        dtypes = {col: str(split.features[col]) for col in columns}
        
        # Calculate missingness
        missingness = {}
        for col in columns:
            try:
                null_count = sum(1 for x in split[col] if x is None or x == "")
                missingness[col] = {
                    "null_count": null_count,
                    "null_pct": round(100 * null_count / num_rows, 2) if num_rows > 0 else 0
                }
            except Exception:
                missingness[col] = {"null_count": -1, "null_pct": -1}
        
        # Sample rows (first 5)
        sample_rows = []
        for i in range(min(5, num_rows)):
            row = {col: str(split[col][i])[:200] for col in columns}  # Truncate long values
            sample_rows.append(row)
        
        result["splits"][split_name] = {
            "num_rows": num_rows,
            "columns": columns,
            "dtypes": dtypes,
            "missingness": missingness,
            "sample_rows": sample_rows,
        }
        
        # Print to console
        print(f"\n--- Split: {split_name} ---")
        print(f"Rows: {num_rows}")
        print(f"Columns: {columns}")
        print(f"Dtypes: {dtypes}")
        print(f"Missingness: {missingness}")
        print(f"Sample rows (first 5):")
        for i, row in enumerate(sample_rows):
            print(f"  [{i}] {row}")
    
    # Save to disk
    save_path = out_dir / "reddit_mental_health_posts"
    print(f"\nSaving dataset to: {save_path}")
    try:
        ds.save_to_disk(str(save_path))
        result["local_path"] = str(save_path)
        print("Dataset saved successfully.")
    except Exception as e:
        print(f"ERROR saving dataset: {e}")
        result["save_error"] = str(e)
    
    return result


def clone_mentalhelp(out_dir: Path) -> dict[str, Any]:
    """
    Clone MentalHelp repo if not present.
    
    Returns dict with repo metadata.
    """
    repo_url = "https://github.com/stevekwon211/MentalHelp.git"
    repo_dir = out_dir / "MentalHelp"
    
    print(f"\n{'='*60}")
    print(f"Cloning MentalHelp repository")
    print("="*60)
    
    result = {
        "repo_url": repo_url,
        "source": "github",
        "local_path": str(repo_dir),
        "files": [],
        "data_files": [],
    }
    
    if repo_dir.exists():
        print(f"Repository already exists at: {repo_dir}")
    else:
        print(f"Cloning {repo_url} to {repo_dir}")
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(repo_dir)],
                check=True,
                capture_output=True,
                text=True,
            )
            print("Clone successful.")
        except subprocess.CalledProcessError as e:
            print(f"ERROR cloning: {e.stderr}")
            result["error"] = e.stderr
            return result
        except FileNotFoundError:
            print("ERROR: git not found. Please install git.")
            result["error"] = "git not found"
            return result
    
    # Print shallow file tree (max depth 2)
    print(f"\nFile tree (depth 2):")
    for root, dirs, files in os.walk(repo_dir):
        level = len(Path(root).relative_to(repo_dir).parts)
        if level > 2:
            continue
        indent = "  " * level
        print(f"{indent}{Path(root).name}/")
        result["files"].append(str(Path(root).relative_to(repo_dir)))
        
        if level < 2:
            for f in files[:10]:  # Limit files shown
                print(f"{indent}  {f}")
                result["files"].append(str(Path(root).relative_to(repo_dir) / f))
            if len(files) > 10:
                print(f"{indent}  ... and {len(files) - 10} more files")
    
    # Find and inspect data files
    data_extensions = {".csv", ".json", ".jsonl", ".parquet"}
    data_files = []
    
    for ext in data_extensions:
        data_files.extend(repo_dir.rglob(f"*{ext}"))
    
    print(f"\nFound {len(data_files)} data files: {[f.name for f in data_files[:10]]}")
    
    for data_file in data_files[:5]:  # Inspect first 5 data files
        file_info = inspect_data_file(data_file)
        result["data_files"].append(file_info)
    
    return result


def inspect_data_file(file_path: Path) -> dict[str, Any]:
    """Inspect a single data file and return schema info."""
    print(f"\n--- Inspecting: {file_path.name} ---")
    
    result = {
        "path": str(file_path),
        "name": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "extension": file_path.suffix,
    }
    
    try:
        import pandas as pd
        
        if file_path.suffix == ".csv":
            df = pd.read_csv(file_path, nrows=5)
        elif file_path.suffix == ".json":
            df = pd.read_json(file_path, lines=False, nrows=5)
        elif file_path.suffix == ".jsonl":
            df = pd.read_json(file_path, lines=True, nrows=5)
        elif file_path.suffix == ".parquet":
            df = pd.read_parquet(file_path).head(5)
        else:
            print(f"  Unsupported format: {file_path.suffix}")
            result["error"] = f"Unsupported format: {file_path.suffix}"
            return result
        
        result["columns"] = list(df.columns)
        result["dtypes"] = {col: str(dtype) for col, dtype in df.dtypes.items()}
        result["num_rows_sampled"] = len(df)
        result["sample_rows"] = df.head(3).to_dict(orient="records")
        
        print(f"  Columns: {result['columns']}")
        print(f"  Dtypes: {result['dtypes']}")
        print(f"  Sample (3 rows): {result['sample_rows']}")
        
    except Exception as e:
        print(f"  ERROR reading file: {e}")
        result["error"] = str(e)
    
    return result


def write_reports(report_data: dict[str, Any], report_dir: Path) -> None:
    """Write Markdown and JSON reports."""
    ensure_dir(report_dir)
    
    # JSON report (machine-readable)
    json_path = report_dir / "report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nJSON report written to: {json_path}")
    
    # Markdown report (human-readable)
    md_path = report_dir / "report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Raw Dataset Inspection Report\n\n")
        f.write(f"**Generated**: {report_data['timestamp']}\n\n")
        f.write("---\n\n")
        
        # HuggingFace dataset
        hf = report_data.get("huggingface_dataset", {})
        f.write("## 1. HuggingFace: solomonk/reddit_mental_health_posts\n\n")
        f.write(f"- **Dataset ID**: `{hf.get('dataset_id', 'N/A')}`\n")
        f.write(f"- **Local Path**: `{hf.get('local_path', 'N/A')}`\n\n")
        
        if "error" in hf:
            f.write(f"> **ERROR**: {hf['error']}\n\n")
        else:
            for split_name, split_info in hf.get("splits", {}).items():
                f.write(f"### Split: {split_name}\n\n")
                f.write(f"- **Rows**: {split_info.get('num_rows', 'N/A')}\n")
                f.write(f"- **Columns**: {split_info.get('columns', [])}\n\n")
                
                f.write("| Column | Dtype | Null Count | Null % |\n")
                f.write("|--------|-------|------------|--------|\n")
                for col in split_info.get("columns", []):
                    dtype = split_info.get("dtypes", {}).get(col, "?")
                    miss = split_info.get("missingness", {}).get(col, {})
                    f.write(f"| `{col}` | {dtype} | {miss.get('null_count', '?')} | {miss.get('null_pct', '?')}% |\n")
                f.write("\n")
                
                f.write("**Sample Rows**:\n```json\n")
                f.write(json.dumps(split_info.get("sample_rows", [])[:3], indent=2, default=str))
                f.write("\n```\n\n")
        
        # MentalHelp repo
        mh = report_data.get("mentalhelp_repo", {})
        f.write("## 2. GitHub: MentalHelp\n\n")
        f.write(f"- **Repo URL**: `{mh.get('repo_url', 'N/A')}`\n")
        f.write(f"- **Local Path**: `{mh.get('local_path', 'N/A')}`\n\n")
        
        if "error" in mh:
            f.write(f"> **ERROR**: {mh['error']}\n\n")
        else:
            f.write("### Data Files Found\n\n")
            for df_info in mh.get("data_files", []):
                f.write(f"#### {df_info.get('name', 'Unknown')}\n\n")
                f.write(f"- **Size**: {df_info.get('size_bytes', 0)} bytes\n")
                f.write(f"- **Columns**: {df_info.get('columns', [])}\n")
                if "error" in df_info:
                    f.write(f"- **Error**: {df_info['error']}\n")
                f.write("\n")
    
    print(f"Markdown report written to: {md_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Step W1: Download and inspect raw datasets"
    )
    parser.add_argument(
        "--out_dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory to save raw datasets (default: data/raw)"
    )
    parser.add_argument(
        "--report_dir",
        type=Path,
        default=Path("results/week1/raw_inspection"),
        help="Directory to save reports (default: results/week1/raw_inspection)"
    )
    
    args = parser.parse_args()
    
    print(f"Output directory: {args.out_dir}")
    print(f"Report directory: {args.report_dir}")
    
    ensure_dir(args.out_dir)
    ensure_dir(args.report_dir)
    
    # Collect all inspection data
    report_data = {
        "timestamp": get_timestamp(),
        "out_dir": str(args.out_dir.resolve()),
        "report_dir": str(args.report_dir.resolve()),
    }
    
    # 1. Inspect HuggingFace dataset
    report_data["huggingface_dataset"] = inspect_hf_dataset(args.out_dir)
    
    # 2. Clone and inspect MentalHelp
    report_data["mentalhelp_repo"] = clone_mentalhelp(args.out_dir)
    
    # 3. Write reports
    write_reports(report_data, args.report_dir)
    
    print("\n" + "="*60)
    print("Step W1 complete. Reports generated.")
    print("="*60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
