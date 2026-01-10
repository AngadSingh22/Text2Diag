def extract_spans(attributions, raw_text, k=12, max_spans=3):
    """
    Selects evidence spans from token attributions.
    
    Args:
        attributions: List of {token, score, start, end, token_idx}
        raw_text: Original text string
        k: Top-k tokens to consider (default 12)
        max_spans: Maximum number of spans to return (default 3)
        
    Returns:
        List[Dict]: List of {start, end, snippet, score, tokens}
    """
    # 1. Filter for positive attribution (evidence FOR the label)
    pos_attrs = [a for a in attributions if a["score"] > 0]
    
    # 2. Sort by score descending and take top K
    top_k = sorted(pos_attrs, key=lambda x: x["score"], reverse=True)[:k]
    
    # 3. Sort by token index to group them physically
    top_k_indices = sorted(top_k, key=lambda x: x["token_idx"])
    
    if not top_k_indices:
        return []
    
    spans = []
    current_span = None
    
    for item in top_k_indices:
        # Skip special tokens (heuristic: [CLS], [SEP], or offsets (0,0) if not start)
        # We'll rely on text-based check for standard BERT tokens + (0,0) check
        if item["token"] in ["[CLS]", "[SEP]", "[PAD]", "<s>", "</s>"]:
            continue
        if item["start"] == 0 and item["end"] == 0 and item["token_idx"] != 0: 
             # Safe guard for weird tokens, but keeping index 0 (CLS) out is key
             continue
        if item["token_idx"] == 0 and item["end"] == 0: # Explicit CLS check
             continue

        if current_span is None:
            current_span = {
                "start": item["start"],
                "end": item["end"],
                "score": item["score"],
                "tokens": [item["token"]]
            }
        else:
            # Merge if adjacent (or close enough, e.g. 1 char gap for space)
            # Tokenizer offsets are into original string.
            # Example: "hello world" -> "hello", "world". hello=(0,5), world=(6,11). Gap is 1.
            # If gap <= 1, merge.
            if item["start"] <= current_span["end"] + 1:
                current_span["end"] = max(current_span["end"], item["end"])
                current_span["score"] += item["score"]
                current_span["tokens"].append(item["token"])
            else:
                spans.append(current_span)
                current_span = {
                    "start": item["start"],
                    "end": item["end"],
                    "score": item["score"],
                    "tokens": [item["token"]]
                }
    
    if current_span:
        spans.append(current_span)
    
    # 4. Sort spans by total score and limit
    spans = sorted(spans, key=lambda x: x["score"], reverse=True)[:max_spans]
    
    # 5. Extract snippets
    for s in spans:
        snippet = raw_text[s["start"]:s["end"]]
        # Scrub
        snippet = snippet.replace("\n", " ").replace("\r", " ").strip()
        # Truncate
        if len(snippet) > 200:
            snippet = snippet[:197] + "..."
        s["snippet"] = snippet
        
    return spans
