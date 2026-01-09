# Sensitivity Analysis Report

**Threshold**: 0.5

## By Text Length Quartile

| Quartile | Count | Micro F1 | Macro F1 |
|----------|-------|----------|----------|
| Q1 (short) | 1441 | 0.809 | 0.7991 |
| Q2 | 1440 | 0.9191 | 0.9123 |
| Q3 | 1440 | 0.9325 | 0.9255 |
| Q4 (long) | 1440 | 0.9016 | 0.8882 |

## By Label Cardinality

| Cardinality | Count | Micro F1 | Macro F1 |
|-------------|-------|----------|----------|
| 1 label | 5648 | 0.8988 | 0.8907 |
| 2 labels | 111 | 0.6551 | 0.6198 |
| 3+ labels | 2 | 0.6667 | 0.3333 |

## By Label Type

| Type | Count | Micro F1 | Macro F1 |
|------|-------|----------|----------|
| condition_only | 5108 | 0.8984 | 0.7537 |
| other | 653 | 0.8363 | 0.1818 |
