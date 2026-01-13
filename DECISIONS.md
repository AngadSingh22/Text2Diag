# DECISIONS – Change Log with Rationale

> **Rule**: Every significant change must be logged here with what/why/expected impact.

---

## 2026-01-09T22:28:02+05:30 – Step W1: Raw Dataset Inspection Setup

### What Changed
1. **`.gitignore`**: Added comprehensive exclusions for `data/`, `data/raw/`, `*.arrow`, model artifacts, and other large files
2. **`requirements.txt`**: Added `datasets>=2.0.0`, `pandas>=1.5.0`, `numpy>=1.21.0`, `pyarrow>=10.0.0`, `pytest>=7.0.0`
3. **`scripts/inspect_raw_datasets.py`**: New script to download and inspect raw datasets

### Why
- Need to download and analyze two datasets before any preprocessing:
  - `solomonk/reddit_mental_health_posts` (HuggingFace)
  - `MentalHelp` (GitHub repo)
- Must understand dataset structure (columns, types, missingness) before designing cleaning pipeline
- Data files must not be committed (too large), only code and small reports

### Expected Metric Impact
- **No model metrics yet** – this is data exploration phase
- **Deliverables**: Structure report (Markdown + JSON) documenting dataset schemas
- **Risk mitigation**: Understanding data shape early prevents downstream pipeline errors

---

## 2026-01-09T23:40:33+05:30 – Governance: Fast/Safe Execution Paths

### What Changed
1. **`AGENT_PROTOCOL.md`**: Added FAST PATH (default, lightweight) and SAFE PATH (merge/push) execution policies. Defined "relevant scope" to prevent full repo re-reads.
2. **`ACCEPTANCE_TESTS.md`**: Split tests into Tier A (smoke, <10s) and Tier B (full). Added copy-paste ready commands for both.
3. **`RUNLOG.md`**: Updated template to support short FAST PATH entries (3 lines) and full SAFE PATH entries. Added deferred logging to `results/runlogs/`.

### Why
Current governance caused slowness due to:
- Mandatory full repo reads on every action
- Full acceptance tests on every atomic commit
- Verbose RUNLOG entries even for trivial changes
- No caching or scope limitation

### Expected Metric Impact
- **Agent efficiency**: ~60% reduction in I/O per atomic step
- **Test time**: Smoke tier targets <10s vs ~30s+ for full suite
- **Auditability**: Preserved via SAFE PATH requirements before push
- **Risk**: None – SAFE PATH ensures full validation before merge

---

## 2026-01-10T00:10:22+05:30 – W1 Label Policy: Weak Labels + Taxonomy

### What Changed
Adopted a "Weak Label" strategy for Reddit data:
1. **Source**: Subreddit name = weak label signal.
2. **Taxonomy**:
    - **Conditions**: Only whitelisted subs (e.g., `ADHD`, `Anxiety`) map to condition labels.
    - **Generic**: Subs like `mentalhealth`, `depression_help` map to `general_distress`.
    - **Other**: Unknown subs map to `other` or are dropped.
3. **Abstention**: Model should learn to abstain or predict `general_distress` when evidence is ambiguous.

### Why
- **No Clinical Ground Truth**: We only have user self-reports/community membership.
- **Safety**: Avoiding "diagnosis" claims. Output is "user posts in r/ADHD-like context", not "user has ADHD".
- **Generic Handling**: Distinguishing general distress from specific conditions is critical for precision.

### Expected Metric Impact
- **Accuracy**: May be lower than "clean" labels but more realistic.
- **Calibration**: Expect higher uncertainty for `general_distress` inputs.

---

## 2026-01-10T02:00:00+05:30 – W2.5 Shortcut/Leakage Audit: FAIL

### What Changed
**Finding**: 62% of examples contain explicit subreddit references (e.g., "r/adhd", "r/depression") in the text.

### Why This Matters
- The model may be learning to detect "r/adhd" substring rather than actual ADHD symptom language.
- Real-world clinical text will not contain these reddit-specific tokens.
- Our 89% F1 may be inflated by this shortcut.

