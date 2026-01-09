# Week 2 Sanitized (Retrain) Summary

**Checkpoint**: `[INSERT_CHECKPOINT_ID]`
**Dataset Version**: `[INSERT_DATASET_HASH]`
**Baseline**: Week 2 (Old) vs Week 3 (Sanitized/Robust)

## Executive Summary
**Robustness Achieved?**: [YES/NO]
- **Shortcut Rate**: [X%] -> [Y%] (Target: <5%)
- **F1 Score**: [Baseline] -> [New] (Expected drop: ~10-15%)
- **Stability**: [Comment on whether model crashes on masked data]

## 1. Metrics Comparison

| Metric | Baseline (W2) | Robust (W3) | Delta |
|--------|---------------|-------------|-------|
| Micro F1 | 0.893 | [VAL] | [DELTA] |
| Macro F1 | 0.883 | [VAL] | [DELTA] |
| Micro AUC | [VAL] | [VAL] | [DELTA] |

### Per-Label Deltas (F1)
- **ADHD**: [OLD] -> [NEW] ([DELTA])
- **Depression**: [OLD] -> [NEW] ([DELTA])
- **OCD**: [OLD] -> [NEW] ([DELTA])
- **PTSD**: [OLD] -> [NEW] ([DELTA])
- **Other**: [OLD] -> [NEW] ([DELTA])

## 2. Audit Results
### A. Shortcut Leakage
- **Dataset Scan**: [PASS/FAIL] (Target: 0 reddit-specific tokens)

### B. Thresholds
- **Policy**: [Global/Per-Label]
- **Selected**:
  - Global: [VAL]
  - Per-Label: [JSON_DUMP]

### C. Error Analysis
**Top False Positives**:
1. ...
2. ...

**Top False Negatives**:
1. ...
2. ...

## 3. Conclusion & Next Steps
- [ ] Deploy Robust Model?
- [ ] Further Cleaning?
