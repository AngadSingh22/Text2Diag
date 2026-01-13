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
py scripts/01_inspect_raw_datasets.py --help
py scripts/02_build_reddit_canonical.py --help
py scripts/03_train_baseline.py --help
py scripts/04_eval_robustness.py --help
py scripts/05_build_sanitized_dataset.py --help
py scripts/06_train_robust.py --help
py scripts/07_posttrain_pack_sanitized.py --help
py scripts/08_compare_robustness.py --help
py scripts/10_calibration_w3.py --help
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
py scripts/01_inspect_raw_datasets.py --help; `
py scripts/02_build_reddit_canonical.py --help; `
py scripts/03_train_baseline.py --help; `
py scripts/04_eval_robustness.py --help; `
py scripts/05_build_sanitized_dataset.py --help; `
py scripts/06_train_robust.py --help; `
py scripts/07_posttrain_pack_sanitized.py --help; `
py scripts/08_compare_robustness.py --help; `
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
py scripts/07_posttrain_pack_sanitized.py --checkpoint_path results/week3/robust_baseline/checkpoints/checkpoint-X --data_dir data/processed/reddit_mh_sanitized --label_map data/processed/reddit_mh_sanitized/label2id.json --smoke --out_dir results/test_pack_smoke
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

---

## Week 3: Calibration

### A7. Calibration W3 Smoke
Run calibration on existing predictions.
```powershell
py scripts/10_calibration_w3.py --val_preds results/week2_sanitized/preds/preds_val.jsonl --test_preds results/week2_sanitized/preds/preds_test.jsonl --out_dir results/week3_calibration
```
**Expected**: `calibration_metrics.json`, `reliability_test.png`, `preds_test_calibrated.jsonl` created.


---

## Week 4: Evidence Extraction

### A8. Evidence Smoke Test
Run evidence extraction on a tiny sample.
```powershell

### A9. Hardened Evidence Runner Smoke (W4.1)
Verify metadata logging and backbone-agnostic attribution.
```powershell
py scripts/12_explain_evidence.py --checkpoint temp_model --temperature_json results/week2_sanitized/calibration/temperature_scaling.json --label_map data/processed/reddit_mh_sanitized/labels.json --dataset_file data/processed/reddit_mh_sanitized/val.jsonl --preds_file results/week2_sanitized/calibration/preds_val_calibrated.jsonl --out_dir results/test_w4_1_hardening --sample_n 10
```
**Expected**: `evidence.jsonl` contains `"metadata":`.

### A10. Faithfulness Baselines Smoke (W4.1)
Verify baselines vs evidence.
```powershell
py scripts/13_w4_faithfulness_baselines.py --checkpoint temp_model --temperature_json results/week2_sanitized/calibration/temperature_scaling.json --label_map data/processed/reddit_mh_sanitized/labels.json --dataset_file data/processed/reddit_mh_sanitized/val.jsonl --preds_file results/week2_sanitized/calibration/preds_val_calibrated.jsonl --out_dir results/test_w4_1_baselines --sample_n 30
# Assertion: Evidence pass rate >= Random pass rate
py -c "import json; d=json.load(open('results/test_w4_1_baselines/baselines_report.json')); assert d['A_pass_rate'] >= d['B_pass_rate'], f'Evidence ({d['A_pass_rate']}) worse than Random ({d['B_pass_rate']})'"
```
**Expected**: Script runs, assertion passes, `baselines_summary.md` created.
### A11. Paired Faithfulness Smoke (W4.2)
Verify paired metrics and dominance rate.
```powershell
py scripts/13_w4_faithfulness_baselines.py --checkpoint temp_model --temperature_json results/week2_sanitized/calibration/temperature_scaling.json --label_map data/processed/reddit_mh_sanitized/labels.json --dataset_file data/processed/reddit_mh_sanitized/val.jsonl --preds_file results/week2_sanitized/calibration/preds_val_calibrated.jsonl --out_dir results/test_w4_2_paired --sample_n 30
# Assertion: Report contains dominance rate
py -c "import json; d=json.load(open('results/test_w4_2_paired/paired_faithfulness_report.json')); assert 'paired_dominance_rate' in d"
```
**Expected**: `paired_faithfulness_report.md` created with CI stats.
### A12. E2E Contract Runner Smoke (W5)
Verify schema validity, abstention, and batch processing.

**1. Single Input (Valid)**
```powershell
py scripts/14_run_e2e_contract_v1.py --checkpoint temp_model --temperature_json results/week2_sanitized/calibration/temperature_scaling.json --label_map data/processed/reddit_mh_sanitized/labels.json --text "I feel extremely anxious and cannot sleep because of panic attacks." --output_file results/test_w5_single.json
# Assertion: Valid Schema
py -c "import json; d=json.load(open('results/test_w5_single.json')); assert d['version']=='v1'; assert isinstance(d['labels'], list)"
```

**2. Abstention (Empty Input)**
```powershell
py scripts/14_run_e2e_contract_v1.py --checkpoint temp_model --temperature_json results/week2_sanitized/calibration/temperature_scaling.json --label_map data/processed/reddit_mh_sanitized/labels.json --text "   " --output_file results/test_w5_abstain.json
# Assertion: Abstain=True
py -c "import json; d=json.load(open('results/test_w5_abstain.json')); assert d['abstain']['is_abstain'] is True"
```

**3. Batch Mode**
```powershell
py scripts/14_run_e2e_contract_v1.py --checkpoint temp_model --temperature_json results/week2_sanitized/calibration/temperature_scaling.json --label_map data/processed/reddit_mh_sanitized/labels.json --input_jsonl results/dummy_w5.jsonl --out_jsonl results/test_w5_batch.jsonl --max_len 128
# Assertion: Output exists
py -c "import os; assert os.path.exists('results/test_w5_batch.jsonl')"
```

### A13. Evidence Method Switch (W5.1)
Verify GradxInput and IG execution.
```powershell
# 1. Default (GradxInput)
py scripts/12_explain_evidence.py --checkpoint temp_model --temperature_json results/week2_sanitized/calibration/temperature_scaling.json --label_map data/processed/reddit_mh_sanitized/labels.json --dataset_file data/processed/reddit_mh_sanitized/val.jsonl --preds_file results/week2_sanitized/calibration/preds_val_calibrated.jsonl --out_dir results/test_w5_1_evidence --sample_n 10
# Assertion: Default method
py -c "import json; d=json.load(open('results/test_w5_1_evidence/evidence.jsonl')); assert d['metadata']['evidence_method'] == 'grad_x_input'"

