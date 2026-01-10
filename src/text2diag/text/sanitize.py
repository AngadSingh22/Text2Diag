"""
Text Sanitization Utils.
Implements policy-locked text cleaning rules.
"""
import re

REDDIT_REF_PATTERN = re.compile(r"/?r/\w+", re.IGNORECASE)
URL_PATTERN = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")

def sanitize_text(text, strip_urls=True, strip_reddit_refs=True, mask_diagnosis_words=False):
    """
    Sanitizes input text according to Week 2.6 policy.
    
    Returns:
        (clean_text, rules_applied_list)
    """
    if not text:
        return "", []
        
    rules_applied = []
    text_clean = text
    
    if strip_urls:
        if URL_PATTERN.search(text_clean):
            text_clean = URL_PATTERN.sub("", text_clean)
            rules_applied.append("strip_urls")
            
    if strip_reddit_refs:
        if REDDIT_REF_PATTERN.search(text_clean):
            text_clean = REDDIT_REF_PATTERN.sub("", text_clean)
            rules_applied.append("strip_reddit_refs")
            
    # Normalize whitespace
    text_clean = " ".join(text_clean.split())
    
    return text_clean, rules_applied
