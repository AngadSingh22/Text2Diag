"""
Attribution Components.
Calculates feature importance scores (gradients) for input tokens.
Now supports multiple methods: 'grad_x_input' (default) and 'integrated_gradients'.
"""
import torch
import numpy as np
from text2diag.explain.integrated_gradients import compute_integrated_gradients

def compute_attributions(model, tokenizer, text, label_idx, method="grad_x_input", device=None, **kwargs):
    """
    Dispatcher for attribution methods.
    
    Args:
        model: HF Model
        tokenizer: HF Tokenizer
        text: Input string
        label_idx: Target class index
        method: "grad_x_input" (default) or "integrated_gradients"
        device: torch device
        **kwargs: Extra args (e.g. max_len, steps)
        
    Returns:
        List[Dict]: Token attributions [{token, start, end, score}]
    """
    if method == "integrated_gradients":
        steps = kwargs.get("steps", 16)
        max_len = kwargs.get("max_len", 512)
        return compute_integrated_gradients(
            model, tokenizer, text, label_idx, 
            steps=steps, max_len=max_len, device=device
        )
    elif method == "grad_x_input":
        # Call legacy/default implementation
        # For simplicity, we just call the local function logic directly or wrapping it.
        # Since I am rewriting the file, I'll keep the logic below but wrapped.
        return compute_input_gradients(model, tokenizer, text, label_idx, device=device, **kwargs)
    else:
        raise ValueError(f"Unknown attribution method: {method}")

def compute_input_gradients(model, tokenizer, text, label_idx, device=None, max_len=512, **kwargs):
    """
    Computes Gradient x Input attribution.
    """
    if device is None:
        device = model.device

    # 1. Tokenize
    inputs = tokenizer(
        text, 
        return_tensors="pt", 
        truncation=True, 
        max_length=max_len,
        return_offsets_mapping=True
    ).to(device)
    
    input_ids = inputs["input_ids"]
    attention_mask = inputs["attention_mask"]
    
    # 2. Get Embeddings & Register Hook
    # Backbone-Agnostic approach
    if hasattr(model, "get_input_embeddings"):
        embed_layer = model.get_input_embeddings()
    elif hasattr(model.config, "embedding_layer_name"):
         raise ValueError("Model specific hook required")
    else:
        embed_layer = model.get_input_embeddings()
        
    inputs_embeds = embed_layer(input_ids)
    inputs_embeds.retain_grad()
    
    # 3. Forward Pass
    # We must pass inputs_embeds to allow gradient flow back to it
    out = model(inputs_embeds=inputs_embeds, attention_mask=attention_mask)
    logits = out.logits
    
    # 4. Backward Pass (Target Class)
    model.zero_grad()
    score = logits[0, label_idx]
    score.backward()
    
    # 5. Compute Attr = Input * Grad
    grads = inputs_embeds.grad
    if grads is None:
         raise RuntimeError("Gradients were None! Model might not support inputs_embeds training path.")
    # 6. Map to tokens
    tokens = tokenizer.convert_ids_to_tokens(input_ids[0])
    
    results = []
    for i, (token, score) in enumerate(zip(tokens, attr_scores)):
        start, end = offset_mapping[i]
        
        # Check assertions
        if start == 0 and end == 0:
             # Typically special tokens or padding. 
             # We let span builder filter them, but note it here.
             pass
             
        results.append({
            "token": token,
            "score": float(score),
            "start": int(start),
            "end": int(end),
            "token_idx": i
        })
        
    return results
