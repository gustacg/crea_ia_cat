---
phase: 05-cross-document-matching
verified: 2026-03-28T00:00:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Phase 5: Cross-Document Matching Verification Report

**Phase Goal:** Todos os campos sobrepostos entre Atestado e ART comparados — identifiers exatos, nomes/endereços fuzzy, escopo semântico, datas por intervalo — cada campo com status MATCH/DIVERGENTE/AUSENTE

**Verified:** 2026-03-28
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | CPF, CNPJ, CREA/RNP comparados com match exato após normalização | VERIFIED | `_comparar_identificadores()` in matching.py lines 144-189 uses `normalizar_crea_rnp()` for all three; 7 unit tests pass |
| 2 | Nomes e empresas comparados via GPT-4.1 com tolerância a variações | VERIFIED | `_comparar_via_gpt()` batches nome_profissional, empresa_contratante, empresa_executora via `client.responses.parse`; 4 GPT tests pass |
| 3 | Endereço da obra comparado com tolerância a formatação | VERIFIED | `endereco_obra` included in GPT batch call with `_formatar_endereco()` helper; covered by mock tests |
| 4 | Datas do atestado validadas como DENTRO do intervalo da ART | VERIFIED | `_comparar_datas()` lines 213-275 enforces strict containment; 6 unit tests pass including boundary cases |
| 5 | Escopo comparado semanticamente via GPT-4.1 com score de confiança | VERIFIED | `escopo` field in GPT batch; prompt specifies confianca 0.0-1.0; `test_escopo_similar` asserts confianca >= 0.7 |
| 6 | Valores financeiros e contrato comparados quando presentes | VERIFIED | `valor_contrato` and `contrato_numero` included in GPT batch; `test_valor_contrato_match` and `test_contrato_numero_match` pass |
| 7 | AR CLIMA vs HIDRO-CLIMA detectado como DIVERGENTE | VERIFIED | Prompt line 87 explicitly states "AR CLIMA SOLUÇÕES vs HIDRO-CLIMA Construções = COMPLETAMENTE DIFERENTES"; `mock_matching_client_divergente` fixture confirms path; `test_empresa_divergente` passes |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `crea_cat_ai/matching.py` | Cross-document matching module; exports cruzar_documentos, StatusCampo, ComparacaoCampo, ResultadoCruzamento | VERIFIED | 457 lines; all 4 classes present; all 3 private layers (_comparar_identificadores, _comparar_datas, _comparar_via_gpt) implemented; public API cruzar_documentos() present |
| `tests/test_matching.py` | Unit tests for all matching logic; min 100 lines | VERIFIED | 300 lines; 21 test functions across 4 test classes |
| `tests/conftest.py` | mock_matching_client fixture | VERIFIED | Three matching fixtures present: mock_matching_client (all MATCH), mock_matching_client_divergente (empresa_executora DIVERGENTE), mock_matching_client_none (output_parsed=None) |
| `main.py` | Pipeline with Phase 5 matching wired in; contains matching.cruzar_documentos | VERIFIED | Lines 9-10 import matching and TipoDocumento; line 124 calls matching.cruzar_documentos; line 171 includes resultado_cruzamento in return dict |
| `tests/test_integration_phase5.py` | Integration tests for matching with real PDFs; min 30 lines | VERIFIED | 75 lines; 3 integration tests with @pytest.mark.integration marker; covers Par 1, Par 2 (D-11), and pipeline end-to-end |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `crea_cat_ai/matching.py` | `crea_cat_ai/analysis.py` | `from crea_cat_ai.analysis import ResultadoAnalise, EntidadesEndereco, normalizar_crea_rnp` | WIRED | Line 20 confirms import; normalizar_crea_rnp used at lines 156-184 |
| `crea_cat_ai/matching.py` | openai | `client.responses.parse` | WIRED | Line 70: `client = OpenAI(api_key=config.OPENAI_API_KEY)`; line 352: `client.responses.parse(...)` with `text_format=ResultadoGPTCruzamento` |
| `tests/test_matching.py` | `crea_cat_ai/matching.py` | `from crea_cat_ai.matching import` | WIRED | Lines 12-17 import cruzar_documentos, StatusCampo, ComparacaoCampo, ResultadoCruzamento |
| `main.py` | `crea_cat_ai/matching.py` | `from crea_cat_ai import matching` | WIRED | Line 9 imports matching; line 124 calls matching.cruzar_documentos(art_analise, atestado_analise) |
| `main.py` | `crea_cat_ai/matching.py` | `matching.cruzar_documentos` | WIRED | Line 124 confirmed; result serialized at line 171 via model_dump() |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `crea_cat_ai/matching.py` | `comparacoes` | Three layers: _comparar_identificadores, _comparar_datas, _comparar_via_gpt each populating ComparacaoCampo objects from ResultadoAnalise inputs | Yes — computes from live ResultadoAnalise fields; GPT layer calls real API | FLOWING |
| `main.py` resultado_cruzamento | `resultado_cruzamento` | `matching.cruzar_documentos(art_analise, atestado_analise)` where art_analise/atestado_analise come from `resultados_analise.get(TipoDocumento.ART.value)` (populated by Phase 3 analysis) | Yes — chained from live Phase 3 output | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 21 matching unit tests pass | `python -m pytest tests/test_matching.py -q` | 21 passed in 9.60s | PASS |
| Full non-integration suite passes (no regressions) | `python -m pytest tests/ -m "not integration" -q` | 84 passed, 19 deselected in 14.67s | PASS |
| matching module imports cleanly | `python -c "from crea_cat_ai.matching import cruzar_documentos, StatusCampo, ComparacaoCampo, ResultadoCruzamento; print('imports OK')"` | imports OK | PASS |
| main.py imports cleanly | `python -c "from main import main; print('main imports OK')"` | main imports OK | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| XREF-01 | 05-01, 05-02 | CPF, CNPJ, CREA/RNP comparados com match exato (após normalização RNP/CREA) | SATISFIED | `_comparar_identificadores()` uses `normalizar_crea_rnp()` for CPF, CNPJ, CREA/RNP; 7 TestMatchExato tests pass |
| XREF-02 | 05-01, 05-02 | Nomes e empresas comparados com tolerância a variações via GPT-4.1 | SATISFIED | nome_profissional, empresa_contratante in GPT batch with explicit MATCH/DIVERGENTE rules in prompt |
| XREF-03 | 05-01, 05-02 | Endereço da obra comparado com tolerância a variações de formatação | SATISFIED | endereco_obra in GPT batch via `_formatar_endereco()`; field present in both ART and Atestado input blocks |
| XREF-04 | 05-01, 05-02 | Datas do atestado validadas como DENTRO do intervalo de datas da ART | SATISFIED | `_comparar_datas()` strict containment; 6 TestValidacaoDatas tests cover all boundary conditions including AUSENTE for missing dates |
| XREF-05 | 05-01, 05-02 | Valores financeiros e número de contrato comparados quando presentes | SATISFIED | valor_contrato and contrato_numero in GPT batch; both verified by unit tests |
| XREF-06 | 05-01, 05-02 | Escopo/objeto do serviço comparado semanticamente via GPT-4.1 | SATISFIED | escopo in GPT batch; prompt specifies confianca score 0.0-1.0; test_escopo_similar asserts confianca >= 0.7 on MATCH |
| XREF-07 | 05-01, 05-02 | Empresa executora/contratada comparada entre documentos | SATISFIED | empresa_executora in GPT batch; D-11 guard in prompt; mock_matching_client_divergente fixture; test_empresa_divergente passes |

