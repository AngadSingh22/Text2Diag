"""
Integrated Gradients Attribution.
Implements the path-integrated gradient attribution method.
"""
import torch
import numpy as np

def compute_integrated_gradients(model, tokenizer, text, label_idx, steps=16, max_len=512, device=None):
    """
    Computes attribution using Integrated Gradients w.r.t input embeddings.
    
    Args:
        model: HuggingFace model
        tokenizer: HuggingFace tokenizer
        text: Input text
        label_idx: Target label index
        steps: Number of integral steps (default 16)
        max_len: Max sequence length
        device: Torch device
        
    Returns:
        List[Dict]: TokenAttribution objects {token, start, end, score}
    """
    if device is None:
        device = model.device

    # 1. Tokenize (Offset Mapping Required)
    encoding = tokenizer(
        text, 
        return_offsets_mapping=True, 
        max_length=max_len, 
        truncation=True, 
        return_tensors="pt"
    )
    input_ids = encoding["input_ids"].to(device) # [1, Seq]
    attention_mask = encoding["attention_mask"].to(device)
    offsets = encoding["offset_mapping"][0].cpu().numpy()
    tokens = tokenizer.convert_ids_to_tokens(input_ids[0])
    
    # 2. Prepare Embeddings
    # Get generic embedding layer
    if hasattr(model, "get_input_embeddings"):
        embed_layer = model.get_input_embeddings()
    elif hasattr(model.config, "embedding_layer_name"):
         # specific hook if needed, but get_input_embeddings usually works
         raise ValueError("Model does not support get_input_embeddings")
    else:
        # Fallback for generic transformers
        embed_layer = model.get_input_embeddings()
        
    input_embeds = embed_layer(input_ids) # [1, Seq, Dim]
    
    # Baseline: Zero Embeddings (or Pad). 
    # Using Zero for simplicity and broad compatibility unless Pad is strictly required. 
    # For text, baseline is often 0 or PAD. User suggested PAD, but 0 is numerically cleaner for IG usually.
    # However, user prompt said "Option A: baseline embeddings = all [PAD] tokens... preferred for simplicity".
    # Let's try PAD baseline.
    pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else 0
    baseline_ids = torch.full_like(input_ids, pad_id)
    baseline_embeds = embed_layer(baseline_ids)
    
    # 3. Path Integration
    # We need gradients for scaled inputs
    # inputs = baseline + alpha * (input - baseline)
    
    # Create alphas [1, steps] -> [steps, 1, 1]
    alphas = torch.linspace(0, 1, steps, device=device).view(steps, 1, 1)
    
    # Expand embeddings for batch processing if memory allows, 
    # OR loop. steps=16 is small enough to batch usually.
    # delta = input - baseline
    delta_embeds = input_embeds - baseline_embeds # [1, Seq, Dim]
    
    # Shape: [steps, Seq, Dim]
    # interpolated[k] = baseline + alpha[k] * delta
    # We need to compute gradients W.R.T these interpolated embeddings.
    
    # We'll do a loop to be safe with memory and graph retention
    grads_accum = torch.zeros_like(input_embeds)
    
    # We can probably batch this. 
    # [steps, Seq, Dim]
    interpolated_embeds = baseline_embeds + alphas * delta_embeds 
    
    # Turn on gradients for leaf checking? 
    # Actually we pass inputs_embeds to model. We need to retain grad on this tensor.
    interpolated_embeds.retain_grad()
    
    # Create matched attention masks [steps, Seq]
    # Attention mask should probably remain 1 for the real tokens? 
    # If we use PAD baseline, attention mask for baseline is technically 0?
    # Usually IG keeps structure constant (mask=1 where text is).
    expanded_mask = attention_mask.expand(steps, -1)
    
    # Forward Pass (Batched)
    # We might need to split if steps is large, but 16 is fine.
    out = model(inputs_embeds=interpolated_embeds, attention_mask=expanded_mask)
    logits = out.logits # [steps, NumLabels]
    
    # Target Score
    target_scores = logits[:, label_idx]
    
    # Backward
    # Sum scores to backprop in one go
    total_score = torch.sum(target_scores)
    total_score.backward()
    
    # Get gradients w.r.t interpolated_embeds
    grads = interpolated_embeds.grad # [steps, Seq, Dim]
    
    # Approximate Integral
    # avg_grad = mean(grads)
    avg_grads = torch.mean(grads, dim=0, keepdim=True) # [1, Seq, Dim]
    
    # Attribution = (Input - Baseline) * AvgGrad
    attr_tensor = delta_embeds * avg_grads # [1, Seq, Dim]
    
    # Sum over embedding dimension -> [1, Seq]
    token_attrs = attr_tensor.sum(dim=-1)[0] # [Seq]
    token_attrs_np = token_attrs.detach().cpu().numpy()
    
    # 4. Pack Results
    attributions = []
    
    for i, token in enumerate(tokens):
        score = float(token_attrs_np[i])
        
        # Filter special tokens/padding if desired, or keep raw. 
        # Strategy: Keep raw, let SpanBuilder filter.
        # But offsets (-1,-1) or (0,0) for specials need handling.
        start, end = offsets[i]
        
        # Guard against special tokens having (0,0)
        if start == 0 and end == 0:
            pass # Keep it, SpanBuilder filters by score/text usually.
            
        attributions.append({
            "token": token,
            "start": int(start),
            "end": int(end),
            "score": score,
            "token_idx": i
        })
        
    return attributions
