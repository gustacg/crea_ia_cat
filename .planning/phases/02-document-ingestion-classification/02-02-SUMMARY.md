---
phase: 02-document-ingestion-classification
plan: 02
subsystem: ingestion
tags: [openai, gpt-4.1, pymupdf, pipeline, integration-test]

# Dependency graph
requires:
  - phase: 02-01
    provides: carregar_pacote() and full ingestion module with TipoDocumento, PacoteDocumentos, DocumentoCarregado
provides:
  - main.py wired to ingestion module — runs full classification pipeline end-to-end
  - Integration test test_classificacao_docs_reais for real GPT-4.1 API validation
  - pytest.ini with integration marker for selective test execution
affects: [03-entity-extraction, 04-metadata-signature, 05-matching]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Integration tests marked with @pytest.mark.integration — skipped by default, run with -m integration"
    - "main.py imports only crea_cat_ai.ingestion — other modules wired in future phases"

key-files:
  created:
    - pytest.ini
  modified:
    - main.py
    - tests/test_ingestion.py

key-decisions:
  - "main.py imports only ingestion module — avoids breaking future phases by not importing stubs"
  - "Integration test skips gracefully when OPENAI_API_KEY absent — safe for CI"

patterns-established:
  - "Checkpoint:human-verify after each GPT-facing feature — ensures real API behavior validated by human"

requirements-completed: [INGS-01, INGS-02, INGS-03, INGS-04]

# Metrics
duration: 15min
completed: 2026-03-28
---

# Phase 02 Plan 02: Wire main.py + Integration Test Summary

**main.py wired to call ingestion.carregar_pacote() with structured output, integration test added for GPT-4.1 real-API validation of all 5 CREA test documents**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-28T00:00:00Z
- **Completed:** 2026-03-28 (partial — awaiting human verification at Task 2)
- **Tasks:** 1 of 2 complete (Task 2 is checkpoint:human-verify)
- **Files modified:** 3

## Accomplishments
- main.py now calls `ingestion.carregar_pacote(input_dir)` and prints structured classification results
- Returns `{"status": "ingestion_complete", "art": ..., "atestado": ..., "complementares": [...], "nao_classificados": [...]}`
- Integration test `test_classificacao_docs_reais` added — validates real GPT-4.1 classifies all 5 documents correctly
- `pytest.ini` created with `integration` marker so unit tests run by default without API calls
- All 7 existing unit tests still pass (1 integration test correctly excluded)

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire main.py to call ingestion and add integration test** - `0e4e69c` (feat)

**Plan metadata:** pending (after Task 2 human verification)

## Files Created/Modified
- `main.py` - Replaced placeholder with full ingestion pipeline call, structured dict return
- `tests/test_ingestion.py` - Appended integration test `test_classificacao_docs_reais` with `@pytest.mark.integration`
- `pytest.ini` - Created with `integration` marker definition

## Decisions Made
- Imported only `crea_cat_ai.ingestion` in main.py (not all 8 modules as the original placeholder did) — avoids import errors from stub modules in future phases
- Integration test skips gracefully with `pytest.skip` when `OPENAI_API_KEY` is absent — CI-safe

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

To run the integration test or `python main.py`:
```
set OPENAI_API_KEY=sk-your-key-here
python main.py
```

Or for the integration test:
```
set OPENAI_API_KEY=sk-your-key-here
python -m pytest tests/test_ingestion.py -m integration -v
```

## Checkpoint Status

**Task 2 is pending human verification.**

The user must run `python main.py` with `OPENAI_API_KEY` set and confirm all 5 test documents are classified correctly:
- MA20250929762.aZzbC (1).pdf → ART
- MA20250957723.ac6Y3.pdf → ART
- 944678...ACT_Alexandre...pdf → Atestado
- saude indigena.pdf → Atestado
- 944678...DECLARACAO...pdf → Declaracao

## Next Phase Readiness
- Ingestion module fully implemented and wired into main.py
- Pending: human verification that GPT-4.1 correctly classifies all 5 real CREA documents
- Once verified: Phase 03 (entity extraction) can proceed with confidence that the document loading pipeline is correct

## Self-Check: PASSED

All files verified present. Commit 0e4e69c confirmed in git log.

## Known Stubs
None — main.py correctly calls real ingestion module. Phases 3-7 stubs are documented as "not implemented" in output text, not silent empty values.

---
*Phase: 02-document-ingestion-classification*
*Completed: 2026-03-28 (partial — awaiting Task 2 checkpoint)*