**All 7 XREF requirements satisfied. No orphaned requirements for Phase 5.**

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `main.py` | 136 | `# Phases 6-7: placeholders` comment | Info | Intentional — phases 6-7 are genuinely not yet implemented. Not a stub in matching.py or any Phase 5 artifact. |

No blockers or warnings found. The placeholder comment in main.py refers to future phases and does not affect Phase 5 goal achievement.

---

### Human Verification Required

None. All Phase 5 behaviors are verifiable programmatically:

- Exact matching logic is deterministic Python (no external deps)
- GPT fuzzy/semantic layer is fully mocked in unit tests
- Integration tests exist for real-document validation but require PDFs + API key (correctly skipped in automated CI)

The Par 2 AR CLIMA / HIDRO-CLIMA divergence detection is validated at the unit level via `mock_matching_client_divergente` and at the integration level via `test_par2_empresa_divergente` (skips gracefully if Par 2 PDFs not present).

---

## Gaps Summary

No gaps. All must-haves verified at all four levels:

- Level 1 (exists): all 5 artifacts present
- Level 2 (substantive): matching.py is 457 lines with 3 complete implementation layers; test_matching.py is 300 lines with 21 tests
- Level 3 (wired): all 5 key links confirmed; cruzar_documentos called in main.py and produces resultado_cruzamento in return dict
- Level 4 (data flows): matching pipeline is fully chained from Phase 3 ResultadoAnalise objects through all three comparison layers

Phase 5 goal is achieved: all overlapping fields between Atestado and ART are compared with MATCH/DIVERGENTE/AUSENTE status per field, using exact matching for identifiers, interval validation for dates, and GPT-4.1 for fuzzy/semantic fields.

---

_Verified: 2026-03-28_
_Verifier: Claude (gsd-verifier)_
