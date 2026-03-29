---
phase: 03-document-analysis-entity-extraction
plan: 01
subsystem: analysis
tags: [openai, pydantic, gpt-4.1-vision, entity-extraction, ocr, spell-check, crea, rnp]

# Dependency graph
requires:
  - phase: 02-document-ingestion-classification
    provides: DocumentoCarregado, PaginaDocumento, TipoDocumento, PacoteDocumentos

provides:
  - ResultadoAnalise Pydantic model with all entity fields
  - analisar_documento() — single GPT call per document for entities + visual + spell-check
  - analisar_pacote() — iterates ART + Atestado + complementares
  - normalizar_crea_rnp() — strips non-digits for CREA/RNP equivalence
  - _selecionar_paginas_analise() — page selection strategy (first+last for >3 pages)

affects:
  - 05-matching (consumes ResultadoAnalise for field-by-field comparison)
  - 06-compliance (consumes engenheiro_habilitado, erros_ortograficos, visual fields)
  - 07-verdict (consumes full ResultadoAnalise for scoring)

# Tech tracking
tech-stack:
  added: []  # No new deps — pydantic already installed as transitive dep of openai
  patterns:
    - "GPT-4.1 Vision with detail:high for visual analysis (timbre, signature)"
    - "Single GPT call per document covers ANAL-01 through ANAL-06"
    - "Page selection: all pages if <=3, else first+last (avoids 32-page token spike)"
    - "normalizar_crea_rnp strips all non-digits for CREA/RNP comparison"
    - "module-level client = OpenAI() reused across calls"

key-files:
  created:
    - crea_cat_ai/analysis.py
    - tests/test_analysis.py
  modified:
    - tests/conftest.py

key-decisions:
  - "Single GPT call per document handles entities + visual + spell-check — reduces cost and maintains context coherence"
  - "normalizar_crea_rnp strips all non-numeric chars so 1120893194MA == 1120893194 == CREA MA 1120893194"
  - "detail:high for all analysis images — detail:low misses signature text and timbre detail"
  - "Page selection: <=3 pages send all, >3 pages send first+last — handles 32-page saude indigena.pdf efficiently"
  - "integration test marked with @pytest.mark.integration — excluded from unit test run (requires real API key)"

patterns-established:
  - "Pattern: responses.parse(text_format=ResultadoAnalise) — same pattern as Phase 2 classification"
  - "Pattern: mock_analysis_client fixture in conftest.py patches crea_cat_ai.analysis.client"
  - "Pattern: _make_doc() helper creates fake DocumentoCarregado for unit tests"

requirements-completed: [ANAL-01, ANAL-02, ANAL-03, ANAL-04, ANAL-05, ANAL-06]

# Metrics
duration: 3min
completed: 2026-03-28
---

# Phase 3 Plan 01: Document Analysis & Entity Extraction Summary

**GPT-4.1 Vision entity extraction via Responses API with Pydantic structured output — normalizes CREA/RNP to single field, detects timbre+signature with detail:high, spell-checks only Atestados, and classifies engineer qualification from signer cargo**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-28T23:54:19Z
- **Completed:** 2026-03-28T23:57:34Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments

- Implemented `crea_cat_ai/analysis.py` with all 8 Pydantic models and 5 public/private functions covering ANAL-01 through ANAL-06
- `normalizar_crea_rnp()` handles all 5 normalization test cases: digits-only, UF suffix, CREA MA prefix, D/GO format, None
- Page selection sends only page 1 + last for documents > 3 pages — prevents 32-page token spike on saude indigena.pdf
- 24 unit tests passing with mocked GPT client; 31 total (full suite including Phase 2) all green

## Task Commits

1. **Task 1: Tests + Pydantic models + analysis.py implementation** - `07f0958` (feat)

**Plan metadata:** (see final docs commit)

## Files Created/Modified

- `crea_cat_ai/analysis.py` — Full implementation: 8 Pydantic models, normalizar_crea_rnp, _selecionar_paginas_analise, _construir_input_analise, analisar_documento, analisar_pacote
- `tests/test_analysis.py` — 24 unit tests covering all 6 ANAL requirements with mocked GPT
- `tests/conftest.py` — Added mock_analysis_client fixture with complete ResultadoAnalise mock

## Decisions Made

- Single GPT call per document handles entities + visual analysis + spell-check together. Separate calls per task would cost more and lose context coherence between entity and visual findings.
- `normalizar_crea_rnp` strips all non-digit characters. This handles every known CREA/RNP format variation: "1120893194", "1120893194MA", "CREA MA 1015902979", "4388D/GO", "147573MA".
- `detail: "high"` used for all analysis images (vs `detail: "low"` in Phase 2 classification). Low detail compresses images and misses signature text and timbre details required by ANAL-04/05.
- Integration test (`test_analisar_documento_integracao`) marked `@pytest.mark.integration` and excluded from unit run. Requires real OPENAI_API_KEY.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Integration test fails as expected when OPENAI_API_KEY is not set (auth gate). This is correct behavior — the test is `@pytest.mark.integration` and is excluded from the unit test suite via `-m "not integration"`.

## Known Stubs

None — all public functions are fully implemented. No hardcoded empty values flowing to consumers.

## Next Phase Readiness

- `ResultadoAnalise` with all fields is ready for Phase 4 (metadata + signature) and Phase 5 (matching)
- `normalizar_crea_rnp` exported and ready for Phase 5 CREA/RNP comparison
- `analisar_pacote` is the entry point that main.py will call after `carregar_pacote`
- Concern: Phase 4 (pyHanko ICP-Brasil) still needs root CA bundle setup

---
*Phase: 03-document-analysis-entity-extraction*
*Completed: 2026-03-28*