### Remediation (Deferred to Week 3)
1. **Token Stripping**: Add preprocessing step to remove `r/<subreddit>` patterns.
2. **URL Removal**: Strip all URLs.
3. **Robustness Eval**: Re-train or re-evaluate on masked data.

### Expected Metric Impact
- After remediation, F1 may drop significantly (10-30%) as model loses shortcut.
- True "diagnostic ability" will be measured.

---

## 2026-01-10T02:24:06+05:30 – W2.6 Policy Lock: Text Sanitization

### What Changed
**LOCKED**: Text sanitization rules for preprocessing:
1. `strip_urls`: Remove all `http(s)://` and `www.` patterns. **ON by default.**
2. `strip_reddit_refs`: Remove `r/<subreddit>`, `/r/<subreddit>` patterns. **ON by default.**
3. `mask_diagnosis_words`: Optional toggle to mask condition names. **OFF by default.**

### Why
- Addresses 62% shortcut leakage detected in W2.5.
- URLs and subreddit references are reddit-specific artifacts not present in real clinical text.
- Diagnosis word masking is optional as it may remove legitimate symptom discussions.

### Expected Metric Impact
- F1 may drop 10-30% if model relied on shortcuts.
- Establishes "true" model capability.

---

## 2026-01-10T02:24:06+05:30 – W2.6 Policy Lock: Threshold Decision Layer

### What Changed
**LOCKED**: Operational threshold policy:
- **Policy**: Per-label thresholds (from W2.5 sweep).
- **Values**: adhd=0.45, depression=0.45, ocd=0.40, other=0.50, ptsd=0.60
- **Fallback**: Global t=0.45 (micro-optimized).
- **Note**: Raw probabilities are always exported. Thresholds are a decision layer only.

### Why
- Per-label thresholds maximize per-class F1 given class imbalance.
- Explicit policy prevents ad-hoc threshold choices downstream.
- Disclaimer: Probabilities are NOT calibrated (no Week 3 work).

### Expected Metric Impact
- Improved per-label F1 vs fixed 0.5 threshold.
- No change to ranking metrics (AUC).

---

## 2026-01-10T05:05:00+05:30 – W3.1 Strategy Shift: Blind Training (Self-Labeling Remediation)

### What Changed
**Pivoted** from "Clean Inference" to "Blind Training":
1.  **Dataset**: Created `reddit_mh_sanitized` where ALL diagnosis words (ADHD, depression, etc.) are masked (`[MASK]`).
2.  **Training**: Retraining model on this masked dataset (Week 3 Robust Baseline).
3.  **Acceptance**: We accept that F1 scores will likely drop (e.g., to ~0.75).

### Why
- **Inference Evaluation (W2.6)** confirmed that the W2 model crashes when shortcuts are removed (Self-labeling dependency).
- Just masking at test time isn't enough; the model must learn to ignore shortcuts **during training** to learn actual symptom patterns.
- This establishes the **Honest Baseline**—the true performance ceiling of the model on symptom data alone.

### Expected Metric Impact
- **F1 Score**: Significant drop expected (0.89 -> ~0.75). This is a **success criteria** for robustness, not a failure.
- **Generalization**: Model should perform better on real-world (non-Reddit) clinical notes where patients don't announce their diagnosis.

---

## 2026-01-10T05:40:00+05:30 – Repo Normalization V1 (Cleanup)

### What Changed
1.  **Script Renaming**: `scripts/10_...` -> `scripts/05_...` (Renumbering to close gap).
2.  **Legacy Archival**: Moving `scripts/train.py`, `eval.py` etc -> `docs/legacy/scripts/` (Start fresh with numbered steps).
3.  **Module Rename**: `src/text2diag/modeling` -> `src/text2diag/decision` (Resolve ambiguity with `model`).

### Why
- **Clutter**: Root `scripts/` had 15+ files, half unused.
- **Sequence**: `10, 11, 12` implied missing steps 5-9.
- **Ambiguity**: `modeling` usually means Architecture (transformers style), but here contained `postprocess.py` (thresholds). `decision` is clearer.

