"""
Unit tests for Reddit Canonical Dataset Build logic.
"""
import sys
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from text2diag.data.reddit_windows import (
    assign_user_split,
    get_label_info,
    derive_labels,
    normalize_text
)

def test_assign_user_split_deterministic():
    """Ensure split assignment is deterministic and respects fractions."""
    seed = 1337
    fracs = {"train": 0.8, "val": 0.1, "test": 0.1}
    
    # Check consistency
    assert assign_user_split("user1", seed, fracs) == assign_user_split("user1", seed, fracs)
    assert assign_user_split("user2", seed, fracs) == assign_user_split("user2", seed, fracs)
    
    # Check simple distribution (approximate)
    counts = {"train": 0, "val": 0, "test": 0}
    for i in range(1000):
        s = assign_user_split(f"user{i}", seed, fracs)
        counts[s] += 1
        
    # Relaxes assertions to avoid flakiness on small N, but roughly 800/100/100
    assert 750 < counts["train"] < 850
    assert 50 < counts["val"] < 150
    assert 50 < counts["test"] < 150

def test_normalize_text():
    assert normalize_text(" Title ", " Body ") == "Title\nBody"
    assert normalize_text(None, "Body") == "Body"
    assert normalize_text("Title", "") == "Title"
    assert normalize_text("   ", "   ") == ""

def test_label_policy_logic():
    policy = {
        "generic_map": {"mentalhealth": "general_distress"},
        "unknown_subreddit_action": "keep_as_other",
        "other_label": "other_sub"
    }
    whitelist = {"adhd", "anxiety"}
    
    # Condtion Whitelist
    l, t = get_label_info("Adhd", policy, whitelist)
    assert l == "adhd" and t == "condition"
    
    l, t = get_label_info("r/Anxiety", policy, whitelist)
    assert l == "anxiety" and t == "condition"
    
    # Generic Map
    l, t = get_label_info("mentalhealth", policy, whitelist)
    assert l == "general_distress" and t == "generic"
    
    # Other
    l, t = get_label_info("gaming", policy, whitelist)
    assert l == "other_sub" and t == "other"
    
    # Drop policy
    policy_drop = {**policy, "unknown_subreddit_action": "drop"}
    l, t = get_label_info("gaming", policy_drop, whitelist)
    assert l is None and t is None

def test_derive_labels():
    policy = {"generic_map": {"mh": "gen"}, "unknown_subreddit_action": "drop"}
    whitelist = {"a"}
    
    # Window with mix
    subs = ["a", "mh", "gaming"]
    labels, types, sources = derive_labels(subs, policy, whitelist)
    
    assert "a" in labels
    assert "gen" in labels
    assert "condition" in types
    assert "generic" in types
    assert "gaming" not in sources # dropped
    assert "a" in sources
    assert "mh" in sources
