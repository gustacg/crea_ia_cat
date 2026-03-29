# Phase 5: Cross-Document Matching - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Cruzamento de todos os campos sobrepostos entre Atestado e ART. Cada campo recebe status MATCH/DIVERGENTE/AUSENTE. Inclui: identifiers exatos (CPF, CNPJ, CREA/RNP), fuzzy matching de nomes/empresas/endereços via GPT-4.1, comparação semântica de escopo via GPT-4.1, validação de datas por intervalo, e comparação de valores financeiros/contrato quando presentes.

</domain>

<decisions>
## Implementation Decisions

### Matching Strategy
- **D-01:** Single GPT-4.1 call batching all fuzzy/semantic comparisons (nomes, empresas, endereços, escopo) — reduces API cost, maintains context coherence, consistent with Phase 3 single-call-per-document pattern
- **D-02:** Exact matching (CPF, CNPJ, CREA/RNP) done locally in Python — no need for GPT, just string normalization and comparison
- **D-03:** Date interval validation done locally in Python — parse dates, check atestado dates are WITHIN ART date range

### Result Structure
- **D-04:** Pydantic model `ResultadoCruzamento` with per-field `StatusCampo` enum (MATCH, DIVERGENTE, AUSENTE) — type-safe, consistent with analysis.py Pydantic pattern
- **D-05:** Each field comparison includes: status, valor_art, valor_atestado, detalhes (explanation string from GPT for fuzzy/semantic)
- **D-06:** Overall result includes list of all field comparisons + summary counts (matches, divergencias, ausentes)

### Date Interval Logic
- **D-07:** Strict interval check — atestado dates must be WITHIN ART date range (data_inicio >= ART inicio, data_termino <= ART termino)
- **D-08:** Missing or malformed dates → AUSENTE status (not DIVERGENTE) — absence is not fraud
- **D-09:** Use `normalizar_crea_rnp` pattern from analysis.py for all identifier normalization — strip non-digits before comparison

### Semantic Scope Comparison
- **D-10:** GPT-4.1 compares escopo/objeto semantically and returns confidence score + justification
- **D-11:** Known divergence "AR CLIMA SOLUÇÕES" vs "HIDRO-CLIMA Construções" (Par 2) MUST be detected as DIVERGENTE for empresa

### Claude's Discretion
- Internal implementation details of the GPT prompt for fuzzy/semantic matching
- Whether to use Responses API (structured output) or chat.completions for the matching call — follow existing pattern from analysis.py (Responses API)
- How to handle the case where both ART and Atestado have missing fields (both AUSENTE)
- Config.py weight integration (PESO_* constants) — Phase 5 focuses on comparison; scoring is Phase 7

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core Implementation References
- `crea_cat_ai/analysis.py` — Defines ResultadoAnalise (the input data model for matching), GPT-4.1 Vision call pattern, Pydantic structured output pattern
- `crea_cat_ai/matching.py` — Stub file for Phase 5 implementation
- `crea_cat_ai/ingestion.py` — Defines DocumentoCarregado, PacoteDocumentos, TipoDocumento
- `config.py` — PESO_* constants for field weights, OPENAI_MODEL, PROJECT_ROOT
- `main.py` — Pipeline entry point, needs wiring for matching module

### Business Rules
- `Anexos_Resolucao 1160-2025.pdf` — Resolução 1.160/2025 do CONFEA with current rules
- `.planning/PROJECT.md` §Context — CREA business rules, test document pairs, known divergences

### Prior Phase Outputs
- `.planning/phases/04-metadata-digital-signature/04-RESEARCH.md` — Gov-Br PKI findings (context for what Phase 4 produces)
- `.planning/STATE.md` §Decisions — All accumulated decisions including RNP/CREA equivalence, date interval rules

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `analysis.ResultadoAnalise` — Central data model with all extracted entities (profissional, contratante, empresa_executora, endereco_obra, datas, escopo, valor_contrato, contrato_numero)
- `analysis.normalizar_crea_rnp()` — Strips non-digits from CREA/RNP for exact comparison
- `ingestion.PacoteDocumentos` — Groups documents by type (art, atestado, complementares)
- `config.OPENAI_MODEL` — GPT-4.1 model reference
- OpenAI client pattern in analysis.py — `client = OpenAI(api_key=config.OPENAI_API_KEY)`

### Established Patterns
- Pydantic models for all structured data (BaseModel with Field, Optional)
- GPT Responses API with `text_format` for structured output
- Module-level OpenAI client reused between calls
- All logs/output in pt-BR
- `pathlib.Path` for all file paths

### Integration Points
- `main.py` calls `analysis.analisar_pacote(pacote)` → returns `dict[str, ResultadoAnalise]`
- Phase 5 matching will consume `ResultadoAnalise` from ART and Atestado to produce `ResultadoCruzamento`
- `main.py` needs new section after Phase 3 analysis to call matching module

</code_context>

<specifics>
## Specific Ideas

- Par 2 known divergence: ART says "AR CLIMA SOLUÇÕES" but atestado says "HIDRO-CLIMA Construções" — this is a REAL divergence that must be caught
- Par 1: Assinante is Administrador (not engineer) — this is Phase 6 (compliance) scope, not Phase 5
- CREA/RNP equivalence: already implemented in `normalizar_crea_rnp()` — reuse for exact matching

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-cross-document-matching*
*Context gathered: 2026-03-29 via --auto mode*
