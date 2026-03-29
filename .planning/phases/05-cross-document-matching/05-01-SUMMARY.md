---
phase: 05-cross-document-matching
plan: 01
subsystem: matching
tags: [matching, cross-document, gpt-4.1, pydantic, tdd]
dependency_graph:
  requires: [03-01, 03-02]
  provides: [cruzar_documentos, StatusCampo, ComparacaoCampo, ResultadoCruzamento]
  affects: [06-compliance, 07-verdict]
tech_stack:
  added: []
  patterns: [responses-api-structured-output, tdd-red-green, three-layer-matching]
key_files:
  created:
    - crea_cat_ai/matching.py
    - tests/test_matching.py
  modified:
    - tests/conftest.py
decisions:
  - Three-layer matching architecture: exact local (identifiers) + local (dates) + single GPT batch (fuzzy/semantic)
  - StatusCampo as str Enum — allows direct JSON serialization and comparison
  - normalizar_crea_rnp reused from analysis.py — handles all known CREA/RNP format variants
  - GPT prompt explicitly guards D-11: AR CLIMA vs HIDRO-CLIMA must be DIVERGENTE
  - Missing/malformed dates → AUSENTE not DIVERGENTE (absence is not fraud)
metrics:
  duration_seconds: 236
  completed_date: "2026-03-29"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
---

# Phase 5 Plan 1: Cross-Document Matching Summary

**One-liner:** Three-layer matching engine (exact identifiers + date intervals + single GPT-4.1 batch) producing per-field MATCH/DIVERGENTE/AUSENTE ResultadoCruzamento from two ResultadoAnalise objects.

## What Was Built

`crea_cat_ai/matching.py` — the cross-document field comparison module that consumes an ART `ResultadoAnalise` and an Atestado `ResultadoAnalise` and produces a `ResultadoCruzamento` with per-field comparison statuses.

### Three-Layer Architecture

**Layer 1 — Exact identifiers (local Python):**
- CREA/RNP comparison using `normalizar_crea_rnp()` from `analysis.py` (strips all non-digits)
- CPF profissional, CNPJ contratante
- ART referenciada (atestado.art_referenciada vs art.numero_documento)
- Both absent → AUSENTE; one absent → AUSENTE; equal → MATCH; different → DIVERGENTE

**Layer 2 — Date interval validation (local Python):**
- Parses DD/MM/YYYY, YYYY-MM-DD, DD/MM/YY formats
- Strict containment: atestado dates must be WITHIN ART date range
- Missing/malformed dates → AUSENTE (not DIVERGENTE — absence is not fraud per D-08)
- Violations include specific details (which bound was exceeded)

**Layer 3 — Fuzzy/semantic via GPT-4.1 (single batched Responses API call):**
- Compares: nome_profissional, empresa_contratante, empresa_executora, endereco_obra, escopo, valor_contrato, contrato_numero
- Prompt explicitly guards D-11: "AR CLIMA SOLUÇÕES" vs "HIDRO-CLIMA Construções" = DIVERGENTE
- Fallback when output_parsed=None: all 7 fields return AUSENTE
- Returns ComparacaoCampo with valor_art, valor_atestado, confianca, detalhes populated

### Public API

```python
def cruzar_documentos(art: ResultadoAnalise, atestado: ResultadoAnalise) -> ResultadoCruzamento
```

### Models Exported

- `StatusCampo` — str enum: MATCH, DIVERGENTE, AUSENTE
- `ComparacaoCampo` — per-field result with status, valores, confianca, detalhes
- `ResultadoCruzamento` — aggregate with comparacoes list + total_match/total_divergente/total_ausente
- `ComparacaoGPT` — GPT output schema (used in conftest mocks)
- `ResultadoGPTCruzamento` — GPT batch output container

## Test Coverage

**21 unit tests in `tests/test_matching.py`:**
- `TestMatchExato` (7 tests): CREA/RNP match after normalization, CPF match, CNPJ match, both absent, one absent, ART referenciada
- `TestValidacaoDatas` (6 tests): within interval, start before ART, end after ART, no atestado dates, no ART dates, ISO format
- `TestGPTCruzamento` (4 tests): nome match, empresa divergente (D-11), escopo similar, GPT fallback
- `TestCruzarDocumentos` (4 tests): complete result, mandatory fields, valor contrato, contrato numero

**3 conftest fixtures added:**
- `mock_matching_client` — all 7 GPT fields as MATCH
- `mock_matching_client_divergente` — empresa_executora as DIVERGENTE (D-11 test)
- `mock_matching_client_none` — output_parsed=None (fallback test)

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 (TDD RED) | d1a35cf | test(05-01): add failing tests for matching module |
| Task 2 (TDD GREEN) | 147ff7f | feat(05-01): implement matching.py with 3-layer matching |

## Requirements Covered

| Requirement | Status |
|-------------|--------|
| XREF-01: CPF/CNPJ/CREA/RNP exact match after normalization | Done |
| XREF-02: Names/companies compared with tolerance via GPT-4.1 | Done |
| XREF-03: Address compared with format tolerance | Done |
| XREF-04: Atestado dates validated within ART interval | Done |
| XREF-05: Financial values and contract number compared | Done |
| XREF-06: Scope compared semantically with confidence score | Done |
| XREF-07: Empresa executora compared (AR CLIMA vs HIDRO-CLIMA detectable) | Done |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — matching.py is fully implemented with all three layers wired.

## Self-Check: PASSED

- `crea_cat_ai/matching.py` exists with 449 lines
- `tests/test_matching.py` exists with 21 test functions
- `tests/conftest.py` updated with 3 mock fixtures
- Commit d1a35cf exists (TDD RED)
- Commit 147ff7f exists (TDD GREEN)
- 21/21 matching tests pass
- 84/84 non-integration tests pass (no regressions)
