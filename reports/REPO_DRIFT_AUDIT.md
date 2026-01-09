# Repo Drift Audit

**Date**: 2026-01-10
**Scope**: Full Repository

## 1. Expected Canonical Structure
- `src/text2diag/{module}`:
    - `data`, `model`, `train`, `eval`, `calibration`, `evidence`, `contract`, `utils`.
- `scripts/`: Numbered pipeline steps (`01_`, `02_`...) or single-purpose utilities.
- `configs/`: YAML configurations.
- `results/`: `week{N}` organized outputs.
- `docs/`: Documentation and legacy archives.

## 2. Observed Deviations

| Item | Current Path | Proposed Path | Reason | Action |
|------|--------------|---------------|--------|--------|
| **Script Inconsistency** | `scripts/train.py`, `scripts/eval.py` (etc) | `docs/legacy/scripts/` | Appears to be unused template code. Superseded by `03_train_baseline.py`. | **Move** to legacy. |
| **Script Numbering** | `scripts/10_...` thru `12_...` | `scripts/05_...` thru `08_...` | Gap in numbering sequences. `10` implies Week 10? | **Rename** to continuous sequence. |
| **Results Clutter** | `results/test_w3_smoke` | `results/week3/smoke` | Ad-hoc output at root of results. | **Move** into week folder. |
| **Results Duplication** | `results_week2/` | (Delete or Merge) | Seems to be an accidental unzipped artifact or duplicate. | **Investigate & Archive**. |
| **Module Ambiguity** | `src/text2diag/modeling/` | `src/text2diag/decision/` | Contains `postprocess.py` (thresholds). `modeling` conflicts with `model`. | **Move/Rename**. |
| **Notebook naming** | `notebooks/colab_week2_train.ipynb` | `notebooks/W2_Train_Baseline.ipynb` | Inconsistent casing/naming. | **Normalize** (Low priority). |

## 3. Orphan Candidates
(Files likely not imported or used in current pipeline)
- `scripts/calibrate.py`
- `scripts/infer_json.py`
- `scripts/run_all.py`
- `scripts/train.py`
- `scripts/prepare_data.py`
- `src/text2diag/model/train.py` (vs `src/text2diag/train/train_baseline.py`)

## 4. Duplicate Functionality
- `src/text2diag/model/train.py` vs `src/text2diag/train/train_baseline.py`.
- `scripts/eval.py` vs `scripts/04_eval_robustness.py`.

## 5. Inconsistent Naming
- `week2` vs `week2_sanitized` (Good, consistent).
- `metrics.json` (Good).
- `preds_val.jsonl` vs `test.jsonl` (Input data is `test.jsonl`, predictions are `preds_test.jsonl`. Consistent).

## Conclusion
Drift is moderate.
- Primary cleanup: Archive legacy scripts.
- Secondary: Renumber Week 3 scripts.
- Tertiary: Fix `results` structure.
