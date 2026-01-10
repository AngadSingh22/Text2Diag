"""
Week 5: Output Repair.
Attempts to fix common validation errors.
"""
import copy

def repair_output(obj, errors=None):
    """
    Attempts to repair the object to comply with SCHEMA_V1.
    
    Returns:
        (repaired_obj, is_repaired (bool), remaining_errors (List[str]))
    """
    # Clone to avoid mutating original
    fixed = copy.deepcopy(obj)
    repaired = False
    
    # 1. Probs Clamping
    if "labels" in fixed and isinstance(fixed["labels"], list):
        for lbl in fixed["labels"]:
            if isinstance(lbl, dict):
                # Clamp Prob
                if "prob_calibrated" in lbl:
                    p = lbl["prob_calibrated"]
                    if isinstance(p, (float, int)):
                        if p < 0.0: 
                            lbl["prob_calibrated"] = 0.0
                            repaired = True
                        if p > 1.0: 
                            lbl["prob_calibrated"] = 1.0
                            repaired = True
                            
                # Coerce Decision
                if "decision" in lbl:
                    d = lbl["decision"]
                    if isinstance(d, bool):
                        lbl["decision"] = 1 if d else 0
                        repaired = True
                        
                # Fix Spans
                if "evidence_spans" in lbl and isinstance(lbl["evidence_spans"], list):
                    valid_spans = []
                    for s in lbl["evidence_spans"]:
                        # Truncate snippet
                        if "snippet" in s and len(s["snippet"]) > 200:
                            s["snippet"] = s["snippet"][:197] + "..."
                            repaired = True
                        
                        # Filter invalid offsets
                        if s.get("start", -1) >= 0 and s.get("end", -1) >= s.get("start", 0):
                            valid_spans.append(s)
                        else:
                            repaired = True # Dropped bad span
                            
                    lbl["evidence_spans"] = valid_spans
                    
    # Re-validate
    from text2diag.contract.validate import validate_output
    ok, new_errors = validate_output(fixed)
    
    return fixed, repaired, new_errors
