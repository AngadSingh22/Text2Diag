# Reddit Canonical Dataset Report

**Generated**: 2026-01-10T00:13:07.048657

> **Safety Note**: Subreddit labels are weak proxies; outputs are not diagnoses; generic subs are treated as general distress; condition labels are only for condition-specific subs; abstention will be used downstream.

## 1. Summary Counts

- **Total Windows**: 57756
- **Unique Users**: 57756
- **Splits**: {'train': 46184, 'val': 5761, 'test': 5811}
- **Leakage Check**: PASS

## 2. Text Statistics (Chars)

- **Min**: 9
- **Median**: 841
- **P95**: 3740
- **Max**: 40125

## 3. Label Distribution (Top 20)

| Label | Count | % |
|---|---|---|
| `adhd` | 18531 | 32.08% |
| `ocd` | 12381 | 21.44% |
| `depression` | 11952 | 20.69% |
| `ptsd` | 8932 | 15.47% |
| `other` | 7117 | 12.32% |

## 4. Examples (Truncated)

**Example 1** (train):
- **Labels**: ['adhd'] (['condition'])
- **Text**: `I get extremely anxious if I’m not working 24/7 A few months ago I was accepted into this full time software engineering fellowship and it’s made me realize that I CANNOT work sustainably to save my l...`

**Example 2** (train):
- **Labels**: ['adhd'] (['condition'])
- **Text**: `I can't will myself to clean my own house, but feel incredibly motivated to clean my girlfriends place? Hey guys, I was curious if anyone else has the same issue as me. My apartment is a fucking pigst...`

**Example 3** (train):
- **Labels**: ['adhd'] (['condition'])
- **Text**: `i need some help i have 6 exams in the next 2 weeks one of them on monday and i havent studied for any of them and i feel overwhelmed from all of this and now i cant sit down and study for the exams a...`

