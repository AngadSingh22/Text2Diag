# ACCEPTANCE_TESTS – Definition of Done

> **Purpose**: Define exact commands to verify the codebase is in a working state.
> Run these after every change.

---

## Quick Smoke Tests (Fast, Local)

### 1. Python Syntax Check
Verify all Python files have valid syntax.

```bash
python -m py_compile scripts/*.py
python -m py_compile src/text2diag/**/*.py
```

**Expected**: Exit code 0, no output.

---

### 2. Import Check
Verify the main package imports without errors.

```bash
python -c "import sys; sys.path.insert(0, 'src'); import text2diag; print('OK')"
```

**Expected**: Prints `OK`, exit code 0.

---

### 3. Script Help Check
Verify each script responds to `--help` without crashing.

```bash
python scripts/prepare_data.py --help
python scripts/train.py --help
python scripts/eval.py --help
python scripts/calibrate.py --help
python scripts/infer_json.py --help
python scripts/run_all.py --help
```

**Expected**: Each prints usage info, exit code 0.

---

## Unit Tests

### 4. Pytest Suite
Run all unit tests in the `tests/` directory.

```bash
pytest tests/ -v
```

**Expected**: All tests pass (or skip if not yet implemented).

**Existing test files**:
- `tests/test_contract_validator.py`
- `tests/test_evidence_span_validity.py`
- `tests/test_repair_rules.py`
- `tests/test_splits_deterministic.py`

---

## Governance File Checks

### 5. Governance Files Exist
Verify all governance files are present.

```bash
ls AGENT_PROTOCOL.md RUNLOG.md ACCEPTANCE_TESTS.md DECISIONS.md 2>nul || dir AGENT_PROTOCOL.md RUNLOG.md ACCEPTANCE_TESTS.md DECISIONS.md
```

**Expected**: All files listed (DECISIONS.md created when first decision is logged).

---

## Artifacts

After a successful run, these should exist:
- `RUNLOG.md` with latest entry
- All scripts executable without syntax errors
- `src/text2diag/` importable

---

## Run All Acceptance Tests (One Command)

```bash
# Windows PowerShell
python -m py_compile scripts/prepare_data.py scripts/train.py scripts/eval.py scripts/calibrate.py scripts/infer_json.py scripts/run_all.py; `
python -c "import sys; sys.path.insert(0, 'src'); import text2diag; print('Import OK')"; `
pytest tests/ -v --tb=short
```

**Expected**: All commands succeed with exit code 0.
