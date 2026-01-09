# AGENT_PROTOCOL – Hard Operating Rules

> **No exceptions.** These rules govern all agent actions in this repository.

---

## Core Operating Rules

### 1. Read Repo First
Before any action, read and understand the relevant parts of the repository.

### 2. Propose a Concrete Plan
Before making edits, propose a specific, actionable plan.

### 3. Append Plan to RUNLOG.md Before Edits
**Before** executing any changes, append the plan to `RUNLOG.md`.

### 4. Execute in Small, Atomic Chunks
Break work into small, independently verifiable pieces.

### 5. Commit After Each Chunk
After each atomic chunk, commit with the message format:
```
Plan Step X: <short description>
```

### 6. Update RUNLOG.md Immediately After Each Chunk
Append to `RUNLOG.md`:
- Files changed
- Tight diff summary (what changed and why)
- Commands run
- Test/metric outputs

### 7. No Silent Changes, No Squashing
- Every change must be logged
- `RUNLOG.md` is **append-only** – never delete or modify existing entries
- Do not squash commits

---

## Additional Governance Rules

### 8. DECISIONS.md Requirement
No changes to anything unless you also update `DECISIONS.md` with:
- **What** changed
- **Why** it changed
- **Expected metric impact**

### 9. Acceptance Tests Requirement
After any change, **rerun Acceptance Tests** as defined in `ACCEPTANCE_TESTS.md`.

---

## Summary Checklist

Before making any change, confirm:
- [ ] Read relevant repo sections
- [ ] Plan documented in RUNLOG.md
- [ ] Change is atomic
- [ ] Commit message follows format
- [ ] RUNLOG.md updated with diff/tests
- [ ] DECISIONS.md updated (if applicable)
- [ ] Acceptance Tests pass
