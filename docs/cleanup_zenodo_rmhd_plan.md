# Cleanup Plan: De-scope Zenodo RMHD External Validation

**Objective**: Remove all artifacts related to the Zenodo Reddit Mental Health Dataset (RMHD) external validation while preserving core Week 5 infrastructure (Contract V1, E2E Runner, Verifier).

## 1. Inventory & Classification

| File Path | Classification | Action |
|-----------|----------------|--------|
| `notebooks/zenodo_rmhd_validation_colab.ipynb` | Pure External | **DELETE** |
| `notebooks/zenodo_rmhd_validation_colab.py` | Pure External | **DELETE** |
| `scripts/20_rmhd_download_subset.py` | Pure External | **DELETE** |
| `scripts/21_rmhd_build_jsonl.py` | Pure External | **DELETE** |
| `scripts/22_rmhd_leakage_report.py` | Pure External | **DELETE** |
| `scripts/24_rmhd_eval_metrics.py` | Pure External | **DELETE** |
| `configs/external/rmhd_label_mapping.json` | Pure External | **DELETE** |
| `src/text2diag/preprocess/sanitize_external.py` | Pure External | **DELETE** (Redundant with `text.sanitize`) |
| `scripts/14_run_e2e_contract_v1.py` | Shared Core | **KEEP & REFACTOR** (Remove RMHD defaults, keep generic flags) |
| `scripts/23_week5_verify_outputs.py` | Shared Core | **KEEP** (Generic Output Verifier) |
| `src/text2diag/explain/dependency.py` | Shared Core | **KEEP** (Week 5 Requirement) |
| `ACCEPTANCE_TESTS.md` | Shared - Partial | **UPDATE** (Remove A15, Keep A16) |

## 2. Refactoring Plan (Shared Components)

### `scripts/14_run_e2e_contract_v1.py`
- **Flag**: `--skip_sanitization` -> Keep (Useful for testing).
- **Flag**: `--include_dependency_graph` -> Keep (Week 5 Requirement).
- **Import**: Remove `text2diag.preprocess.sanitize_external` usage if present (it was used via `sanitize_config` override or explicit call? No, script uses `sanitize_text` from `text.sanitize` by default, but I need to check if I added imports).

### `src/text2diag/explain/dependency.py`
- Verify graph edges are generic enough or configurable. Current hardcoded edges ("ptsd"->"depression") are acceptable for the generic "Week 5" graph requirement as a placeholder/demonstration.

## 3. Documentation Cleanup
- `walkthrough.md`: Remove "External Validation" section.
- `task.md`: Remove "External Validation" items.
- `RUNLOG.md` / `DECISIONS.md`: Log the de-scoping.

## 4. Acceptance Tests
- Remove A15 (RMHD Sanitization Smoke).
- Verify A16 (Verifier Smoke) works without RMHD.
- Ensure A12 (E2E Runner) covers basic flow.

## 5. Execution Steps
1. **Governance**: Log plan.
2. **Delete**: Remove Pure External files.
3. **Refactor**: Clean up scripts and tests.
4. **Verify**: Run `py -m pytest` and Tier A smoke tests.
