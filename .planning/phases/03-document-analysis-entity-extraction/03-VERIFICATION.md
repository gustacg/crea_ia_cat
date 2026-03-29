---
phase: 03-document-analysis-entity-extraction
verified: 2026-03-28T00:00:00Z
status: human_needed
score: 6/6 unit-verifiable must-haves verified
gaps: []
human_verification:
  - test: "Run `python main.py` with real PDF documents in INPUT_DIR and inspect the 'Fase 2: Analise e Extracao de Entidades' output block"
    expected: "ART document shows profissional.nome containing 'ALEXANDRE' or 'NIZO', crea_rnp extracted, contratante.cnpj present. Atestado Par 1 shows assinante 'RUAN FERNANDES' with cargo 'ADMINISTRADOR' and Engenheiro: NAO. Atestado Par 2 (32 pages) completes without timeout."
    why_human: "Entity extraction accuracy against real documents requires GPT-4.1 Vision API call and visual inspection of output — cannot be verified by static code analysis or unit tests alone."
  - test: "Run `python -m pytest tests/test_analysis.py -m integration -x -q` with OPENAI_API_KEY set and the 5 test PDFs present"
    expected: "test_analise_art_real, test_assinante_ruan_real, and test_analisar_documento_integracao all pass — GPT correctly extracts entities and classifies Ruan as non-engineer"
    why_human: "Integration tests require real OpenAI API key and real PDF files — cannot run in automated verification"
---

# Phase 3: Document Analysis & Entity Extraction — Verification Report

**Phase Goal:** Cada documento tem um set completo de entidades extraídas (CPF, CNPJ, CREA/RNP tratados como equivalentes, nomes, organizações, datas, endereços, escopo do serviço) + verificação ortográfica + detecção visual de timbre e assinatura

**Verified:** 2026-03-28
**Status:** human_needed — all automated checks pass; live GPT accuracy needs human confirmation
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `analisar_documento()` returns a `ResultadoAnalise` with entity fields populated from GPT structured output | VERIFIED | `client.responses.parse(text_format=ResultadoAnalise)` in `analysis.py:290-295`; `test_extrai_entidades_art` and `test_analisar_documento_retorna_resultado_analise` pass |
| 2 | RNP and CREA identifiers normalize to the same numeric string via `normalizar_crea_rnp()` | VERIFIED | All 5 canonical cases pass in behavioral spot-check: plain digits, UF suffix, CREA MA prefix, D/GO format, None |
| 3 | Spell-check errors are only collected for Atestado documents, not ARTs | VERIFIED | `PROMPT_ANALISE_BASE` line 161 explicitly instructs GPT "VERIFICAÇÃO ORTOGRÁFICA (apenas para Atestados)"; `test_ortografia_art_vazia` verifies mock returns `erros_ortograficos=[]` for ART type |
| 4 | Visual analysis detects timbre and signature presence with signer details | VERIFIED | `"detail": "high"` in `_construir_input_analise`; `AnaliseVisual` model with `tem_timbre`, `tem_assinatura_visual`, `assinantes` list; `test_visual_timbre` and `test_visual_assinatura` pass |
| 5 | Signer with cargo ADMINISTRADOR is classified as `engenheiro_habilitado=false` | VERIFIED | `AssinanteInfo.engenheiro_habilitado: bool` field; behavioral spot-check confirms `AssinanteInfo(cargo="ADMINISTRADOR", engenheiro_habilitado=False)` works; mock fixture uses this exact case |
| 6 | Signer with cargo containing Engenheiro is classified as `engenheiro_habilitado=true` | VERIFIED | `test_engenheiro_habilitado` instantiates `AssinanteInfo(cargo="Engenheiro Civil de Saude Indigena", engenheiro_habilitado=True)` and asserts correctly |

