#!/usr/bin/env python3
"""
Threshold Decision Layer.

Applies per-label or global thresholds to convert probabilities to predictions.
"""
import json
from typing import Dict, List, Optional, Union
import numpy as np

def load_thresholds(path: str) -> Dict[str, float]:
    """Load thresholds from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def apply_thresholds(
    probs: np.ndarray,
    thresholds_per_label: Dict[str, float],
    label_order: List[str],
    default_global: float = 0.5
) -> np.ndarray:
    """
    Apply per-label thresholds to probability array.
    
    Args:
        probs: (N, L) array of probabilities
        thresholds_per_label: dict mapping label name -> threshold
        label_order: list of label names in column order
        default_global: fallback threshold if label not in dict
    
    Returns:
        (N, L) binary prediction array
    """
    preds = np.zeros_like(probs, dtype=int)
    
    for i, label in enumerate(label_order):
        t = thresholds_per_label.get(label, default_global)
        preds[:, i] = (probs[:, i] > t).astype(int)
    
    return preds

def load_threshold_config(config_path: str) -> Dict:
    """Load threshold policy config from YAML."""
    import yaml
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