### Expected Metric Impact
- None (refactor only).

---

## 2026-01-10T06:15:00+05:30 – Policy Lock: Week 2 Sanitized

### Decision
Locked decision thresholds for the Robust (Sanitized) Model:
- **Global Threshold**: 0.480 (Optimized on `val`)
- **Per-Label Policy**: See `results/week2_sanitized/policy/thresholds_per_label.json`

### Rationale
- Optimized for Micro-F1 on `data/processed/reddit_mh_sanitized/val.jsonl`.
- Shift from Baseline (0.35) due to different probability distribution in robust model (less overconfident on shortcuts).

### Metric Impact
- **Micro-F1**: 0.841 (Val), 0.839 (Test).
- **Leakage**: 0 detected shortcuts.

---

## 2026-01-10T11:45:00+05:30 – W4 Evidence Policy: Gradient x Input + Deletion Check

### Decision
1. **Attribution Method**: Gradient x Input on Embedding Layer.
2. **Span Selection**: Merge top-12 tokens into max 3 spans.
3. **Faithfulness Check**: Deletion Test (Mask spans and measure probability drop).
4. **Pass Criteria**: Delta >= 0.05 (any span) OR Delta >= 0.03 (all spans).

### Rationale
- **Gradient x Input**: Fast, deterministic, and sufficient for identifying salient tokens in Transformers.
- **Deletion Test**: The gold standard for faithfulness. If deleting "evidence" doesn't drop the score, it wasn't evidence.
- **Calibrated Probabilities**: Using W3 calibrated scores ensures deltas are meaningful (not raw logit noise).

### Expected Metric Impact
- **Metric**: Faithfulness Pass Rate (Target > 80%).
---

## 2026-01-10T12:00:00+05:30 – W4.1 Evidence Hardening

### Decision
1.  **Attribution**: Make `compute_input_gradients` backbone-agnostic by using `model.get_input_embeddings()` and `inputs_embeds` forward pass.
2.  **Offsets**: Source offsets strictly from tokenizer `return_offsets_mapping=True` on the *exact* inference text.
3.  **Baselines**: Introduce "Random-Span" and "Label-Shuffle" baselines to Contextualize faithfulness scores.

### Rationale
- **Hardcoding**: `model.distilbert.embeddings` breaks if we switch to BERT/RoBERTa/DeBERTa. The official HF API `get_input_embeddings` is safer.
- **Verification**: A 30% pass rate is meaningless without a baseline. Random spans allow us to see if the model is just generally sensitive to *any* deletion, or specifically to the extracted spans.

### Expected Metric Impact
- **Faithfulness**: We expect Evidence Spans > Random Spans > Label Shuffle (in terms of delta).

### Expected Metric Impact
- **Faithfulness**: We expect Evidence Spans > Random Spans > Label Shuffle (in terms of delta).

---

## 2026-01-10T12:15:00+05:30 – W4.2 Paired Faithfulness Metrics

### Decision
1.  **Metric Update**: Use **Paired Dominance Rate** (`P(delta_evidence > delta_random)`) and **Paired Mean Difference** as primary validation signals.
2.  **Reporting**: Report 95% Bootstrap CI for the mean difference.

### Rationale
- **Variance**: Individual examples vary wildly in sensitivity. Comparing group means ignores the intra-example correlation.
- **Robustness**: If Evidence > Random on 60% of examples, that's a signal, even if the mean difference is small due to outliers.

### Expected Metric Impact
- **Dominance Rate**: Target > 50% (better than random chance).
### Expected Metric Impact
- **Dominance Rate**: Target > 50% (better than random chance).

---

## 2026-01-10T12:20:00+05:30 – W5 Output Contract & Abstention

### Decision
1.  **Schema v1**: Strict JSON structure with mandatory `metadata`, `calibration`, `labels`, and `abstain` keys.
2.  **Repair Policy**: Auto-fix minor issues (probs float precision, snippet truncation). Critical failures = Abstain.
3.  **Abstention Triggers**: High priority (Safe > Robust > Helpful).
    - Confidence too low (<0.40).
    - Input too short/empty.
    - Leakage detected.

