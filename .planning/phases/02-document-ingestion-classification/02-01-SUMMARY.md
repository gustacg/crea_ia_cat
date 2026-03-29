---
phase: 02-document-ingestion-classification
plan: 01
subsystem: ingestion
tags: [pymupdf, openai, pydantic, structured-output, responses-api, vision, pdf, classification]

# Dependency graph
requires:
  - phase: 01-environment-setup
    provides: Python 3.13 environment with openai, pymupdf, pikepdf, pyHanko, Pillow installed; config.py with OPENAI_MODEL, IMAGE_DPI, MAX_PAGES_PER_PDF

provides:
  - TipoDocumento enum (8 types: ART, Atestado, Declaracao, Anuencia, NF, Contrato, RelatorioFotografico, Desconhecido)
  - PaginaDocumento dataclass (numero, texto_nativo, imagem_b64)
  - DocumentoCarregado dataclass (caminho, tipo, paginas, tem_texto_nativo)
  - PacoteDocumentos dataclass (art, atestado, complementares, nao_classificados)
  - ResultadoClassificacao Pydantic model for GPT structured output
  - carregar_pdf(Path) -> list[PaginaDocumento] — PyMuPDF page-to-image with text extraction
  - classificar_documento(DocumentoCarregado) -> ResultadoClassificacao — GPT-4.1 Responses API
  - _agrupar_documentos(list[DocumentoCarregado]) -> PacoteDocumentos — document grouping
  - carregar_pacote(Path) -> PacoteDocumentos — full pipeline entry point

affects:
  - 02-02 (main.py wiring uses carregar_pacote as pipeline entry point)
  - 03-entity-extraction (consumes DocumentoCarregado.paginas)
  - 05-matching (consumes PacoteDocumentos.art and .atestado)
  - all-subsequent-phases (all phases consume types from ingestion.py)

# Tech tracking
tech-stack:
  added: []  # All dependencies already installed in Phase 1
  patterns:
    - "Responses API with text_format=PydanticModel for structured GPT output (not chat.completions)"
    - "import pymupdf (never import fitz) — CLAUDE.md hard rule"
    - "pymupdf.open(str(caminho)) — must convert Path to str for C extension"
    - "with pymupdf.open(...) as doc — context manager prevents file handle leaks"
    - "config.IMAGE_DPI / 72 as Matrix scale for 200-DPI PNG renders"
    - "output_parsed=None safety check for GPT refusal handling"
    - "TDD flow: RED (collection fails) -> GREEN (7 tests pass)"

key-files:
  created:
    - crea_cat_ai/ingestion.py
    - tests/conftest.py
    - tests/test_ingestion.py
  modified: []

key-decisions:
  - "Responses API used instead of chat.completions — per CLAUDE.md convention; simpler structured output with text_format= parameter"
  - "First page only for classification — sufficient for all 5 test docs, avoids memory spike on 32-page Atestado"
  - "Module-level OpenAI client — monkeypatched in tests via conftest.py mock_openai_client fixture"
  - "TipoDocumento as str Enum — allows direct comparison with GPT response string values"

patterns-established:
  - "Pattern: Always use import pymupdf (not fitz) — all future modules follow this"
  - "Pattern: All print/log messages in pt-BR — established for entire pipeline"
  - "Pattern: config.OPENAI_MODEL (not hardcoded 'gpt-4.1') — config-driven model selection"
  - "Pattern: pytest monkeypatch for OpenAI client mocking — reused in future test phases"

requirements-completed: [INGS-01, INGS-02, INGS-03, INGS-04]

# Metrics
duration: 12min
completed: 2026-03-28
---

# Phase 2 Plan 01: Document Ingestion & Classification Summary

**PyMuPDF PDF loading with 200-DPI PNG conversion and GPT-4.1 Responses API classification producing typed PacoteDocumentos grouping from raw PDF directory**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-28T23:24:18Z
- **Completed:** 2026-03-28T23:36:00Z
- **Tasks:** 2 (TDD: RED then GREEN)
- **Files modified:** 3

## Accomplishments

- Full `crea_cat_ai/ingestion.py` implementation: 8-type enum, 4 dataclasses, Pydantic schema, 4 functions (273 lines)
- All 7 unit tests pass with mocked OpenAI client — no API key required for test suite
- Real PDF validation confirmed: 1-page ART loads as 2688-char text + 504,660-char base64 PNG at 200 DPI

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test infrastructure and unit tests** - `0ab88d3` (test)
2. **Task 2: Implement ingestion.py** - `449d93f` (feat)

**Plan metadata:** (docs commit — see below)

_Note: Task 1 = TDD RED phase (collection fails, no implementation). Task 2 = TDD GREEN phase (all 7 tests pass)._

## Files Created/Modified

- `crea_cat_ai/ingestion.py` — Full implementation: TipoDocumento enum, PaginaDocumento/DocumentoCarregado/PacoteDocumentos dataclasses, ResultadoClassificacao Pydantic model, carregar_pdf/classificar_documento/_agrupar_documentos/carregar_pacote functions
- `tests/conftest.py` — Fixtures: pdf_dir, pdf_art_path, pdf_atestado_path, mock_openai_client (monkeypatches client), all_test_pdfs
- `tests/test_ingestion.py` — 7 unit tests: enum validation, PDF loading, text extraction, PNG header check, mocked classification, document grouping, empty directory error

## Decisions Made

- Responses API (`client.responses.parse`) over chat.completions — per CLAUDE.md convention; `text_format=ResultadoClassificacao` gives typed Pydantic instance directly without manual JSON parsing
- First page only for classification — page 0 is sufficient for all 5 test documents; avoids loading 32 images for `saude indigena.pdf` into memory
- Module-level `client = OpenAI(...)` — enables monkeypatching in tests without refactoring; production use reads from `config.OPENAI_API_KEY`
- `TipoDocumento(resultado.tipo)` with `except ValueError` fallback — gracefully handles edge case where GPT returns unmapped string

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required beyond `OPENAI_API_KEY` already documented in Phase 1.

## Known Stubs

None — no stubs, placeholders, or hardcoded empty values. All functions are fully implemented and tested.

## Next Phase Readiness

- `carregar_pacote(Path) -> PacoteDocumentos` is ready as the pipeline entry point for Plan 02 (main.py wiring)
- `DocumentoCarregado` with `paginas: list[PaginaDocumento]` ready for Phase 3 entity extraction
- `PacoteDocumentos.art` and `.atestado` ready for Phase 5 field matching
- Integration test (real GPT-4.1 API call against 5 test PDFs) deferred to Plan 02 or Phase 3 — requires `OPENAI_API_KEY` in environment

---
*Phase: 02-document-ingestion-classification*
*Completed: 2026-03-28*
