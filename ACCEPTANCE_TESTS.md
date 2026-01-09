# ACCEPTANCE_TESTS – Definition of Done

> **Purpose**: Define exact commands to verify the codebase is in a working state.

---

## Tier A: Smoke Tests (Run on Every Atomic Commit)

Fast checks that must pass before any commit. Target: <10 seconds.

### A1. Syntax Check
```powershell
py -m compileall src scripts -q
```
**Expected**: Exit code 0, no output.

### A2. Import Check
```powershell
py -c "import sys; sys.path.insert(0, 'src'); import text2diag; print('OK')"
```
**Expected**: Prints `OK`, exit code 0.

### A3. New Script Help Check
For any newly added/modified script, verify `--help` works:
```powershell
py scripts/<script_name>.py --help
```
**Expected**: Prints usage info, exit code 0.

### A4. Quick Pytest
```powershell
py -m pytest tests/ -q --tb=no
```
**Expected**: All collected tests pass (or 0 collected if empty). Exit code 0.

---

### Tier A: All-in-One Command (Copy-Paste Ready)

```powershell
# Windows PowerShell - Smoke Tests
py -m compileall src scripts -q; `
py -c "import sys; sys.path.insert(0, 'src'); import text2diag; print('Import OK')"; `
py -m pytest tests/ -q --tb=no
```

---

## Tier B: Full Tests (Run Before Push/Milestone)

Comprehensive checks for merge readiness. Run after completing a plan step.

### B1. Full Pytest with Verbose Output
```powershell
py -m pytest tests/ -v --tb=short
```
**Expected**: All tests pass.

### B2. All Scripts Help Check
```powershell
py scripts/prepare_data.py --help
py scripts/train.py --help
py scripts/eval.py --help
py scripts/calibrate.py --help
py scripts/infer_json.py --help
py scripts/run_all.py --help
py scripts/inspect_raw_datasets.py --help
```
**Expected**: Each prints usage info, exit code 0.

### B3. Governance Files Exist
```powershell
Get-ChildItem AGENT_PROTOCOL.md, RUNLOG.md, ACCEPTANCE_TESTS.md, DECISIONS.md | Select-Object Name
```
**Expected**: All 4 files listed.

### B4. Lint (if configured)
```powershell
# TODO: Add ruff or flake8 when configured
# ruff check src scripts
```

---

### Tier B: All-in-One Command (Copy-Paste Ready)

```powershell
# Windows PowerShell - Full Tests
py -m compileall src scripts -q; `
py -c "import sys; sys.path.insert(0, 'src'); import text2diag; print('Import OK')"; `
py -m pytest tests/ -v --tb=short; `
py scripts/prepare_data.py --help; `
py scripts/train.py --help; `
py scripts/eval.py --help; `
py scripts/calibrate.py --help; `
py scripts/infer_json.py --help; `
py scripts/run_all.py --help; `
py scripts/inspect_raw_datasets.py --help; `
Get-ChildItem AGENT_PROTOCOL.md, RUNLOG.md, ACCEPTANCE_TESTS.md, DECISIONS.md | Select-Object Name
```

---

## Artifacts

After a successful SAFE PATH run:
- `RUNLOG.md` with latest entry (expanded format)
- All scripts respond to `--help`
- `src/text2diag/` importable
- All governance files present

---

## Test File Inventory

| File | Purpose | Tier |
|------|---------|------|
| `tests/test_contract_validator.py` | Contract validation | A, B |
| `tests/test_evidence_span_validity.py` | Evidence spans | A, B |
| `tests/test_repair_rules.py` | Repair rules | A, B |
| `tests/test_splits_deterministic.py` | Deterministic splits | A, B |
| `tests/test_reddit_canonical.py` | Reddit Logic | A, B |

---

## Week 2: Baseline Model Tests

### A5. W2 Smoke Test (Training Loop)
Verify the training script runs end-to-end on a tiny subset.
```powershell
py scripts/03_train_baseline.py --data_dir data/processed/reddit_mh_windows --out_dir results/test_w2_smoke --limit_examples 50 --epochs 1 --batch_size 2
```
**Expected**: Runs without error, creates artifacts in `results/test_w2_smoke`.

### B5. Colab Notebook Check
Ensure notebook exists.
```powershell
Get-Item notebooks/colab_week2_train.ipynb
```
**Expected**: File found.

---

### Week 2 Sanitized (Post-Train Pack)
Tier A (Smoke):
```bash
py scripts/11_posttrain_pack_sanitized.py --checkpoint_path results/week3/robust_baseline/checkpoints/checkpoint-X --data_dir data/processed/reddit_mh_sanitized --label_map data/processed/reddit_mh_sanitized/label2id.json --smoke --out_dir results/test_pack_smoke
# Expect: Preds saved, Metrics printed, Pack Complete.
```

## Week 2.6 (Leakage Eval)

### A6. Leakage-Controlled Eval
```powershell
py scripts/04_eval_robustness.py --checkpoint results_week2/results/week2/checkpoints/checkpoint-4332 --sanitize_config configs/text_cleaning.yaml
```
**Expected**: Creates artifacts in `results/week2/robustness/`.

### B6. Artifacts Check
```powershell
Get-ChildItem results/week2/robustness/*.json | Select-Object Name
Get-ChildItem configs/text_cleaning.yaml
Get-ChildItem configs/model_thresholds.yaml
```
**Expected**: `leakage_eval_metrics.json` and config files exist.
