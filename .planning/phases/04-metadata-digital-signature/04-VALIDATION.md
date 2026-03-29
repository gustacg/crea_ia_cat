---
phase: 4
slug: metadata-digital-signature
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pytest.ini (exists — addopts = -m 'not integration') |
| **Quick run command** | `python -m pytest tests/ -m "not integration" -x -q` |
| **Full suite command** | `python -m pytest tests/ -m "not integration" -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -m "not integration" -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -m "not integration" -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | META-01 | unit | `pytest tests/test_metadata.py -k "test_extract"` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | META-02 | unit | `pytest tests/test_metadata.py -k "test_anomalia"` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 1 | SIGN-01 | unit | `pytest tests/test_signature.py -k "test_detecta"` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | SIGN-02 | unit | `pytest tests/test_signature.py -k "test_valida"` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 1 | SIGN-03 | unit | `pytest tests/test_signature.py -k "test_ausencia"` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 2 | META-01,SIGN-01 | integration | `pytest tests/test_integration_phase4.py -m integration` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_metadata.py` — stubs for META-01, META-02
- [ ] `tests/test_signature.py` — stubs for SIGN-01, SIGN-02, SIGN-03
- [ ] `tests/test_integration_phase4.py` — integration test stubs

*Existing pytest infrastructure from Phase 3 covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Gov-Br chain download | SIGN-02 | Requires internet access to repo.iti.br | Run `python -c "from crea_cat_ai.signature import ..."; verify certs/ dir created` |
| ICP-Brasil trust store | SIGN-02 | Requires CA bundle from acraiz.icpbrasil.gov.br | Verify certs/ contains both govbr and icp-brasil chains |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
