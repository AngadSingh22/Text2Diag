"""
Week 5: Abstention Decision Logic.
Centralizes the decision to abstain based on safety and confidence.
"""

def decide_abstain(probs_map, labels_map, contract_ok, text_len, thresholds_map=None):
    """
    Decides whether to abstain from prediction.
    
    Args:
        probs_map: Dict {label: prob}
        labels_map: Dict {label_id: name}
        contract_ok: Bool (validation passed)
        text_len: Length of input text
        thresholds_map: Optional decision thresholds
        
    Returns:
        (is_abstain (bool), reasons (List[str]))
    """
    reasons = []
    
    # 1. Input Safety (Sanitization/Length)
    # If text became empty or too short after sanitization
    if text_len < 5:
        reasons.append("Input too short after sanitization")
        
    # 2. Contract Integrity
    if not contract_ok:
        reasons.append("Contract validation failed")
        
    # 3. Confidence Safety (Global Min)
    # If max probability across ALL labels is very low, we abstain globally
    # even if all are technically below threshold (predicting [0,0,0,0,0])
    # BUT prediction 0s is valid. 
    # Abstention is about "I don't know", not "I know it's nothing".
    # Here we define a "Confidence Floor" = 0.40.
    # If the model is not > 40% confident in ANY label, user might want an abstention.
    # However, strict contract allow predicting all zeros.
    # We'll use a soft check: if max(probs) < 0.2, maybe abstain?
    # Let's stick to user request: "Confidence too low (<0.40)"
    
    max_prob = max(probs_map.values()) if probs_map else 0.0
    if max_prob < 0.40:
        # Note: Predicting 'None' is valid, but 'Abstaining' means "Unsure".
        # If model outputs 0.3 for everything, it's unsure.
        reasons.append(f"Max confidence {max_prob:.2f} < 0.40")
        
    is_abstain = len(reasons) > 0
    return is_abstain, reasons
