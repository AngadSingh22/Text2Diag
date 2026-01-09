# Shortcut/Leakage Audit Report

**Overall**: ❌ FAIL

## Statistics

- Total Scanned: 20000
- Subreddit Mentions: 446
- URL Mentions: 449
- Examples with Any Leak: 12478 (62.39%)

## Label Mentions in Text

- `adhd`: 4269 (21.34%)
- `depression`: 2563 (12.81%)
- `ocd`: 3365 (16.82%)
- `other`: 4790 (23.95%)
- `ptsd`: 1995 (9.97%)

## Remediation Suggestions

- Strip 'r/<subreddit>' tokens from text
- Remove URLs
- Consider masking label names in text