### Rationale
- **Deterministic Interface**: Downstream systems need guaranteed structure.
- **Fail-Safe**: Better to return `{"abstain": true}` than a hallucinated prediction on OOD input.

### Expected Metric Impact
- **Coverage**: Will decrease (abstentions).
- **Precision**: Should increase (filtering low-conf/short inputs).
### Expected Metric Impact
- **Coverage**: Will decrease (abstentions).
- **Precision**: Should increase (filtering low-conf/short inputs).

---

## 2026-01-10T17:55:00+05:30 – W5.1 Layered Evidence

### Decision
1.  **Default Method**: `grad_x_input` (Fast, Production).
2.  **Analysis Method**: `integrated_gradients` (Stable, Slow).
3.  **Audit Policy**: Occlusion Audit runs offline on samples, not per-inference.
4.  **Contract Stability**: Contract v1 remains unchanged; `evidence_meta` is optional.

### Rationale
- **Performance**: IG is 16x slower (default steps) than Grad×Input, too slow for real-time batch constraints if strict latency needed.
- **Robustness**: IG satisfies Axiomatic Attribution properties (sensitivity, implementation invariance), providing a ground-truth check for Grad×Input.

### Expected Metric Impact
- **Faithfulness**: IG spans might be slightly more faithful (higher delta) but at cost of compute.

---

## 2026-01-11T12:15:00+05:30 – External Validation Policy

### Decision
1.  **Dataset**: Zenodo RMHD (Low et al., 2020).
2.  **Leakage Policy**: Strict sanitization. Remove all diagnosis phrases, label tokens (synonyms), URLs, and reddit patterns.
3.  **Labeling**: Weak labeling via subreddit mapping. Non-mapped subreddits -> Control (all 0) or Other.
4.  **Metrics**: Compute F1/AUC only on mapped labels. Skip labels absent from dataset.
5.  **Dependency Graph**: Deterministic co-occurrence graph generation included in E2E validation.

