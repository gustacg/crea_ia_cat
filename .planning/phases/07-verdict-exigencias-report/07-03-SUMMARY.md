---
phase: 07-verdict-exigencias-report
plan: "03"
subsystem: integration
tags: [main, pipeline, integration-tests, verdict, report]
dependency_graph:
  requires: [07-01, 07-02]
  provides: [complete-pipeline, end-to-end-integration]
  affects: [main.py]
tech_stack:
  added: []
  patterns: [multi-par-processing, early-return-guard]
key_files:
  created:
    - tests/test_integration_phase7.py
  modified:
    - main.py
decisions:
  - "D-20 guard in main.py: early return when ART or Atestado absent prevents verdict generation on incomplete pars"
  - "Multi-par __main__ block iterates INPUT_DIR subdirectories automatically (D-19)"
  - "Return dict simplified to veredito/score/exigencias/relatorio_paths — removed redundant intermediate data"
metrics:
  duration: "15 minutes"
  completed_date: "2026-03-29"
  tasks_completed: 1
  files_modified: 2
---

# Phase 7 Plan 03: Integration — Wire Verdict + Report into main.py Summary

**One-liner:** Complete pipeline integration wiring verdict.calcular_veredito() and report.gerar_relatorios() into main.py, replacing Phase 7 placeholder, with 4 cross-module integration tests validating knock-out rules.

## What Was Built

**main.py** updated to complete the end-to-end CREA CAT AI pipeline:

- Added `from crea_cat_ai import verdict` and `from crea_cat_ai import report` imports
- Replaced Phase 7 placeholder (lines 158-161) with full veredito + relatorio block
- Added D-20 guard: early return with error status when ART or Atestado absent
- Calls `verdict.calcular_veredito()` with all 4 sources (cruzamento, compliance, metadata, assinatura)
- Extracts profissional/contratante names from ART analysis for report header
- Calls `report.gerar_relatorios()` to produce JSON + Markdown output files
- Simplified return dict: `{status, veredito, score, exigencias, relatorio_json, relatorio_md, par_name}`
- Updated `__main__` block: iterates all par subdirectories in INPUT_DIR, falls back to flat structure

**tests/test_integration_phase7.py** — 4 integration tests validating cross-module wiring:

1. `test_empresa_divergente_not_aderente` — Par 2 smoke test: empresa divergente (AR CLIMA vs HIDRO-CLIMA) must not produce ADERENTE (D-04)
2. `test_all_match_aderente` — All 6 fields matching produces ADERENTE
3. `test_cpf_divergente_suspeito` — CPF divergente activates D-02 knock-out, forces SUSPEITO
4. `test_exigencias_generated_for_divergence` — Divergent empresa_executora generates UPPERCASE exigencias; compliance exigencias passed through

All 4 tests pass without real PDFs or GPT API calls.

## Task Execution

| Task | Name | Status | Commit |
|------|------|--------|--------|
| 1 | Wire verdict + report into main.py and create integration tests | Complete | d354d8c |
| 2 | Verify end-to-end pipeline on real test pairs | Checkpoint (awaiting human) | — |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None — main.py is fully wired. The output/ directory will be populated when `python main.py` is run with real test documents and a valid OPENAI_API_KEY.

## Checkpoint Status

Task 2 is a `checkpoint:human-verify` gate requiring the user to:
1. Run `python main.py` with OPENAI_API_KEY set
2. Verify output/ contains relatorio.json + relatorio.md for each par
3. Confirm Par 2 (AR CLIMA vs HIDRO-CLIMA) is PENDENTE or SUSPEITO (never ADERENTE)
4. Confirm exigencias are in UPPERCASE CREA format

## Self-Check: PASSED

- main.py: FOUND and verified with grep
- tests/test_integration_phase7.py: FOUND and all 4 tests PASS
- Commit d354d8c: FOUND in git log
- All acceptance criteria verified via Python script