**Score:** 6/6 truths verified (unit-testable portion)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `crea_cat_ai/analysis.py` | Entity extraction, visual analysis, spell check, CREA/RNP normalization | VERIFIED | 340 lines; all 8 Pydantic models, 5 public/private functions, module-level client, full prompt |
| `tests/test_analysis.py` | Unit tests for ANAL-01 through ANAL-06 with mocked GPT | VERIFIED | 356 lines (exceeds 80-line minimum); 24 unit tests + 3 integration tests; covers all 6 ANAL requirements |
| `tests/conftest.py` | `mock_analysis_client` fixture added (not deleted) | VERIFIED | Fixture present at line 81; patches `crea_cat_ai.analysis.client` with complete `ResultadoAnalise` mock |
| `main.py` | Pipeline with Phase 2 ingestion + Phase 3 analysis wired | VERIFIED | Lines 7-8 import both `ingestion` and `analysis`; lines 51-74 call `analysis.analisar_pacote(pacote)` and print entity summary |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `crea_cat_ai/analysis.py` | OpenAI Responses API | `client.responses.parse(text_format=ResultadoAnalise)` | VERIFIED | Found at `analysis.py:290`; pattern `responses.parse` confirmed |
| `crea_cat_ai/analysis.py` | `crea_cat_ai/ingestion.py` | `from crea_cat_ai.ingestion import DocumentoCarregado, PaginaDocumento, TipoDocumento, PacoteDocumentos` | VERIFIED | Found at `analysis.py:18-23` |
| `tests/test_analysis.py` | `crea_cat_ai/analysis.py` | `from crea_cat_ai.analysis import ...` | VERIFIED | All public symbols imported at `test_analysis.py:16-28` |
| `main.py` | `crea_cat_ai/analysis.py` | `analysis.analisar_pacote(pacote)` | VERIFIED | `from crea_cat_ai import analysis` at `main.py:7`; `analysis.analisar_pacote(pacote)` at `main.py:53` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `main.py` (entity summary print block) | `resultados_analise` | `analysis.analisar_pacote(pacote)` → `analisar_documento()` → `client.responses.parse()` → `response.output_parsed` | Yes — GPT structured output via Responses API; fallback to `ResultadoAnalise(confianca=0.0)` only on model refusal | FLOWING |
| `crea_cat_ai/analysis.py` `analisar_documento()` return | `response.output_parsed` | `client.responses.parse(model=..., instructions=..., input=..., text_format=ResultadoAnalise)` | Real GPT API call with document images and text; not hardcoded | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Module imports cleanly | `python -c "from crea_cat_ai.analysis import ResultadoAnalise, analisar_documento, analisar_pacote, normalizar_crea_rnp; print('imports OK')"` | `imports OK` | PASS |
| `normalizar_crea_rnp` — all 5 canonical cases | Inline Python assertions for digits-only, UF suffix, CREA MA prefix, D/GO format, None | All 5 assertions pass | PASS |
| `_selecionar_paginas_analise` — 1, 3, 32-page docs | Inline Python assertions | 1-page → 1, 3-page → 3, 32-page → [1, 32] | PASS |
| `AssinanteInfo.engenheiro_habilitado` boolean | Inline instantiation and assertion | ADMINISTRADOR → False, Engenheiro Civil → True | PASS |
| Unit test suite | `python -m pytest tests/test_analysis.py -x -q` | `24 passed, 3 deselected in 4.69s` | PASS |
| Full test suite (Phase 2 + Phase 3) | `python -m pytest tests/ -x -q` | `31 passed, 4 deselected in 4.90s` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ANAL-01 | 03-01-PLAN.md, 03-02-PLAN.md | GPT-4.1 Vision extrai entidades estruturadas: CPF, CNPJ, CREA, RNP, nomes, organizações, datas, endereços, escopo | SATISFIED | `ResultadoAnalise` has all required fields; `analisar_documento()` calls GPT with `text_format=ResultadoAnalise`; `test_extrai_entidades_art` verifies nome, crea_rnp, cnpj extraction |
| ANAL-02 | 03-01-PLAN.md | Pipeline trata RNP e CREA como identificadores equivalentes na comparação | SATISFIED | `normalizar_crea_rnp()` strips all non-digits; PROMPT says "RNP e CREA são EQUIVALENTES"; 5 canonical normalization tests pass |
| ANAL-03 | 03-01-PLAN.md | GPT-4.1 verifica ortografia do atestado (ignorando termos técnicos de engenharia) | SATISFIED | Prompt section "VERIFICAÇÃO ORTOGRÁFICA (apenas para Atestados)" with ignore-list; `test_ortografia_art_vazia` and `test_ortografia_atestado_pode_ter_erros` pass |
| ANAL-04 | 03-01-PLAN.md, 03-02-PLAN.md | GPT-4.1 Vision detecta presença de timbre/logo da contratante no atestado | SATISFIED | `AnaliseVisual.tem_timbre` field; `"detail": "high"` in image input; `test_visual_timbre` passes |
| ANAL-05 | 03-01-PLAN.md, 03-02-PLAN.md | GPT-4.1 Vision detecta assinatura visual e extrai nome, cargo, CREA/CPF do assinante | SATISFIED | `AnaliseVisual.assinantes: list[AssinanteInfo]` with nome, cargo, crea_rnp, cpf fields; `test_visual_assinatura` passes; integration test `test_assinante_ruan_real` covers real-doc case |
| ANAL-06 | 03-01-PLAN.md, 03-02-PLAN.md | Pipeline identifica quando assinante NÃO é engenheiro habilitado na área do serviço | SATISFIED | `AssinanteInfo.engenheiro_habilitado: bool`; prompt rule "ADMINISTRADOR... = false"; `test_nao_engenheiro`, `test_engenheiro_habilitado`, `test_administrador_no_resultado_analise` all pass |

