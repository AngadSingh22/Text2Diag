# Leakage Analysis Report (Lightweight)

> **Note**: This is a text-only analysis. Actual F1 deltas require GPU inference.

## Sanitization Impact

### VAL
- Total examples: 5761
- Examples affected by sanitization: 250 (4.34%)
- Reddit refs removed: 141
- URLs removed: 219
- Avg character reduction: 0.68%

### TEST
- Total examples: 5811
- Examples affected by sanitization: 258 (4.44%)
- Reddit refs removed: 148
- URLs removed: 192
- Avg character reduction: 0.72%

## Expected Impact

Based on W2.5 shortcut audit, **62.39%** of examples contained shortcuts.

> [!WARNING]
> **Provisional Verdict**: LIKELY SHORTCUT DEPENDENCE
>
> The high leak rate suggests the model may be relying on reddit-specific cues.
> Run full evaluation with GPU to measure actual F1 drop.

## Next Steps

1. Run `scripts/09_eval_sanitized.py` on **Google Colab** (with GPU)
2. If F1 drops >10%, rebuild dataset with sanitization baked in
3. Retrain model on sanitized data
