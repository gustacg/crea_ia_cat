# Phase 6: Complementary Docs & Compliance - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Verificar documentos complementares (Declaracao, Anuencia) e conformidade regulatoria. Declaracao verificada quando necessaria (Art. 59 par. 1), Anuencia verificada em subcontratacao, Anexo IV checklist completo, Res. 1.160/2025 aplicada sobre base 1.137/2023. Produz lista de verificacoes com status CONFORME/NAO_CONFORME/NAO_APLICAVEL e exigencias no formato CREA.

</domain>

<decisions>
## Implementation Decisions

### Declaracao Trigger & Verification (CDOC-01, CDOC-02, CDOC-03, COMP-03)
- **D-01:** Trigger: `engenheiro_habilitado == False` on ANY atestado signer in `ResultadoAnalise.visual.assinantes` — already extracted in Phase 3, no new GPT call needed
- **D-02:** When triggered, search `pacote.complementares` for document with `tipo == TipoDocumento.DECLARACAO`
- **D-03:** Declaracao verification: extract declaring engineer's CREA/RNP and specialty from its `ResultadoAnalise`, then check specialty matches the service area of the ART/Atestado
- **D-04:** Specialty-area matching requires GPT-4.1 — single call to compare engineer title/specialty with ART service scope (semantic, not exact)
- **D-05:** If Declaracao absent when required → generate exigencia: "APRESENTAR DECLARACAO DE PROFISSIONAL HABILITADO NA AREA, DE ACORDO COM O par. 1, DO ART. 59 DA RESOLUCAO 1137 DO CONFEA"

### Declaracao Cross-Reference (CDOC-04)
- **D-06:** Cross-reference Declaracao entities with ART and Atestado: declaring engineer's CREA must be valid, ART number referenced in Declaracao must match, profissional name must match
- **D-07:** Use same matching patterns from Phase 5 (normalizar_crea_rnp for exact, GPT for fuzzy names) — import and reuse matching utilities

### Anuencia Handling (CDOC-03)
- **D-08:** Subcontracting detection: compare `empresa_executora` from ART with the company in the atestado — if different companies and one is subcontractor, Anuencia is required
- **D-09:** If subcontracting detected and no Anuencia in `pacote.complementares` → exigencia
- **D-10:** If Anuencia present → verify it references correct parties (contratante, subcontratada, profissional)
- **D-11:** Neither test pair has subcontracting — this is structural code with no test data validation yet

### Anexo IV Checklist (COMP-01)
- **D-12:** 6 mandatory data categories from Anexo IV (Res. 1.137/2023) verified on the Atestado:
  1. Identificacao do contratante (nome + CNPJ/CPF)
  2. Identificacao do profissional (nome + CREA/RNP)
  3. Descricao do servico/obra (escopo)
  4. Periodo de execucao (datas inicio/termino)
  5. Local da obra (endereco)
  6. Assinatura do contratante (assinatura visual presente)
- **D-13:** Each category checked against `ResultadoAnalise` fields — purely local Python, no GPT needed
- **D-14:** Missing category → `NAO_CONFORME` with specific exigencia identifying which data is absent

### Res. 1.160/2025 Application (COMP-02)
- **D-15:** Researcher must read `Anexos_Resolucao 1160-2025.pdf` to extract specific changes from 1.160/2025 over base 1.137/2023
- **D-16:** Implementation: apply 1.160 rules as overrides on the base compliance logic — code should be structured so base rules come from 1.137 and deltas from 1.160 are clearly separated
- **D-17:** Focus on articles that affect Declaracao requirements, Anexo IV data, and atestado acceptance criteria

### Compliance Output Model
- **D-18:** Pydantic model `ResultadoCompliance` following established project patterns (BaseModel, Field, Optional)
- **D-19:** Fields: `verificacoes` (list of per-check results), `exigencias` (list of formatted strings), `declaracao_necessaria` (bool), `declaracao_encontrada` (bool), `anuencia_necessaria` (bool), `anuencia_encontrada` (bool), `anexo_iv_completo` (bool), `observacoes` (Optional[str])
- **D-20:** Each verificacao has: `requisito` (requirement ID like "CDOC-01"), `descricao`, `status` (CONFORME/NAO_CONFORME/NAO_APLICAVEL), `detalhes`

### GPT vs Local Logic Split
- **D-21:** Local Python (no GPT): Declaracao trigger (bool flag), Anexo IV field presence, Anuencia detection (company comparison), cross-reference exact fields (CREA, ART number)
- **D-22:** GPT-4.1 (semantic): Engineer specialty vs service area matching, Declaracao content validation in context, fuzzy name matching in cross-references
- **D-23:** Reuse `analysis.normalizar_crea_rnp()` and matching patterns from Phase 5 for cross-reference checks

