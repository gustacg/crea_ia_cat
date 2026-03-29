---
phase: 06-complementary-docs-compliance
plan: 01
subsystem: compliance
tags: [compliance, declaracao, anuencia, anexo-iv, res-1137, tdd]
dependency_graph:
  requires:
    - "05-02: matching.py (ResultadoCruzamento)"
    - "03-xx: analysis.py (ResultadoAnalise, AssinanteInfo, normalizar_crea_rnp)"
    - "02-xx: ingestion.py (TipoDocumento, PacoteDocumentos)"
  provides:
    - "compliance.py: verificar_compliance(), ResultadoCompliance"
    - "StatusCompliance enum (CONFORME/NAO_CONFORME/NAO_APLICAVEL)"
    - "VerificacaoItem, ResultadoEspecialidadeGPT models"
  affects:
    - "07-xx: verdict.py (consumes ResultadoCompliance for scoring)"
tech_stack:
  added: []
  patterns:
    - "Responses API with text_format=ResultadoEspecialidadeGPT for specialty matching (same as matching.py)"
    - "Python-pure deterministic checks for Anexo IV (no GPT)"
    - "normalizar_crea_rnp reused from analysis.py for CREA cross-reference"
    - "TDD: RED commit (stubs + 22 tests) then GREEN commit (full implementation)"
key_files:
  created:
    - crea_cat_ai/compliance.py
    - tests/test_compliance.py
  modified: []
decisions:
  - "Exigência texto: 'PAR. 1' (uppercase) em vez de 'par. 1' para manter formato CREA maiúsculo"
  - "_verificacoes_1160_overrides retorna lista vazia — texto articulado Res. 1.160/2025 não disponível no PDF fornecido (Anexos_Resolucao 1160-2025.pdf contém formulários da 1.137/2023)"
  - "Verificação CDOC-02 (especialidade GPT) só é acionada quando Declaração presente e ART tem escopo — evita chamada GPT desnecessária"
metrics:
  duration: "6 minutes"
  completed: "2026-03-29"
  tasks: 2
  files: 2
---

# Phase 06 Plan 01: Compliance Module Summary

**One-liner:** Compliance verification with Art.59 §1º Declaração trigger, Anuência subcontracting detection, Anexo IV 6-category checklist, and Res.1.160/2025 structural hook — all wired through verificar_compliance() orchestrator.

## What Was Built

`crea_cat_ai/compliance.py` (622 lines) implementing the full regulatory verification layer:

- **verificar_compliance()** — public API orchestrating all 3 checks, returns `ResultadoCompliance`
- **verificar_declaracao()** — Art. 59 §1º enforcement: checks `engenheiro_habilitado` flag, searches complementares for Declaração, generates CREA-format exigência when absent, cross-references CREA and ART number (CDOC-04), calls GPT for specialty matching (CDOC-02)
- **verificar_anuencia()** — Subcontracting detection: compares `empresa_executora` between ART and Atestado (strip+upper), generates exigência when needed, accepts Anuência when found (CDOC-03)
- **verificar_anexo_iv()** — Deterministic Python-pure checklist: 6 CATEGORIAS_ANEXO_IV lambda checks against ResultadoAnalise fields (COMP-01)
- **_verificacoes_1160_overrides()** — Structural hook returning empty list pending Res. 1.160/2025 text (COMP-02)
- **_verificar_especialidade_gpt()** — Single Responses API call for semantic specialty-to-scope matching

`tests/test_compliance.py` (22 test functions across 7 test classes) covering all 7 requirements (CDOC-01 through CDOC-04, COMP-01 through COMP-03).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Exigência texto uppercase normalization**
- **Found during:** Task 2 (TDD GREEN — test_exigencia_formato_crea_correto failed)
- **Issue:** Plan specified `"par. 1"` in lowercase in the D-05 exigência text. Test correctly asserted `exigencia == exigencia.upper()` (CREA format is all-uppercase).
- **Fix:** Changed `"par. 1"` to `"PAR. 1"` in the exigência string so it matches CREA's standard all-uppercase declarative format.
- **Files modified:** `crea_cat_ai/compliance.py`
- **Commit:** d1c7bd9

## Test Results

```
22 passed in test_compliance.py
106 passed total (no regressions)
```

## Known Stubs

- `_verificacoes_1160_overrides()` returns `[]` — intentional placeholder. The PDF `Anexos_Resolucao 1160-2025.pdf` contains Anexos I-VI of Res. 1.137/2023 (ART/CAT form templates), not the text of Res. 1.160/2025. Will be completed when the regulation text is provided. Documented in RESEARCH.md.

## Self-Check: PASSED
