"""
# Zenodo RMHD Validation Pipeline (Colab Compatible)
# This script orchestrates the external validation on Reddit Mental Health Dataset (Low et al., 2020).
# User is expected to run this in Google Colab.

# 1. Setup
!git clone https://github.com/YourRepo/Text2Diag.git
%cd Text2Diag
!pip install -r requirements.txt
!pip install transformers torch numpy pandas scikit-learn

import sys
import os
sys.path.append("src")

# 2. Download Data (Placeholder - User must upload or wget real data)
# Use scripts/20_rmhd_download_subset.py (which is currently a template)
# Assume data is in data/external/rmhd_raw/
!mkdir -p data/external/rmhd_raw
# Manually upload or download CSVs to data/external/rmhd_raw/

# 3. Build JSONL
!python scripts/21_rmhd_build_jsonl.py \
  --data_dir data/external/rmhd_raw \
  --out_file data/external/rmhd_raw/rmhd_full.jsonl \
  --label_map configs/external/rmhd_label_mapping.json \
  --sample_n 5000

# 4. Leakage Report (Audit)
!python scripts/22_rmhd_leakage_report.py \
  --input_file data/external/rmhd_raw/rmhd_full.jsonl \
  --out_dir results/external/rmhd_audit

# 5. Strict Sanitization (Preprocessing)
# We apply this explicitly to create the inference input
import json
from tqdm import tqdm
from text2diag.preprocess.sanitize_external import sanitize_text_strict

input_file = "data/external/rmhd_raw/rmhd_full.jsonl"
sanitized_file = "data/external/rmhd_sanitized.jsonl"

print("Sanitizing...")
with open(input_file, "r") as f_in, open(sanitized_file, "w") as f_out:
    for line in tqdm(f_in):
        row = json.loads(line)
        row["text"] = sanitize_text_strict(row["text"])
        # We assume labels remain valid (weak labels from subreddits)
        f_out.write(json.dumps(row) + "\n")

# 6. Run Week 5 E2E Batch Runner
# Note: Ensure checkpoint is available (e.g. from Drive)
CHECKPOINT = "temp_model" # Replace with actual path
!python scripts/14_run_e2e_contract_v1.py \
  --checkpoint {CHECKPOINT} \
  --temperature_json results/week2_sanitized/calibration/temperature_scaling.json \
  --label_map data/processed/reddit_mh_sanitized/labels.json \
  --input_jsonl data/external/rmhd_sanitized.jsonl \
  --out_jsonl results/external/rmhd_e2e_outputs.jsonl \
  --include_dependency_graph \
  --skip_sanitization

# 7. Verification
!python scripts/23_week5_verify_outputs.py \
  --input_file results/external/rmhd_e2e_outputs.jsonl \
  --out_report results/external/rmhd_verification.json

# 8. Evaluation Metrics
!python scripts/24_rmhd_eval_metrics.py \
  --pred_file results/external/rmhd_e2e_outputs.jsonl \
  --gold_file data/external/rmhd_raw/rmhd_full.jsonl \
  --out_dir results/external/rmhd_metrics

print("Validation Complete. Check results/external/")
"""
