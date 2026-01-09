# Threshold Policy (Week 2.6)

> **Status**: LOCKED as of 2026-01-10

## Policy Summary

This document defines the **operational decision layer** for converting model probabilities to binary predictions.

## Threshold Values

| Label | Threshold | Source |
|-------|-----------|--------|
| adhd | 0.45 | W2.5 per-label sweep |
| depression | 0.45 | W2.5 per-label sweep |
| ocd | 0.40 | W2.5 per-label sweep |
| other | 0.50 | W2.5 per-label sweep |
| ptsd | 0.60 | W2.5 per-label sweep |

**Fallback Global Threshold**: 0.45 (micro-F1 optimized)

## Why Per-Label Thresholds?

1. **Class Imbalance**: Different labels have different base rates. PTSD (lower support) benefits from a higher threshold to reduce false positives.
2. **Optimized F1**: Each threshold was chosen to maximize that label's individual F1 score on the validation set.
3. **Flexibility**: Per-label thresholds outperform a single global threshold on macro-F1.

## Important Disclaimer

> [!CAUTION]
> **Probabilities are NOT calibrated.**
> 
> The raw sigmoid outputs from the model do NOT represent true probabilities of a condition.
> This threshold policy is a **decision layer only** and does not provide calibrated risk estimates.
> 
> Do NOT interpret a 0.75 output as "75% chance of ADHD".

## Usage

```python
from text2diag.decision import load_thresholds, apply_thresholds

thresholds = load_thresholds("results/week2/audits/thresholds_per_label.json")
preds = apply_thresholds(probs, thresholds, label_order=["adhd", "depression", "ocd", "other", "ptsd"])
```

## Files

- `results/week2/audits/thresholds_per_label.json`: Per-label thresholds
- `results/week2/audits/thresholds_global.json`: Global fallback
- `configs/threshold_policy.yaml`: Policy configuration
