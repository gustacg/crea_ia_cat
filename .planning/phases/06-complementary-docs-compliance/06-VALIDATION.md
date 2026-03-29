---
phase: 6
slug: complementary-docs-compliance
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (pytest.ini present) |
| **Config file** | `pytest.ini` — `addopts = -m "not integration"` |
| **Quick run command** | `pytest tests/test_compliance.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~5 seconds (unit), ~30 seconds (integration with API) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_compliance.py -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | CDOC-01 | unit | `pytest tests/test_compliance.py::TestDeclaracaoTrigger::test_assinante_nao_engenheiro_requer_declaracao -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | CDOC-01 | unit | `pytest tests/test_compliance.py::TestDeclaracaoTrigger::test_assinante_engenheiro_nao_requer_declaracao -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | CDOC-02 | unit | `pytest tests/test_compliance.py::TestDeclaracaoVerificacao::test_declaracao_encontrada_engenheiro_area_correta -x` | ❌ W0 | ⬜ pending |
| 06-01-04 | 01 | 1 | CDOC-02 | unit | `pytest tests/test_compliance.py::TestDeclaracaoVerificacao::test_declaracao_ausente_gera_exigencia -x` | ❌ W0 | ⬜ pending |
| 06-01-05 | 01 | 1 | CDOC-03 | unit | `pytest tests/test_compliance.py::TestAnuencia::test_sem_subcontratacao_nao_aplicavel -x` | ❌ W0 | ⬜ pending |
| 06-01-06 | 01 | 1 | CDOC-04 | unit | `pytest tests/test_compliance.py::TestCrossReference::test_crea_declarante_matches_profissional -x` | ❌ W0 | ⬜ pending |
| 06-01-07 | 01 | 1 | COMP-01 | unit | `pytest tests/test_compliance.py::TestAnexoIV::test_atestado_completo_todas_categorias_conforme -x` | ❌ W0 | ⬜ pending |
| 06-01-08 | 01 | 1 | COMP-01 | unit | `pytest tests/test_compliance.py::TestAnexoIV::test_atestado_sem_escopo_gera_exigencia -x` | ❌ W0 | ⬜ pending |
| 06-01-09 | 01 | 1 | COMP-01 | unit | `pytest tests/test_compliance.py::TestAnexoIV::test_atestado_sem_assinatura_gera_exigencia -x` | ❌ W0 | ⬜ pending |
| 06-01-10 | 01 | 1 | COMP-02 | unit | `pytest tests/test_compliance.py::TestRes1160::test_verificacoes_1137_aplicadas -x` | ❌ W0 | ⬜ pending |
| 06-01-11 | 01 | 1 | COMP-03 | unit | `pytest tests/test_compliance.py::TestDeclaracaoVerificacao::test_exigencia_formato_crea_correto -x` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | CDOC-01+02 | integration | `pytest tests/test_integration_phase6.py -m integration -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_compliance.py` — unit test stubs for CDOC-01 to CDOC-04, COMP-01 to COMP-03
- [ ] `tests/test_integration_phase6.py` — integration test stub for Par 1 (Ruan/Alexandre Declaracao flow)

*Existing `tests/conftest.py` fixtures and `test_matching.py` helper `_make_resultado` should be reused/shared.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Res. 1.160/2025 override rules | COMP-02 | Text not available in provided PDF — structural hook only | Verify hook exists, apply rules when text provided |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