# 2. Integrated Gradients
py scripts/12_explain_evidence.py --checkpoint temp_model --temperature_json results/week2_sanitized/calibration/temperature_scaling.json --label_map data/processed/reddit_mh_sanitized/labels.json --dataset_file data/processed/reddit_mh_sanitized/val.jsonl --preds_file results/week2_sanitized/calibration/preds_val_calibrated.jsonl --out_dir results/test_w5_1_ig --sample_n 5 --evidence_method integrated_gradients --ig_steps 4
# Assertion: IG method recorded
py -c "import json; d=json.load(open('results/test_w5_1_ig/evidence.jsonl')); assert d['metadata']['evidence_method'] == 'integrated_gradients'"
```

### A14. Occlusion Audit (W5.1)
Verify causal faithfulness audit.
```powershell
py scripts/15_occlusion_audit_w5_1.py --checkpoint temp_model --temperature_json results/week2_sanitized/calibration/temperature_scaling.json --label_map data/processed/reddit_mh_sanitized/labels.json --dataset_file data/processed/reddit_mh_sanitized/val.jsonl --preds_file results/week2_sanitized/calibration/preds_val_calibrated.jsonl --out_dir results/test_w5_1_audit --sample_n 10
# Assertion: Report exists and parses
py -c "import json; d=json.load(open('results/test_w5_1_audit/occlusion_audit.json')); assert 'dominance_rate' in d"
```

### A15. Verifier Smoke (W5/Validation)
Verify output contract checker.
```powershell
# Create dummy output
py -c "import json; json.dump({'version':'v1', 'labels':[], 'abstain':{'is_abstain':False, 'reasons':[]}, 'meta':{}, 'calibration':{}, 'model_info':{}}, open('results/dummy_verify.jsonl', 'w'))"
py scripts/23_week5_verify_outputs.py --input_file results/dummy_verify.jsonl --out_report results/dummy_verify_report.json
# Assertion: Report exists
py -c "import os; assert os.path.exists('results/dummy_verify_report.json')"
```

## Week 6: Freeze & Reproducibility

### A16. Freeze Runner Smoke (W6)
Verify deterministic batch execution.
```powershell
py scripts/30_week6_freeze_run.py --release_config configs/release/week6_freeze.json --sample_n 5 --out_dir results/test_w6_freeze_smoke
# Assertion: Manifest exists
py -c "import os; assert os.path.exists('results/test_w6_freeze_smoke/manifest.json')"
```

### A17. Golden Regression Check (W6)
Verify zero regression on golden set.
```powershell
py scripts/31_week6_golden_check.py --release_config configs/release/week6_freeze.json
# Expected: Exit code 0, "Golden Regression PASSED"
```


