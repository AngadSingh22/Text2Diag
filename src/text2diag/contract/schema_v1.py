"""
Week 5: Output Contract Schema (v1).
Defines the strict structure for model outputs.
"""

SCHEMA_V1 = {
    "version": "v1",
    "example_id": None, # Optional string
    "model_info": {
        "model_name": None,
        "checkpoint": None,
        "max_len": 512,
        "window_size": 3
    },
    "calibration": {
        "method": "temperature_scaling",
        "temperature": 1.0,
        "timestamp": None
    },
    "labels": [
        # List of objects like:
        # {
        #   "name": "adhd",
        #   "prob_calibrated": 0.85, (float 0-1)
        #   "decision": 1, (int 0 or 1)
        #   "threshold_used": 0.45,
        #   "evidence_spans": [{"start": 0, "end": 10, "snippet": "...", "score": 0.1}],
        #   "faithfulness": {"delta": 0.05, "pass": true}
        # }
    ],
    "abstain": {
        "is_abstain": False, # bool
        "reasons": [] # List[str]
    },
    "meta": {
        "created_at": None,
        "preprocessing": {
            "sanitized": False,
            "rules_applied": []
        }
    }
}
