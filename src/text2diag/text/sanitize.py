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
        (clean_text, rules_applied_list, audit_meta)
    """
    if not text:
        return "", [], {"version": "sanitize_v2", "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}
        
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
    
    import hashlib
    content_hash = hashlib.sha256(text_clean.encode("utf-8")).hexdigest()
    
    audit_meta = {
        "version": "sanitize_v2",
        "sha256": content_hash
    }
    
    # If enabled but no rules triggered, mark as none_matched for clarity
    if (strip_urls or strip_reddit_refs) and not rules_applied:
        rules_applied.append("none_matched")
    
    return text_clean, rules_applied, audit_meta
