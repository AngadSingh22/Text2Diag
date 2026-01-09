# DECISIONS – Change Log with Rationale

> **Rule**: Every significant change must be logged here with what/why/expected impact.

---

## 2026-01-09T22:28:02+05:30 – Step W1: Raw Dataset Inspection Setup

### What Changed
1. **`.gitignore`**: Added comprehensive exclusions for `data/`, `data/raw/`, `*.arrow`, model artifacts, and other large files
2. **`requirements.txt`**: Added `datasets>=2.0.0`, `pandas>=1.5.0`, `numpy>=1.21.0`, `pyarrow>=10.0.0`, `pytest>=7.0.0`
3. **`scripts/inspect_raw_datasets.py`**: New script to download and inspect raw datasets

### Why
- Need to download and analyze two datasets before any preprocessing:
  - `solomonk/reddit_mental_health_posts` (HuggingFace)
  - `MentalHelp` (GitHub repo)
- Must understand dataset structure (columns, types, missingness) before designing cleaning pipeline
- Data files must not be committed (too large), only code and small reports

### Expected Metric Impact
- **No model metrics yet** – this is data exploration phase
- **Deliverables**: Structure report (Markdown + JSON) documenting dataset schemas
- **Risk mitigation**: Understanding data shape early prevents downstream pipeline errors
