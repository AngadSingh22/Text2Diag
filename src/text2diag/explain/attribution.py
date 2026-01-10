import torch
import numpy as np

def compute_input_gradients(model, tokenizer, text, label_idx, device=None, max_len=512):
    """
    Computes token attributions using Gradient x Input.
    Backbone-agnostic implementation using inputs_embeds.
    
    Args:
        model: HuggingFace model
        tokenizer: HuggingFace tokenizer
        text: Raw input string
        label_idx: Target label index to explain
        device: Torch device (defaults to model.device)
        max_len: Maximum sequence length (must match inference)
        
    Returns:
        List[Dict]: List of {token, score, start, end, token_idx}
    """
    if device is None:
        device = model.device
        
    # 1. Tokenize with offsets (Critical for span mapping)
    # We insist on truncation=True and max_length to match inference conditions
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_len, return_offsets_mapping=True)
    offset_mapping = inputs.pop("offset_mapping")[0].cpu().numpy()
    
    # Move to device
    inputs = {k: v.to(device) for k, v in inputs.items()}
    input_ids = inputs["input_ids"]
    
    # 2. Get Embedding Layer Genericially
    try:
        embeddings_layer = model.get_input_embeddings()
    except AttributeError:
        # Final fallback for models that don't impl generic header (rare in HF)
        if hasattr(model, "distilbert"): embeddings_layer = model.distilbert.embeddings.word_embeddings
        elif hasattr(model, "bert"): embeddings_layer = model.bert.embeddings.word_embeddings
        elif hasattr(model, "roberta"): embeddings_layer = model.roberta.embeddings.word_embeddings
        else: raise ValueError(f"Could not find input embeddings for {type(model)}")
        
    # 3. Compute Embeddings & Retain Grad
    # We must do this manually to have a leaf tensor to differentiate w.r.t
    inputs_embeds = embeddings_layer(input_ids)
    inputs_embeds.retain_grad()
    
    # 4. Forward Pass with inputs_embeds
    # Exclude input_ids, use inputs_embeds instead
    model_inputs = {k: v for k, v in inputs.items() if k != "input_ids"}
    model_inputs["inputs_embeds"] = inputs_embeds
    
    # Zero gradients
    model.zero_grad()
    
    outputs = model(**model_inputs)
    logits = outputs.logits
    
    # 5. Gradient Computation
    target_logit = logits[0, label_idx]
    target_logit.backward()
    
    # Gradients w.r.t embeddings
    grads = inputs_embeds.grad # (1, seq_len, hidden_dim)
    
    if grads is None:
         # Fallback hook method would go here, but inputs_embeds usually works
         raise RuntimeError("Gradients were None! Model might not support inputs_embeds training path.")

    # Gradient x Input: (embed * grad).sum(dim=-1)
    attr_scores = (inputs_embeds * grads).sum(dim=-1).squeeze(0) # (seq_len)
    attr_scores = attr_scores.detach().cpu().numpy()
    
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
