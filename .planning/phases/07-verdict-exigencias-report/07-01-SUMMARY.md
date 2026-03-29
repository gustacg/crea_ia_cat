---
phase: 07-verdict-exigencias-report
plan: "01"
subsystem: verdict
tags: [scoring, knock-outs, veredito, exigencias, tdd, pure-computation]
dependency_graph:
  requires:
    - crea_cat_ai/matching.py (StatusCampo, ComparacaoCampo, ResultadoCruzamento)
    - crea_cat_ai/compliance.py (StatusCompliance, VerificacaoItem, ResultadoCompliance)
    - crea_cat_ai/metadata.py (MetadadosPDF)
    - crea_cat_ai/signature.py (ResultadoAssinatura)
    - config.py (PESO_*, SCORE_ADERENTE, SCORE_PENDENTE)
  provides:
    - calcular_veredito() public API
    - StatusItem, TipoVeredito, ItemVerificado, Veredito models
  affects:
    - main.py (Phase 7 Plan 3 wiring)
    - crea_cat_ai/report.py (Phase 7 Plan 2 consumes Veredito)
tech_stack:
  added: []
  patterns:
    - str Enum pattern (consistent with TipoDocumento, StatusCampo)
    - Pydantic BaseModel for output types
    - Pure computation — zero GPT calls, zero I/O
    - Weighted average scoring with knock-out overrides
key_files:
  created:
    - crea_cat_ai/verdict.py
    - tests/test_verdict.py
  modified: []
decisions:
  - Compliance items use peso=0.0 — they generate their own exigencias already; adding them to the weighted average would double-penalize
  - Single penalidade per metadata analysis (break after first anomalous doc) — avoids stack overflow on edge cases with many documents
  - CAMPO_PESOS includes empresa_contratante mapped to PESO_NOME as a proxy — not a core identifier but meaningful
  - art_referenciada mapped to PESO_CONTRATO — similar specificity level to contract numbers
metrics:
  duration: "~15 minutes"
  completed_date: "2026-03-29"
  tasks_completed: 1
  files_created: 2
  files_modified: 0
---

# Phase 07 Plan 01: Verdict Scoring, Knock-outs & Exigencias Summary

Weighted average scoring engine with knock-out cap rules (CPF/CNPJ/CREA at 0.49, empresa at 0.79) and CREA-format exigencias generation from 4 upstream sources.

## What Was Built

`crea_cat_ai/verdict.py` — pure-computation decision engine that produces ADERENTE/PENDENTE/SUSPEITO verdicts from all upstream analysis results. No GPT calls, no I/O.

### Public API

```python
def calcular_veredito(
    resultado_cruzamento: ResultadoCruzamento | None,
    resultado_compliance: ResultadoCompliance,
    resultados_metadata: dict[str, MetadadosPDF],
    resultados_assinatura: dict[str, ResultadoAssinatura],
) -> Veredito:
```

Returns `Veredito(tipo, score, itens_verificados, exigencias)`.

### Scoring Algorithm (D-01 to D-04)

1. Consolidate items from 4 sources into unified `ItemVerificado` list
2. Weighted average: `score = sum(STATUS_SCORE[status] * peso) / sum(peso)` for items with peso > 0
3. Knock-out rules: CPF/CNPJ/CREA divergente caps at 0.49; empresa divergente caps at 0.79
4. Penalties: metadata suspeito -0.15; declaracao ausente -0.20
5. Threshold classification: >= 0.80 ADERENTE, >= 0.50 PENDENTE, < 0.50 SUSPEITO

### Exigencias Format

All exigencias are in UPPERCASE declarative CREA format (D-08):
- Compliance exigencias reused directly from Phase 6 (no reformatting needed)
- New cruzamento exigencias generated per-campo (CPF, CNPJ, CREA, empresa, escopo, datas)
- Combined without duplication

## TDD Execution

**RED phase:** 35 failing tests written first (ImportError from stub verdict.py).
**GREEN phase:** Full implementation. All 35 tests pass.
**REFACTOR phase:** Not needed — code was clean from initial implementation.

## Tests

`tests/test_verdict.py` — 35 unit tests, 0 integration:
- `TestEnums` (4): StatusItem and TipoVeredito str enum values
- `TestModels` (3): ItemVerificado and Veredito Pydantic models
- `TestCalcularScore` (3): weighted average math
- `TestKnockouts` (6): cap and penalty rules
- `TestVereditoTipo` (3): threshold classification
- `TestConsolidarItens` (5): item consolidation from all 4 sources
- `TestExigencias` (6): CREA format exigencias generation
- `TestCalcularVeredito` (5): public API end-to-end

## Commits

| Hash | Type | Description |
|------|------|-------------|
| f6808eb | test | RED phase — 35 failing tests for verdict.py |
| f25b634 | feat | GREEN phase — full verdict.py implementation, all 35 tests pass |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — `verdict.py` is a complete, fully wired implementation. No placeholders, no hardcoded empty values. The `calcular_veredito()` function processes all inputs and returns a meaningful `Veredito`. This plan's goal is fully achieved.

## Self-Check: PASSED

- `crea_cat_ai/verdict.py`: FOUND (506 lines, min_lines=150)
- `tests/test_verdict.py`: FOUND (736 lines, min_lines=100, 35 test functions)
- Commit f6808eb: FOUND
- Commit f25b634: FOUND
- All 35 tests pass: VERIFIED (`python -m pytest tests/test_verdict.py` — 35 passed)
- Imports verified: `from crea_cat_ai.verdict import calcular_veredito, StatusItem, TipoVeredito, ItemVerificado, Veredito` — OK