### Rationale
- **Leakage**: External datasets often contain "I was diagnosed with X" which trivializes the task.
- **Dependency**: Required for Week 5 contract completeness check.

 
 # #   2 0 2 6 - 0 1 - 1 3 T 2 2 : 2 0 : 0 0 + 0 5 : 3 0   � �    D e - s c o p e   Z e n o d o   R M H D   E x t e r n a l   V a l i d a t i o n  
  
 # # #   D e c i s i o n  
 1 .     * * R e m o v e * * :   A l l   Z e n o d o / R M H D   s p e c i f i c   s c r i p t s ,   n o t e b o o k s ,   a n d   c o n f i g s .  
 2 .     * * P r e s e r v e * * :   C o r e   i n f r a s t r u c t u r e   a d d e d   d u r i n g   t h i s   p h a s e   ( C o n t r a c t   V e r i f i e r ,   D e p e n d e n c y   G r a p h   l o g i c ,   G e n e r i c   E 2 E   f l a g s ) .  
  
 # # #   R a t i o n a l e  
 -   * * F o c u s * * :   P r i o r i t i z e   s t a b i l i t y   a n d   r e p r o d u c i b i l i t y   o n   t h e   i n t e r n a l   d a t a s e t   ( W e e k   6   F r e e z e ) .  
 -   * * C o s t * * :   M a i n t a i n i n g   e x t e r n a l   d a t a   p i p e l i n e s   a d d s   i n s t a b i l i t y   ( U R L   r o t ,   a p p r o v a l   g a t e s ) .  
 -   * * V a l u e * * :   C o r e   l o g i c   ( d e p e n d e n c y   g r a p h ,   s a n i t i z a t i o n   f l a g s )   i s   v a l u a b l e   i n d e p e n d e n t   o f   t h e   e x t e r n a l   d a t a s e t .  
  
 # # #   M e t r i c   I m p a c t  
 -   N o n e   o n   i n t e r n a l   m e t r i c s .  
  
 # #   2 0 2 6 - 0 1 - 1 4 T 0 0 : 5 0 : 2 9 + 0 5 : 3 0   � �    W e e k   6   F r e e z e   &   L o c k  
  
 # # #   D e c i s i o n  
 1 .     * * F r e e z e * * :   T h e   " W e e k   6   F r e e z e "   r u n   i s   t h e   c a n o n i c a l   r e p r o d u c i b l e   o u t p u t   f o r   t h i s   v e r s i o n .  
 2 .     * * L o c k * * :   N o   c h a n g e s   t o   m o d e l   w e i g h t s   o r   d a t a   s p l i t s .   O n l y   p a c k a g i n g ,   d e t e r m i n i s m   f i x e s ,   a n d   r e g r e s s i o n   c o n t r o l s   a r e   a l l o w e d .  
 3 .     * * S c o p e * * :   S t r i c t l y   i n t e r n a l   d a t a s e t   ( W e e k   1   C a n o n i c a l ) .   N o   e x t e r n a l   v a l i d a t i o n .  
  
 # # #   R a t i o n a l e  
 -   * * S t a b i l i t y * * :   E n s u r e   f u t u r e   c h a n g e s   ( i f   a n y )   c a n   b e   r e g r e s s i o n - t e s t e d   a g a i n s t   a   k n o w n   g o o d   s t a t e .  
 -   * * R e p r o d u c i b i l i t y * * :   ` s c r i p t s / 3 0 _ w e e k 6 _ f r e e z e _ r u n . p y `   p r o v i d e s   a   s i n g l e   e n t r y   p o i n t   t h a t   g u a r a n t e e s   i d e n t i c a l   o u t p u t s   g i v e n   t h e   s a m e   e n v i r o n m e n t .  
  
 # # #   M e t r i c   I m p a c t  
 -   N o n e   ( L o g i c   i s   i d e n t i c a l   t o   W e e k   5   E 2 E ,   j u s t   p i n n e d ) .  
  
 # #   2 0 2 6 - 0 1 - 1 4 T 0 1 : 3 0 : 0 0 + 0 5 : 3 0   � �    W e e k   6   H a r d e n i n g   P o l i c i e s  
  
 # # #   D e c i s i o n  
 1 .     * * E x a m p l e   I D * * :   d e t e r m i n i s t i c   ( h a s h   o f   i n p u t )   i f   n o t   p r o v i d e d .  
 2 .     * * F a i t h f u l n e s s * * :   M u s t   u s e   c a l i b r a t e d   p r o b s .   N e g a t i v e   d e l t a   i s   f l a g g e d   " s u s p i c i o u s " .  
 3 .     * * T h r e s h o l d s * * :   E x p l i c i t   p r o v e n a n c e   r e q u i r e d   ( " s o u r c e "   f i e l d ) .  
 4 .     * * S a n i t i z a t i o n * * :   C o m p l e t e   a u d i t   t r a i l   ( v e r s i o n ,   r u l e s ,   h a s h )   r e q u i r e d .  
  
 # # #   R a t i o n a l e  
 -   * * A u d i t a b i l i t y * * :   W e   m u s t   k n o w   e x a c t l y   * w h y *   a   d e c i s i o n   w a s   m a d e   ( w h i c h   t h r e s h o l d ? )   a n d   * w h a t *   d a t a   w a s   u s e d   ( s a n i t i z a t i o n   h a s h ) .  
 -   * * C o r r e c t n e s s * * :   N e g a t i v e   e v i d e n c e   ( d e l t a   <   0 )   i m p l i e s   t h e   s p a n   * s u p p r e s s e d *   t h e   l a b e l ,   w h i c h   c o n t r a d i c t s   " e v i d e n c e " .  
  
 # # #   M e t r i c   I m p a c t  
 -   N o n e   o n   F 1 / A U C .   F a i t h f u l n e s s   p a s s   r a t e   m i g h t   d r o p   s l i g h t l y   d u e   t o   s t r i c t e r   n e g a t i v e   c h e c k s .  
 