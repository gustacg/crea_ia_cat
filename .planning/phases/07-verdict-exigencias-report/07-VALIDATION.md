---
phase: 7
slug: verdict-exigencias-report
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already configured) |
| **Config file** | `pytest.ini` (project root) |
| **Quick run command** | `python -m pytest tests/test_verdict.py tests/test_report.py -x` |
| **Full suite command** | `python -m pytest tests/ -m "not integration"` |
| **Estimated runtime** | ~5 seconds (unit), ~60 seconds (integration with GPT) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_verdict.py tests/test_report.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -m "not integration"`
- **Before `/gsd:verify-work`:** Full suite must be green (including integration)
- **Max feedback latency:** 10 seconds (unit tests)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | VERD-01 | unit | `pytest tests/test_verdict.py::TestScoring -x` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | VERD-01 | unit | `pytest tests/test_verdict.py::TestKnockouts -x` | ❌ W0 | ⬜ pending |
| 07-01-03 | 01 | 1 | VERD-02 | unit | `pytest tests/test_verdict.py::TestConsolidarItens -x` | ❌ W0 | ⬜ pending |
| 07-01-04 | 01 | 1 | VERD-03 | unit | `pytest tests/test_verdict.py::TestExigencias -x` | ❌ W0 | ⬜ pending |
| 07-01-05 | 01 | 1 | VERD-04 | unit | `pytest tests/test_report.py::TestRelatorioJSON -x` | ❌ W0 | ⬜ pending |
| 07-01-06 | 01 | 1 | VERD-05 | unit | `pytest tests/test_report.py::TestRelatorioMarkdown -x` | ❌ W0 | ⬜ pending |
| 07-02-01 | 02 | 2 | VERD-06 | integration | `pytest tests/test_integration_phase7.py -m integration` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_verdict.py` — stubs for VERD-01, VERD-02, VERD-03 (unit, pure functions)
- [ ] `tests/test_report.py` — stubs for VERD-04, VERD-05 (unit, uses tmp_path fixture)
- [ ] `tests/test_integration_phase7.py` — stubs for VERD-06 (integration, requires real PDFs + API key)

*Existing infrastructure covers framework needs (pytest.ini, conftest.py already present).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Markdown report readability | VERD-05 | Visual formatting quality | Open output/*.md in a Markdown viewer, confirm sections render correctly |
| Par 2 PENDENTE/SUSPEITO result | VERD-06 | Requires human review of verdict reasoning | Run pipeline on Par 2, verify veredito is not ADERENTE |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
