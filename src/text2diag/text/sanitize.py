#!/usr/bin/env python3
"""
Text Sanitization Module.

Provides utilities to remove shortcuts/leakage from text:
- URLs
- Reddit references (r/subreddit, /r/subreddit)
- Optional diagnosis word masking
"""
import re
from typing import Dict, Any, List, Optional

def strip_urls(text: str) -> tuple[str, int]:
    """Remove URLs from text. Returns (cleaned_text, count_removed)."""
    pattern = r'https?://\S+|www\.\S+'
    matches = re.findall(pattern, text, re.IGNORECASE)
    cleaned = re.sub(pattern, '', text, flags=re.IGNORECASE)
    return cleaned.strip(), len(matches)

def strip_reddit_refs(text: str) -> tuple[str, int]:
    """Remove reddit references like r/subreddit, /r/subreddit. Returns (cleaned_text, count_removed)."""
    # Pattern matches: r/name, /r/name, "subreddit" mentions
    pattern = r'(?:/r/|r/)\w+'
    matches = re.findall(pattern, text, re.IGNORECASE)
    cleaned = re.sub(pattern, '', text, flags=re.IGNORECASE)
    # Also remove standalone "subreddit" which is boilerplate
    cleaned = re.sub(r'\bsubreddit\b', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip(), len(matches)

def mask_diagnosis_words(text: str, vocab: List[str], case_insensitive: bool = True) -> tuple[str, int]:
    """
    Replace diagnosis words with [MASK]. 
    Returns (masked_text, count_masked).
    """
    count = 0
    flags = re.IGNORECASE if case_insensitive else 0
    for word in vocab:
        pattern = rf'\b{re.escape(word)}\b'
        matches = re.findall(pattern, text, flags)
        count += len(matches)
        text = re.sub(pattern, '[MASK]', text, flags=flags)
    return text, count

def sanitize_text(text: str, cfg: Dict[str, Any]) -> tuple[str, Dict[str, int]]:
    """
    Apply sanitization in fixed order. Returns (sanitized_text, stats).
    
    Config keys:
    - strip_urls: bool
    - strip_reddit_refs: bool
    - mask_diagnosis_words: bool
    - diagnosis_vocab: List[str]
    - case_insensitive: bool
    """
    stats = {"urls_removed": 0, "reddit_refs_removed": 0, "diagnosis_words_masked": 0}
    
    if cfg.get("strip_urls", True):
        text, count = strip_urls(text)
        stats["urls_removed"] = count
    
    if cfg.get("strip_reddit_refs", True):
        text, count = strip_reddit_refs(text)
        stats["reddit_refs_removed"] = count
    
    if cfg.get("mask_diagnosis_words", False):
        vocab = cfg.get("diagnosis_vocab", [])
        case_insensitive = cfg.get("case_insensitive", True)
        text, count = mask_diagnosis_words(text, vocab, case_insensitive)
        stats["diagnosis_words_masked"] = count
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text, stats

def load_sanitize_config(path: str) -> Dict[str, Any]:
    """Load sanitization config from YAML file."""
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
