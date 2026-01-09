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

---

## 2026-01-09T23:40:33+05:30 – Governance: Fast/Safe Execution Paths

### What Changed
1. **`AGENT_PROTOCOL.md`**: Added FAST PATH (default, lightweight) and SAFE PATH (merge/push) execution policies. Defined "relevant scope" to prevent full repo re-reads.
2. **`ACCEPTANCE_TESTS.md`**: Split tests into Tier A (smoke, <10s) and Tier B (full). Added copy-paste ready commands for both.
3. **`RUNLOG.md`**: Updated template to support short FAST PATH entries (3 lines) and full SAFE PATH entries. Added deferred logging to `results/runlogs/`.

### Why
Current governance caused slowness due to:
- Mandatory full repo reads on every action
- Full acceptance tests on every atomic commit
- Verbose RUNLOG entries even for trivial changes
- No caching or scope limitation

### Expected Metric Impact
- **Agent efficiency**: ~60% reduction in I/O per atomic step
- **Test time**: Smoke tier targets <10s vs ~30s+ for full suite
- **Auditability**: Preserved via SAFE PATH requirements before push
- **Risk**: None – SAFE PATH ensures full validation before merge

---

## 2026-01-10T00:10:22+05:30 – W1 Label Policy: Weak Labels + Taxonomy

### What Changed
Adopted a "Weak Label" strategy for Reddit data:
1. **Source**: Subreddit name = weak label signal.
2. **Taxonomy**:
    - **Conditions**: Only whitelisted subs (e.g., `ADHD`, `Anxiety`) map to condition labels.
    - **Generic**: Subs like `mentalhealth`, `depression_help` map to `general_distress`.
    - **Other**: Unknown subs map to `other` or are dropped.
3. **Abstention**: Model should learn to abstain or predict `general_distress` when evidence is ambiguous.

### Why
- **No Clinical Ground Truth**: We only have user self-reports/community membership.
- **Safety**: Avoiding "diagnosis" claims. Output is "user posts in r/ADHD-like context", not "user has ADHD".
- **Generic Handling**: Distinguishing general distress from specific conditions is critical for precision.

### Expected Metric Impact
- **Accuracy**: May be lower than "clean" labels but more realistic.
- **Calibration**: Expect higher uncertainty for `general_distress` inputs.

---

## 2026-01-10T02:00:00+05:30 – W2.5 Shortcut/Leakage Audit: FAIL

### What Changed
**Finding**: 62% of examples contain explicit subreddit references (e.g., "r/adhd", "r/depression") in the text.

### Why This Matters
- The model may be learning to detect "r/adhd" substring rather than actual ADHD symptom language.
- Real-world clinical text will not contain these reddit-specific tokens.
- Our 89% F1 may be inflated by this shortcut.

### Remediation (Deferred to Week 3)
1. **Token Stripping**: Add preprocessing step to remove `r/<subreddit>` patterns.
2. **URL Removal**: Strip all URLs.
3. **Robustness Eval**: Re-train or re-evaluate on masked data.

### Expected Metric Impact
- After remediation, F1 may drop significantly (10-30%) as model loses shortcut.
- True "diagnostic ability" will be measured.

---

## 2026-01-10T02:24:06+05:30 – W2.6 Policy Lock: Text Sanitization

### What Changed
**LOCKED**: Text sanitization rules for preprocessing:
1. `strip_urls`: Remove all `http(s)://` and `www.` patterns. **ON by default.**
2. `strip_reddit_refs`: Remove `r/<subreddit>`, `/r/<subreddit>` patterns. **ON by default.**
3. `mask_diagnosis_words`: Optional toggle to mask condition names. **OFF by default.**

### Why
- Addresses 62% shortcut leakage detected in W2.5.
- URLs and subreddit references are reddit-specific artifacts not present in real clinical text.
- Diagnosis word masking is optional as it may remove legitimate symptom discussions.

### Expected Metric Impact
- F1 may drop 10-30% if model relied on shortcuts.
- Establishes "true" model capability.

---

## 2026-01-10T02:24:06+05:30 – W2.6 Policy Lock: Threshold Decision Layer

### What Changed
**LOCKED**: Operational threshold policy:
- **Policy**: Per-label thresholds (from W2.5 sweep).
- **Values**: adhd=0.45, depression=0.45, ocd=0.40, other=0.50, ptsd=0.60
- **Fallback**: Global t=0.45 (micro-optimized).
- **Note**: Raw probabilities are always exported. Thresholds are a decision layer only.

### Why
- Per-label thresholds maximize per-class F1 given class imbalance.
- Explicit policy prevents ad-hoc threshold choices downstream.
- Disclaimer: Probabilities are NOT calibrated (no Week 3 work).

### Expected Metric Impact
- Improved per-label F1 vs fixed 0.5 threshold.
- No change to ranking metrics (AUC).
