---
phase: 04-metadata-digital-signature
plan: 03
subsystem: pipeline-integration
tags: [integration, metadata, signature, main, tests]
dependency_graph:
  requires: [04-01, 04-02]
  provides: [phase4-pipeline-complete]
  affects: [main.py, pipeline-flow]
tech_stack:
  added: []
  patterns: [phase-integration, integration-tests, real-pdf-validation]
key_files:
  created:
    - tests/test_integration_phase4.py
  modified:
    - main.py
    - crea_cat_ai/signature.py
decisions:
  - Keep PDF file open during entire validate_pdf_signature() call — pyHanko reads file lazily
key_decisions:
  - validate_pdf_signature requires file handle open: moved entire sig loop inside with-block
metrics:
  duration: 15m
  completed: 2026-03-29
  tasks_completed: 2
  files_changed: 3
---

# Phase 4 Plan 3: Wire Analysis and Integration Tests Summary

Phase 4 Plan 3 wires metadata.py and signature.py into main.py pipeline and validates correct results on all 5 real test PDFs via integration tests — including DECLARACAO valid trusted signature, ACT/ART no sigs, and saude indigena 2 sigs.

## What Was Built

### Task 1: Wire metadata and signature into main.py pipeline (commit c4ca904)

Updated `main.py` to add Phase 4 processing after the Phase 3 analysis block:

- Added `from crea_cat_ai import metadata, signature` import
- Added Phase 4 block that iterates all docs (art + atestado + complementares), calls `metadata.processar_documento()` and `signature.validar_assinaturas()` for each
- Added summary printout showing creator, producer, anomalias, and signature status per document
- Added `resultados_metadata` and `resultados_assinatura` dicts to the return value
- Removed "Fase 3: Metadados e Assinatura Digital" from the placeholder section, renumbered remaining phases 4-6

### Task 2: Integration tests for metadata and signature on real PDFs (commit 6331448)

Created `tests/test_integration_phase4.py` with 8 `@pytest.mark.integration` tests:

**Metadata tests:**
- `test_meta_art_par1`: ART Par 1 has docinfo (creator/producer not None)
- `test_meta_todos_docs`: all 5 PDFs process via processar_documento() without exception
- `test_meta_sem_software_suspeito`: none of the 5 test PDFs flag SOFTWARE_SUSPEITO

**Signature tests:**
- `test_sig_declaracao_assinada`: DECLARACAO has 1 sig, valido=True, confiavel=True
- `test_sig_act_alexandre_sem_assinatura`: ACT_Alexandre returns presente=False, quantidade=0
- `test_sig_art_sem_assinatura`: MA20250929762 returns presente=False
- `test_sig_saude_indigena_duas_assinaturas`: saude indigena has presente=True, quantidade=2
- `test_sig_ausencia_e_estado_valido`: all non-signed PDFs have no anomalias field (SIGN-03)

## Results

- Unit tests: 63 passed (0 failed)
- Integration tests: 8 passed (0 failed, 0 skipped)
- Full pipeline runs without exceptions

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed "seek of closed file" in signature.py**
- **Found during:** Task 2 (integration test test_sig_declaracao_assinada failed)
- **Issue:** `validar_assinaturas()` opened the PDF with a `with` block that closed the file after getting `sigs`. Then `validation.validate_pdf_signature(sig, ...)` tried to seek the file handle during validation — but the file was already closed. Error: `ValueError: seek of closed file`
- **Fix:** Moved the signature validation loop inside the `with open(...)` block so the file handle remains open throughout `validate_pdf_signature()`. pyHanko reads signature bytes lazily from the file handle, so it must stay open.
- **Files modified:** `crea_cat_ai/signature.py`
- **Commit:** 6331448

## Known Stubs

None — all metadata and signature processing is fully wired to real data from pikepdf and pyHanko.

## Self-Check: PASSED

- FOUND: main.py
- FOUND: tests/test_integration_phase4.py
- FOUND: crea_cat_ai/signature.py
- FOUND: 04-03-SUMMARY.md
- FOUND: commit c4ca904
- FOUND: commit 6331448
