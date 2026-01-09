# CLEANUP_PLAN.md - Repo Normalization V1

**Status**: DRAFT (Phase 1: Audit)
**Goal**: Non-destructive normalization of file paths and names.

## 1. Goals
- Canonical structure: `src/text2diag/{module}`, `scripts/`, `configs/`, `results/`.
- Consistent naming: `weekX` (lowercase, no hyphen), `preds_split.jsonl`.
- No deletion of placeholders.

## 2. Audit Findings
- **Script Sequence Gap**: `02-04` exist, then jumps to `10`.
- **Legacy Clutter**: `train.py`, `eval.py` etc unused in root scripts.
- **Results Structure**: `test_w3_smoke` at root. `results_week2` duplicate in root.
- **Module Ambiguity**: `src/text2diag/modeling` vs `model`.

## 3. Moves / Renames Map
| Current | Target | Rationale |
|---------|--------|-----------|
| `scripts/train.py` | `docs/legacy/scripts/train.py` | Legacy unused template |
| `scripts/eval.py` | `docs/legacy/scripts/eval.py` | Legacy unused template |
| `scripts/prepare_data.py` | `docs/legacy/scripts/prepare_data.py` | Legacy unused template |
| `scripts/calibrate.py` | `docs/legacy/scripts/calibrate.py` | Legacy unused template |
| `scripts/infer_json.py` | `docs/legacy/scripts/infer_json.py` | Legacy unused template |
| `scripts/run_all.py` | `docs/legacy/scripts/run_all.py` | Legacy unused template |
| `scripts/inspect_raw_datasets.py` | `scripts/01_inspect_raw_datasets.py` | Normalize naming |
| `scripts/10_build_sanitized_dataset.py` | `scripts/05_build_sanitized_dataset.py` | Fix sequence (W3) |
| `scripts/11_train_robust.py` | `scripts/06_train_robust.py` | Fix sequence (W3) |
| `scripts/11_posttrain_pack_sanitized.py` | `scripts/07_posttrain_pack_sanitized.py` | Fix sequence (W3) |
| `scripts/12_compare_robustness.py` | `scripts/08_compare_robustness.py` | Fix sequence (W3) |
| `results/test_w3_smoke/` | `results/week3/smoke/` | Normalize results path |
| `src/text2diag/modeling/` | `src/text2diag/decision/` | Fix module ambiguity (model vs modeling) |
| `results_week2/` | `results/week2_archived_duplicate/` | Isolate debris for deletion later |

## 4. Verification Plan
- **Pre-Move**: Run `ACCEPTANCE_TESTS.md` Tier A (Smoke).
- **mid-Move**: Run `grep` or `rg` to find imports of moved files.
- **Post-Move**: Run Tier A again.
