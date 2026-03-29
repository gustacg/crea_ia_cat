---
phase: 2
slug: document-ingestion-classification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | INGS-01 | unit | `python -m pytest tests/test_ingestion.py -k load` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | INGS-02 | unit | `python -m pytest tests/test_ingestion.py -k convert` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | INGS-03 | unit | `python -m pytest tests/test_analysis.py -k classify` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | INGS-04 | integration | `python -m pytest tests/test_analysis.py -k test_pairs` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ingestion.py` — stubs for INGS-01, INGS-02
- [ ] `tests/test_analysis.py` — stubs for INGS-03, INGS-04
- [ ] `tests/conftest.py` — shared fixtures (test PDF paths, mock OpenAI client)
- [ ] `pip install pytest` — if not already installed

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GPT-4.1 classification accuracy on real docs | INGS-04 | Requires live API call with real PDFs | Run `python main.py` on test pairs, verify classification output matches ground truth |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
