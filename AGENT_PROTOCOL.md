# AGENT_PROTOCOL – Hard Operating Rules

> **No exceptions.** These rules govern all agent actions in this repository.

---

## Execution Paths

### FAST PATH (Default During Active Development)

Use FAST PATH for iterative development within a plan step:

1. **Relevant Scope Only**: Read only files being touched + governance files + directly referenced specs. **Do NOT re-read the entire repo each time.**
2. **Atomic Steps**: Small, independently verifiable changes.
3. **Smoke Tests Only**: Run Tier A (smoke) tests from `ACCEPTANCE_TESTS.md`.
4. **Short RUNLOG Entries**: 3-line summary + commit SHA + smoke pass/fail. Defer verbose logs to `results/runlogs/<date>/<sha>.txt` with pointer.

**Relevant Scope Definition**:
- Files being modified in this step
- `AGENT_PROTOCOL.md`, `RUNLOG.md`, `ACCEPTANCE_TESTS.md`, `DECISIONS.md`
- Any spec file explicitly referenced in the current plan
- Parent directories for context (but not full recursive reads)

### SAFE PATH (Required for Merge/Push/Milestone)

Use SAFE PATH when:
- Pushing to `main` branch
- Completing a plan (all steps done)
- Before any tagged milestone or release

Requirements:
1. **Full Acceptance Tests**: Run all Tier A + Tier B tests.
2. **Full Evidence**: Paste complete test outputs or link to artifact file.
3. **Expanded RUNLOG Entry**: Full diff table, all commands, all outputs.
4. **DECISIONS.md Update**: Required for any non-trivial change.

---

## Core Operating Rules

### 1. Read Relevant Scope
Read files as defined by FAST/SAFE PATH above. Never read entire repo unnecessarily.

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

### 6. Update RUNLOG.md After Each Chunk
- **FAST PATH**: Short entry (3 lines max) + commit SHA + smoke results
- **SAFE PATH**: Full entry with diff table, commands, outputs

### 7. No Silent Changes, No Squashing
- Every change must be logged
- `RUNLOG.md` is **append-only** – never delete or modify existing entries
- Do not squash commits

---

## Additional Governance Rules

### 8. DECISIONS.md Requirement
Update `DECISIONS.md` for any non-trivial change with:
- **What** changed
- **Why** it changed
- **Expected metric impact**

### 9. Acceptance Tests Requirement
- **FAST PATH**: Run Tier A (smoke) tests after each atomic step
- **SAFE PATH**: Run Tier A + Tier B (full) tests before push/merge

---

## Summary Checklist

**FAST PATH** (each atomic step):
- [ ] Read relevant scope only
- [ ] Change is atomic
- [ ] Commit with "Plan Step X" message
- [ ] Run smoke tests (Tier A)
- [ ] Short RUNLOG entry appended

**SAFE PATH** (before push/milestone):
- [ ] All FAST PATH items complete
- [ ] Run full tests (Tier A + B)
- [ ] Expanded RUNLOG entry with evidence
- [ ] DECISIONS.md updated if applicable
- [ ] Push to main
