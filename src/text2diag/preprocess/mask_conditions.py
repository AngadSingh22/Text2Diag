"""
Condition Masking Module (Week 6+).
Prevents label leakage by masking explicit condition names in input text.
"""
import re
import hashlib

# Explicit condition names to mask
# Case-insensitive, whole word matching preferred
CONDITIONS = [
    "adhd", "add", 
    "depression", "depressed", "depressive",
    "anxiety", "anxious",
    "ptsd", "post traumatic stress", "post-traumatic stress",
    "ocd", "obsessive compulsive", "obsessive-compulsive",
    "bipolar", "mania", "manic",
    "suicide", "suicidal",
    "schizophrenia", "schizophrenic",
    "autism", "autistic"
]

# Regex generation
# Sort by length descending to match longest first ("post traumatic stress" before "ptsd")
CONDITIONS_SORTED = sorted(CONDITIONS, key=len, reverse=True)
PATTERN_STR = "|".join([re.escape(c) for c in CONDITIONS_SORTED])
# Use word boundaries, but also handle "r/" prefix if missed by sanitizer
# (r/adhd -> [COND])
MASK_REGEX = re.compile(r"(?:\br/)?\b(" + PATTERN_STR + r")\b", re.IGNORECASE)

def mask_condition_mentions(text):
    """
    Masks condition mentions with [COND].
    Args:
        text: Input text
    Returns:
        (masked_text, masks_list)
        masks_list is list of dicts: {original, start, end} (offsets in masked text?) 
        Actually, we usually track what was replaced.
    """
    if not text:
        return "", []
        
    masks = []
    
    def replacer(match):
        original = match.group(0)
        masks.append({
            "original": original,
            # We can't easily track offsets in the new string during regex sub without logic.
            # But the requirement says "offsets/evidence spans needed on masked_text".
            # So we just need the FINAL text. Tracking exact offsets of the mask itself is secondary audit.
            "replacement": "[COND]" 
        })
        return "[COND]"
        
    masked_text = MASK_REGEX.sub(replacer, text)
    
    return masked_text, masks
