---
phase: 3
slug: document-analysis-entity-extraction
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/conftest.py (exists from Phase 2) |
| **Quick run command** | `python -m pytest tests/test_analysis.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_analysis.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | ANAL-01 | unit | `python -m pytest tests/test_analysis.py::test_entity_extraction -q` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | ANAL-02 | unit | `python -m pytest tests/test_analysis.py::test_crea_rnp_normalization -q` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | ANAL-03 | unit | `python -m pytest tests/test_analysis.py::test_spell_check -q` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | ANAL-04 | unit | `python -m pytest tests/test_analysis.py::test_visual_detection -q` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 1 | ANAL-05 | unit | `python -m pytest tests/test_analysis.py::test_signer_classification -q` | ❌ W0 | ⬜ pending |
| 03-01-06 | 01 | 1 | ANAL-06 | integration | `python -m pytest tests/test_analysis.py::test_full_analysis_pipeline -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_analysis.py` — stubs for ANAL-01 through ANAL-06
- [ ] Test fixtures with mock GPT responses for entity extraction
- [ ] Test fixtures with real document page images (base64) for visual tests

*Existing pytest infrastructure from Phase 2 covers framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GPT Vision accuracy on real scanned docs | ANAL-04, ANAL-05 | Depends on GPT model behavior | Run integration test with real API key, inspect JSON output for timbre/assinatura fields |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
