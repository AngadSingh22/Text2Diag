"""
Week 5: Output Validator.
Checks if an output object conforms to SCHEMA_V1 strictness.
"""
def validate_output(obj):
    """
    Validates the structure and constraints of the output object.
    
    Returns:
        (is_valid (bool), errors (List[str]))
    """
    errors = []
    
    # 1. Top Level Keys
    required_keys = ["version", "model_info", "calibration", "labels", "abstain", "meta"]
    for k in required_keys:
        if k not in obj:
            errors.append(f"Missing top-level key: {k}")
            
    if errors:
        return False, errors
        
    # 2. Version
    if obj["version"] != "v1":
        errors.append(f"Invalid version: {obj.get('version')}")
        
    # 3. Model Info
    if not isinstance(obj["model_info"], dict):
        errors.append("model_info must be a dict")
        
    # 4. Calibration
    if not isinstance(obj["calibration"], dict):
        errors.append("calibration must be a dict")
        
    # 5. Abstain
    if not isinstance(obj["abstain"], dict):
        errors.append("abstain must be a dict")
    else:
        if not isinstance(obj["abstain"].get("is_abstain"), bool):
            errors.append("abstain.is_abstain must be bool")
        if not isinstance(obj["abstain"].get("reasons"), list):
            errors.append("abstain.reasons must be list")
            
    # 6. Labels
    if not isinstance(obj["labels"], list):
        errors.append("labels must be a list")
    else:
        for i, lbl in enumerate(obj["labels"]):
            if not isinstance(lbl, dict):
                errors.append(f"Label {i} is not a dict")
                continue
                
            # Check fields
            if "name" not in lbl: errors.append(f"Label {i} missing name")
            if "prob_calibrated" not in lbl: errors.append(f"Label {i} missing prob")
            if "decision" not in lbl: errors.append(f"Label {i} missing decision")
            
            # Check constraints
            p = lbl.get("prob_calibrated", -1)
            if not isinstance(p, (float, int)) or not (0.0 <= p <= 1.0):
                errors.append(f"Label {i} prob_calibrated out of range [0,1]: {p}")
                
            d = lbl.get("decision", -1)
            if d not in [0, 1]:
                errors.append(f"Label {i} decision must be 0 or 1, got {d}")
                
            # Spans
            spans = lbl.get("evidence_spans", [])
            if not isinstance(spans, list):
                errors.append(f"Label {i} evidence_spans must be list")
            else:
                for j, s in enumerate(spans):
                    if len(s.get("snippet", "")) > 200:
                        errors.append(f"Label {i} span {j} snippet too long (>200 chars)")
                    if s.get("start", -1) < 0:
                        errors.append(f"Label {i} span {j} start < 0")
                    if s.get("end", -1) < s.get("start", -1):
                        errors.append(f"Label {i} span {j} end < start")
                        
    return len(errors) == 0, errors
