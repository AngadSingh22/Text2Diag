"""
Strict sanitization for external datasets to prevent label leakage.
Removes:
- URLs
- Reddit refs (r/, u/)
- Explicit diagnosis phrases ("diagnosed with X")
- Label tokens/synonyms (masked)
"""
import re
from typing import List, Dict, Tuple

DIAGNOSIS_PHRASES = [
    r"diagnosed with", r"my diagnosis is", r"i have", r"i'm", r"i am", 
    r"doctor said", r"therapist said", r"psychiatrist said"
]

# Label synonyms to mask
LABEL_SYNONYMS = {
    "adhd": ["adhd", "add", "attention deficit"],
    "depression": ["depression", "depressed", "major depressive disorder", "mdd"],
    "ptsd": ["ptsd", "post traumatic", "post-traumatic", "trauma"],
    "ocd": ["ocd", "obsessive compulsive", "obsessive-compulsive"],
    "anxiety": ["anxiety", "anxious", "gad", "social anxiety"],
    "bipolar": ["bipolar", "bp1", "bp2", "mania", "manic"],
    "schizophrenia": ["schizophrenia", "schizo", "psychosis", "psychotic"],
    "autism": ["autism", "autistic", "asd", "asperger", "aspergers"],
    "bpd": ["bpd", "borderline"]
}

def sanitize_text_strict(text: str) -> str:
    """
    Apply strict sanitization to text.
    Returns cleaned text with [MASKED_CONDITION] tokens.
    """
    if not isinstance(text, str):
        return ""
        
    text_clean = text.lower() # Normalize case for matching (output remains lower)
    
    # 1. Remove URLs
    text_clean = re.sub(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", "", text_clean)
    
    # 2. Remove Reddit Refs
    text_clean = re.sub(r"/?r/\w+", "", text_clean)
    text_clean = re.sub(r"/?u/\w+", "", text_clean)
    
    # 3. Mask Label Tokens (Stand-alone words)
    # We iterate all synonyms and replace whole words
    for label, synonyms in LABEL_SYNONYMS.items():
        for syn in synonyms:
            # \b matches word boundary
            pattern = re.compile(r'\b' + re.escape(syn) + r'\b')
            text_clean = pattern.sub("[MASKED_CONDITION]", text_clean)
            
    # 4. Diagnosis Phrases (Contextual)
    # The phrase itself + condition is often covered by (3) if condition is masked.
    # But "diagnosed with" alone is a strong signal if followed by [MASKED_CONDITION].
    # We might want to remove the specific phrases too to force symptom reliance.
    # User requirement: "Remove explicit diagnosis phrases that trivially leak labels"
    for phrase in DIAGNOSIS_PHRASES:
        # Match phrase roughly
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        # We replace with nothing or generic token?
        # Let's replace with something neutral to preserve grammar flow? 
        # Or just strip. User said "Remove".
        text_clean = pattern.sub("", text_clean)
        
    # Whitespace cleanup
    text_clean = " ".join(text_clean.split())
    
    return text_clean
