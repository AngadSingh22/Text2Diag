import torch
import numpy as np

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def verify_faithfulness(model, tokenizer, text, spans, label_idx, temperature=1.0, device=None):
    """
    Verifies evidence by deleting spans and checking probability drop.
    
    Args:
        model: HuggingFace model
        tokenizer: HuggingFace tokenizer
        text: Original text
        spans: List of spans to mask
        label_idx: Target label index
        temperature: Calibration temperature (default 1.0)
        device: Torch device (defaults to model.device)
        
    Returns:
        Dict: {p_full, p_masked, delta, pass}
    """
    if device is None:
        device = model.device
        
    # 1. Full Prediction
    # We use basic tokenization parameters compatible with training
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to(device)
    with torch.no_grad():
        logits = model(**inputs).logits
    
    full_logit = logits[0, label_idx].item()
    p_full = sigmoid(full_logit / temperature)
    
    # 2. Mask Spans (Union Deletion)
    chars = list(text)
    for span in spans:
        start = span["start"]
        end = span["end"]
        # Basic bounds check
        start = max(0, start)
        end = min(len(chars), end)
        
        # Replace with whitespace (neutral padding)
        # This preserves offsets for debugging but removes information
        for i in range(start, end):
            chars[i] = " "
            
    masked_text = "".join(chars)
    
    # 3. Masked Prediction
    inputs_masked = tokenizer(masked_text, return_tensors="pt", truncation=True, max_length=512).to(device)
    with torch.no_grad():
        logits_masked = model(**inputs_masked).logits
        
    masked_logit = logits_masked[0, label_idx].item()
    p_masked = sigmoid(masked_logit / temperature)
    
    delta = p_full - p_masked
    
    # Pass criterion: Union delta >= 0.03 AND delta >= 0
    passed = (delta >= 0.03)
    
    status = "failed_low_delta"
    flag = None
    
    if passed:
        status = "passed"
    elif delta < 0:
        status = "suspicious_negative_delta"
        flag = "negative_delta_suspicious"
    
    result = {
        "p_full": round(float(p_full), 4),
        "p_masked": round(float(p_masked), 4),
        "delta": round(float(delta), 4),
        "is_faithful": bool(passed),
        "faithfulness_status": status
    }
    
    if flag:
        result["flag"] = flag
        result["is_faithful"] = False # Enforce not faithful if negative
        
    return result
