---
phase: 04-metadata-digital-signature
plan: 01
subsystem: metadata
tags: [pikepdf, pdf-metadata, fraud-detection, anomaly-detection]

# Dependency graph
requires:
  - phase: 01-environment-setup
    provides: pikepdf 10.5.1 installed, config.py with SOFTWARE_SUSPEITO list
  - phase: 03-document-analysis-entity-extraction
    provides: test patterns (unittest.mock, conftest fixtures, pytest markers)
provides:
  - MetadadosPDF dataclass with creator/producer/author/creation_date/mod_date/anomalias
  - extrair_metadados() reads pikepdf docinfo, parses PDF date format
  - detectar_anomalias() checks SOFTWARE_SUSPEITO list and date consistency
  - processar_documento() public API combining extract + detect
  - Unit tests for META-01 and META-02 (21 tests, 100% passing)
affects: [05-matching, 07-verdict, main.py integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pikepdf.open() as context manager with str() wrapping of docinfo values"
    - "_parse_pdf_date() with regex normalization of timezone quotes before strptime"
    - "TDD RED/GREEN: test file committed before implementation"

key-files:
  created:
    - crea_cat_ai/metadata.py
    - tests/test_metadata.py
  modified: []

key-decisions:
  - "_parse_pdf_date uses full string strptime (not slice to N chars) because timezone offset adds chars"
  - "detectar_anomalias loops SOFTWARE_SUSPEITO against both creator and producer fields with break to avoid duplicates"
  - "processar_documento() is the public API entry point — main.py calls this not extrair/detectar separately"

patterns-established:
  - "Pattern: pikepdf docinfo values always wrapped with str() before use (pikepdf.String objects)"
  - "Pattern: _parse_pdf_date regex normalizes -03'00' to -0300 and Z to +0000 before strptime"

requirements-completed: [META-01, META-02]

# Metrics
duration: 2min
completed: 2026-03-29
---

# Phase 4 Plan 1: Metadata Extraction Summary

**pikepdf-based MetadadosPDF extraction with SOFTWARE_SUSPEITO anomaly detection and date consistency checking**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-29T00:35:22Z
- **Completed:** 2026-03-29T00:38:13Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- MetadadosPDF dataclass with 6 fields (creator, producer, author, creation_date, mod_date, anomalias) extracted from PDF docinfo via pikepdf
- extrair_metadados() reads pikepdf docinfo with str() wrapping, _parse_pdf_date() handles all PDF date variants including timezone with apostrophes
- detectar_anomalias() flags SOFTWARE_SUSPEITO (Photoshop, GIMP, Paint.NET, Inkscape) in creator/producer and mod_date < creation_date anomalies
- 21 unit tests all passing, covering META-01 and META-02 requirements with mock pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: Create unit tests (RED)** - `e6152b7` (test)
2. **Task 2: Implement metadata.py (GREEN)** - `f1e5523` (feat)

_Note: TDD tasks have two commits (test RED → feat GREEN)_

## Files Created/Modified

- `crea_cat_ai/metadata.py` — Full implementation: MetadadosPDF dataclass, _parse_pdf_date(), extrair_metadados(), detectar_anomalias(), processar_documento()
- `tests/test_metadata.py` — 21 unit tests (6 parse-date, 3 extrair, 9 detectar, 3 processar) + 2 integration tests

## Decisions Made

- `_parse_pdf_date` uses full-string strptime (not sliced) — the PDF timezone format `D:20250115143000-03'00'` after normalization becomes 19 chars, not 18; slicing cuts the tz offset and parsing fails
- `detectar_anomalias` uses `break` inner loop to avoid duplicate anomalias when same software matches both creator and producer
- `processar_documento` is the canonical public API for main.py — wraps both operations and sets `m.anomalias` in place before returning

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed _parse_pdf_date slice length**
- **Found during:** Task 2 (implement metadata.py, GREEN phase)
- **Issue:** Research.md code used `s[:18]` to slice before strptime with `%z`, but the normalized timezone string `20250115143000-0300` is 19 chars — slice cut `0` from `-0300` producing `ValueError`
- **Fix:** Removed the `:18` slice, used full string `s` in strptime with `%z`
- **Files modified:** `crea_cat_ai/metadata.py`
- **Verification:** `test_parse_pdf_date_standard` passed after fix
- **Committed in:** f1e5523 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix was essential — without it the standard PDF date format with timezone would always fall through to the naive parser, losing timezone info.

## Issues Encountered

- Pre-existing failure in `tests/test_signature.py::TestParametrosCriticosValidacao::test_moment_self_reported` — unrelated to this plan, caused by `signature.py` still being a stub (that's plan 04-02). Logged as out-of-scope, not fixed.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `metadata.py` ready for integration into `main.py` (Phase 4 Plan 3 wires all Phase 4 modules)
- `processar_documento()` is the entry point — consistent with integration pattern in RESEARCH.md Pattern 5
- No blockers for Phase 5 (matching)

---
*Phase: 04-metadata-digital-signature*
*Completed: 2026-03-29*