No orphaned requirements — all 6 ANAL IDs are claimed by plans 03-01 and/or 03-02 and verified above.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `crea_cat_ai/analysis.py` | 298-303 | `return ResultadoAnalise(confianca=0.0, ...)` on `output_parsed=None` | Info | Intentional safety fallback for GPT model refusals — not a stub, downstream consumers check `confianca` |

No stub patterns, TODO/FIXME comments, empty handlers, or placeholder returns found in the critical path.

### Human Verification Required

#### 1. Live GPT Entity Extraction Accuracy

**Test:** Run `python main.py` with the 5 test PDFs present in `INPUT_DIR` and inspect the "Fase 2: Analise e Extracao de Entidades" output section.

**Expected:**
- ART: profissional.nome contains "ALEXANDRE" (or "NIZO"), crea_rnp is a numeric string, contratante.cnpj present
- Atestado Par 1 (944678...ACT_Alexandre): assinante "RUAN FERNANDES" with cargo "ADMINISTRADOR", Engenheiro: NAO
- Atestado Par 2 (saude indigena.pdf, 32 pages): completes without timeout, at least one assinante detected, Timbre: SIM (Ministry of Health letterhead)
- No Python exceptions or API errors

**Why human:** GPT entity extraction accuracy against real scanned documents is a live API behavior — static analysis can confirm the code calls the API correctly but cannot confirm the model returns correct field values.

#### 2. Integration Test Suite with Real API

**Test:** Set `OPENAI_API_KEY` and run `python -m pytest tests/test_analysis.py -m integration -x -q` with the 5 test PDFs in `Documentos que crea recebe/`.

**Expected:** `test_analisar_documento_integracao`, `test_analise_art_real`, and `test_assinante_ruan_real` all pass (3 passed).

**Why human:** Integration tests require a live OpenAI API key and real PDF files — neither is available in automated verification.

### Gaps Summary

No gaps. All 6 ANAL requirements are implemented, substantive, wired, and data-flowing. The phase goal is met at the code level:

- `ResultadoAnalise` captures every required entity field (CPF, CNPJ, CREA/RNP, nomes, organizações, datas, endereços, escopo)
- `normalizar_crea_rnp()` makes CREA and RNP directly comparable
- Spell-check is correctly scoped to Atestados only in the GPT prompt
- `"detail": "high"` Vision images ensure timbre and signature detection
- `engenheiro_habilitado: bool` on `AssinanteInfo` with correct prompt guidance classifies signer qualification
- `main.py` wires the full Phase 2 + Phase 3 pipeline end-to-end
- 24 unit tests (mocked GPT) + 3 integration tests (real GPT, gated by `@pytest.mark.integration`) — full suite 31 tests pass

Pending: human confirmation that real GPT-4.1 extracts correct ground-truth entities from the 5 test PDFs.

---

_Verified: 2026-03-28_
_Verifier: Claude (gsd-verifier)_
