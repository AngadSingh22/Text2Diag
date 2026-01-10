import torch
import numpy as np

def compute_input_gradients(model, tokenizer, text, label_idx, device=None):
    """
    Computes token attributions using Gradient x Input.
    
    Args:
        model: HuggingFace model (AutoModelForSequenceClassification)
        tokenizer: HuggingFace tokenizer
        text: Raw input string
        label_idx: Target label index to explain
        device: Torch device (defaults to model.device)
        
    Returns:
        List[Dict]: List of {token, score, start, end, token_idx}
    """
    if device is None:
        device = model.device
        
    # tokenize with offsets
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512, return_offsets_mapping=True)
    offset_mapping = inputs.pop("offset_mapping")[0].cpu().numpy()
    
    # Move to device
    inputs = {k: v.to(device) for k, v in inputs.items()}
    input_ids = inputs["input_ids"]
    
    # Identify embedding layer
    if hasattr(model, "distilbert"):
        embeddings_layer = model.distilbert.embeddings.word_embeddings
    elif hasattr(model, "bert"):
        embeddings_layer = model.bert.embeddings.word_embeddings
    elif hasattr(model, "roberta"):
        embeddings_layer = model.roberta.embeddings.word_embeddings
    else:
        # Fallback: try to find a module named 'word_embeddings'
        found = False
        for name, module in model.named_modules():
            if "word_embeddings" in name.lower() and isinstance(module, torch.nn.Embedding):
                embeddings_layer = module
                found = True
                break
        if not found:
            # Fallback 2: try 'embeddings' (could be a wrapper)
             for name, module in model.named_modules():
                if name.endswith("embeddings") and not name.endswith("position_embeddings") and not name.endswith("token_type_embeddings"):
                     # This is risky, but let's try to get the word embeddings from it if it has it
                     if hasattr(module, "word_embeddings"):
                         embeddings_layer = module.word_embeddings
                         found = True
                         break
        if not found:
            raise ValueError(f"Could not automatically find word_embeddings layer for model type {type(model)}")

    # Get embeddings with grad
    inputs_embeds = embeddings_layer(input_ids)
    inputs_embeds.retain_grad()
    
    # Construct inputs for forward pass
    # Exclude input_ids, include inputs_embeds
    model_inputs = {k: v for k, v in inputs.items() if k != "input_ids"}
    model_inputs["inputs_embeds"] = inputs_embeds
    
    # Zero gradients
    model.zero_grad()
    
    # Forward pass
    outputs = model(**model_inputs)
    logits = outputs.logits
    
    # Select target logit
    target_logit = logits[0, label_idx]
    
    # Backward pass
    target_logit.backward()
    
    # Get gradients
    grads = inputs_embeds.grad # (1, seq_len, hidden_dim)
    
    # Gradient x Input: (embed * grad).sum(dim=-1)
    attr_scores = (inputs_embeds * grads).sum(dim=-1).squeeze(0) # (seq_len)
    attr_scores = attr_scores.detach().cpu().numpy()
    
    # Map to tokens
    tokens = tokenizer.convert_ids_to_tokens(input_ids[0])
    
    results = []
    for i, (token, score) in enumerate(zip(tokens, attr_scores)):
        start, end = offset_mapping[i]
        results.append({
            "token": token,
            "score": float(score),
            "start": int(start),
            "end": int(end),
            "token_idx": i
        })
        
    return results