### Claude's Discretion
- Internal prompt design for specialty-area matching GPT call
- Whether to batch GPT calls or make separate ones for Declaracao validation
- How to structure the Anuencia verification when test data becomes available
- Exact exigencia wording for each non-conformity (follow CREA uppercase pattern with legal basis)
- StatusCompliance enum naming (CONFORME/NAO_CONFORME/NAO_APLICAVEL or similar)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Regulatory References
- `Anexos_Resolucao 1160-2025.pdf` — Resolucao 1.160/2025 do CONFEA, contains specific changes to compliance rules. Researcher MUST extract relevant articles affecting Declaracao, Anexo IV, and atestado requirements
- `.planning/PROJECT.md` section Context — Business rules: Declaracao requirement (Art. 59 par. 1), Anuencia rules, exigencia format, test pair known issues

### Core Implementation References
- `crea_cat_ai/analysis.py` — Defines `ResultadoAnalise`, `AssinanteInfo` (with `engenheiro_habilitado` flag), `EntidadesProfissional`, `AnaliseVisual` — the input data consumed by compliance checks
- `crea_cat_ai/compliance.py` — Stub file for Phase 6 implementation (has docstring with responsibilities)
- `crea_cat_ai/matching.py` — Contains `normalizar_crea_rnp` import pattern, `StatusCampo` enum, GPT batch call pattern for reuse
- `crea_cat_ai/ingestion.py` — Defines `TipoDocumento` enum (DECLARACAO, ANUENCIA values), `PacoteDocumentos` (complementares list)
- `config.py` — OPENAI_MODEL, thresholds, PESO_* weights
- `main.py` — Pipeline entry point, needs wiring for compliance module (Phase 6 placeholder at line 137-140)

### Prior Phase Outputs
- `.planning/phases/05-cross-document-matching/05-CONTEXT.md` — Matching patterns, Pydantic model conventions, GPT call patterns established in Phase 5
- `.planning/STATE.md` section Decisions — All accumulated architectural decisions

### Test Data
- `Documentos que crea recebe/` — Contains 5 test documents including Declaracao for Par 1 (Alexandre's declaration)
  - Par 1: Ruan (Administrador) signs atestado → requires Declaracao → Alexandre's Declaracao present
  - Par 2: No Declaracao (no non-engineer signer scenario known)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `analysis.ResultadoAnalise` — Central data model with all extracted entities, visual analysis, assinantes list with `engenheiro_habilitado` flag
- `analysis.AssinanteInfo.engenheiro_habilitado` — Boolean flag already computed in Phase 3, direct trigger for Declaracao requirement
- `analysis.normalizar_crea_rnp()` — CREA/RNP normalization for exact comparison
- `ingestion.TipoDocumento.DECLARACAO` / `.ANUENCIA` — Enum values for filtering complementares
- `ingestion.PacoteDocumentos.complementares` — List of complementary documents already classified
- `matching.StatusCampo` — MATCH/DIVERGENTE/AUSENTE enum, reusable pattern for compliance status
- `config.OPENAI_MODEL` — GPT-4.1 model reference
- OpenAI client pattern: `client = OpenAI(api_key=config.OPENAI_API_KEY)` at module level

### Established Patterns
- Pydantic models for all structured data (BaseModel, Field, Optional, str Enum)
- GPT Responses API with `text_format` for structured output
- Module-level OpenAI client reused between calls
- All logs/output in pt-BR
- `pathlib.Path` for all file paths
- Single GPT call per concern (Phase 3: one call per document; Phase 5: one batch for all fuzzy/semantic)
- Integration tests marked with `@pytest.mark.integration`, excluded from default runs

### Integration Points
- `main.py` currently has placeholder at lines 137-140 for Phase 6
- Phase 6 module receives: `pacote` (PacoteDocumentos), `resultados_analise` (dict[str, ResultadoAnalise]), `resultado_cruzamento` (ResultadoCruzamento)
- Phase 6 output feeds into Phase 7 (verdict/scoring) — `ResultadoCompliance` will be consumed alongside matching results

</code_context>

<specifics>
## Specific Ideas

- Par 1 is the critical test case: Ruan (Administrador) signs the atestado → must trigger Declaracao requirement → Alexandre's Declaracao file (944678.2026__DECLARACAO__ENG_2_assinado__1_05022026162803.pdf) must be found in complementares and verified
- Exigencias must follow real CREA format: uppercase declarative sentences with legal basis (e.g., "APRESENTAR DECLARACAO DE PROFISSIONAL HABILITADO NA AREA, DE ACORDO COM O par. 1, DO ART. 59 DA RESOLUCAO 1137 DO CONFEA")
- RNP/CREA equivalence rule carries forward — use same normalization in cross-references
- compliance.py stub already has the correct docstring with all responsibilities listed

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-complementary-docs-compliance*
*Context gathered: 2026-03-28 via --auto mode*
