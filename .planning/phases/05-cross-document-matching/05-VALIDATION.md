---
phase: 5
slug: cross-document-matching
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pytest.ini (exists — addopts = -m 'not integration') |
| **Quick run command** | `python -m pytest tests/ -m "not integration" -x -q` |
| **Full suite command** | `python -m pytest tests/ -m "not integration" -v` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -m "not integration" -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -m "not integration" -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 8 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | XREF-01 | unit | `pytest tests/test_matching.py -k "test_exact"` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | XREF-04 | unit | `pytest tests/test_matching.py -k "test_data"` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | XREF-02,XREF-03,XREF-06,XREF-07 | unit | `pytest tests/test_matching.py -k "test_fuzzy or test_semantic"` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 1 | XREF-05 | unit | `pytest tests/test_matching.py -k "test_valor"` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | XREF-01..07 | integration | `pytest tests/test_integration_phase5.py -m integration` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_matching.py` — stubs for XREF-01 through XREF-07
- [ ] `tests/test_integration_phase5.py` — integration test stubs

*Existing pytest infrastructure from Phase 3 covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GPT fuzzy/semantic accuracy | XREF-02,XREF-06 | Requires live GPT API call | Run `python main.py` with real PDFs, check matching output |
| Par 2 divergence detection | XREF-07 | Requires real document pair | Verify "AR CLIMA" vs "HIDRO-CLIMA" flagged as DIVERGENTE |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 8s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
