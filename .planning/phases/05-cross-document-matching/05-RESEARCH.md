# Phase 5: Cross-Document Matching - Research

**Researched:** 2026-03-28
**Domain:** Python cross-document field comparison, GPT-4.1 fuzzy/semantic matching, Pydantic structured output
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Single GPT-4.1 call batching all fuzzy/semantic comparisons (nomes, empresas, endereços, escopo) — reduces API cost, maintains context coherence, consistent with Phase 3 single-call-per-document pattern
- **D-02:** Exact matching (CPF, CNPJ, CREA/RNP) done locally in Python — no need for GPT, just string normalization and comparison
- **D-03:** Date interval validation done locally in Python — parse dates, check atestado dates are WITHIN ART date range
- **D-04:** Pydantic model `ResultadoCruzamento` with per-field `StatusCampo` enum (MATCH, DIVERGENTE, AUSENTE) — type-safe, consistent with analysis.py Pydantic pattern
- **D-05:** Each field comparison includes: status, valor_art, valor_atestado, detalhes (explanation string from GPT for fuzzy/semantic)
- **D-06:** Overall result includes list of all field comparisons + summary counts (matches, divergencias, ausentes)
- **D-07:** Strict interval check — atestado dates must be WITHIN ART date range (data_inicio >= ART inicio, data_termino <= ART termino)
- **D-08:** Missing or malformed dates → AUSENTE status (not DIVERGENTE) — absence is not fraud
- **D-09:** Use `normalizar_crea_rnp` pattern from analysis.py for all identifier normalization — strip non-digits before comparison
- **D-10:** GPT-4.1 compares escopo/objeto semantically and returns confidence score + justification
- **D-11:** Known divergence "AR CLIMA SOLUÇÕES" vs "HIDRO-CLIMA Construções" (Par 2) MUST be detected as DIVERGENTE for empresa

### Claude's Discretion

- Internal implementation details of the GPT prompt for fuzzy/semantic matching
- Whether to use Responses API (structured output) or chat.completions for the matching call — follow existing pattern from analysis.py (Responses API)
- How to handle the case where both ART and Atestado have missing fields (both AUSENTE)
- Config.py weight integration (PESO_* constants) — Phase 5 focuses on comparison; scoring is Phase 7

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| XREF-01 | CPF, CNPJ, CREA/RNP comparados com match exato (após normalização RNP/CREA) | Local Python comparison using `normalizar_crea_rnp()` from analysis.py; strip non-digits, compare strings |
| XREF-02 | Nomes e empresas comparados com tolerância a variações via GPT-4.1 | Single batched GPT call (D-01); prompt receives ART and Atestado field values side-by-side |
| XREF-03 | Endereço da obra comparado com tolerância a variações de formatação | Batched into the same GPT call as XREF-02; GPT handles abbreviation and format variants |
| XREF-04 | Datas do atestado validadas como DENTRO do intervalo de datas da ART | Local Python: parse date strings with multiple format fallbacks; strict containment check (D-07) |
| XREF-05 | Valores financeiros e número de contrato comparados quando presentes | Exact string comparison for contrato_numero; normalized numeric comparison for valor_contrato; batched to GPT when normalization is ambiguous |
| XREF-06 | Escopo/objeto do serviço comparado semanticamente via GPT-4.1 | GPT returns confidence score (0.0–1.0) + justification in the same batched call |
| XREF-07 | Empresa executora/contratada comparada entre documentos | Batched into GPT call; D-11 case ("AR CLIMA" vs "HIDRO-CLIMA") must be DIVERGENTE |
</phase_requirements>

---

## Summary

Phase 5 implements `matching.py` — the module that consumes two `ResultadoAnalise` objects (one from ART, one from Atestado) and produces a `ResultadoCruzamento` with per-field comparison statuses. The module has three distinct execution paths: (1) local exact matching for identifiers (CPF, CNPJ, CREA/RNP) and numeric values, (2) local date interval validation, and (3) a single batched GPT-4.1 call for all fuzzy/semantic comparisons (names, companies, addresses, scope).

The architecture mirrors Phase 3 exactly: Pydantic models for structured output, OpenAI Responses API with `text_format=Model`, module-level client reuse, and all text in pt-BR. No new dependencies are needed — all required tools already exist in the project environment.

The critical success criterion for Phase 5 is detection of the known Par 2 divergence: "AR CLIMA SOLUÇÕES" (ART) vs "HIDRO-CLIMA Construções" (Atestado). These are semantically and lexically distinct company names — not abbreviations or format variants — so GPT must classify them as DIVERGENTE with high confidence. The prompt must be designed to NOT be over-tolerant (i.e., it should not treat any name difference as a minor variation).

**Primary recommendation:** Implement `matching.py` as a three-layer module: exact-match layer (pure Python), date-interval layer (pure Python), GPT-batch layer (single Responses API call). Wire into `main.py` after Phase 3 analysis, before Phase 6. Test with three unit test classes (exact, dates, GPT mock) plus one integration test per Par.

---

## Standard Stack

### Core (all already installed)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| openai (Python SDK) | latest | GPT-4.1 Responses API for fuzzy/semantic batch | Same pattern as analysis.py — Responses API with structured output |
| pydantic | included with openai | `ResultadoCruzamento` model + `StatusCampo` enum | Consistent with all other phase models |
| re (stdlib) | — | Identifier normalization (reuse of `normalizar_crea_rnp` pattern) | Already used in analysis.py |
| datetime (stdlib) | — | Date parsing and interval comparison | Required for XREF-04 (D-03) |

**No new dependencies.** All four libraries are already available in the project environment.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib (stdlib) | — | File paths in integration tests | All file access |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single batched GPT call | Separate GPT call per field | Higher cost, lower context coherence — REJECTED (D-01) |
| Local fuzzy matching (rapidfuzz, difflib) | GPT-4.1 for fuzzy names | Misses semantic divergence like "AR CLIMA" vs "HIDRO-CLIMA" — REJECTED |
| chat.completions | Responses API | Responses API gives typed Pydantic output — use Responses API (existing pattern) |

---

## Architecture Patterns

### Recommended Module Structure

```
crea_cat_ai/matching.py
├── StatusCampo (enum: MATCH, DIVERGENTE, AUSENTE)
├── ComparacaoCampo (Pydantic: status, campo, valor_art, valor_atestado, detalhes, confianca)
├── ResultadoCruzamento (Pydantic: comparacoes list, total_match, total_divergente, total_ausente)
├── ResultadoGPTCruzamento (Pydantic: output schema for GPT batch call)
├── _comparar_identificadores() → list[ComparacaoCampo]   # local exact match
├── _comparar_datas() → ComparacaoCampo                   # local interval check
├── _comparar_via_gpt() → list[ComparacaoCampo]           # single GPT batch call
└── cruzar_documentos(art, atestado) → ResultadoCruzamento  # public API
```

### Pattern 1: StatusCampo Enum

**What:** A `str` enum (same as `TipoDocumento`) so values serialize cleanly in JSON and are directly comparable.

**Example:**
```python
from enum import Enum

class StatusCampo(str, Enum):
    MATCH = "MATCH"
    DIVERGENTE = "DIVERGENTE"
    AUSENTE = "AUSENTE"
```

### Pattern 2: ComparacaoCampo Pydantic Model

**What:** Per-field comparison result. Matches D-05 specification.

**Example:**
```python
from pydantic import BaseModel, Field
from typing import Optional

class ComparacaoCampo(BaseModel):
    campo: str                              # Nome do campo (ex: "cpf", "escopo")
    status: StatusCampo
    valor_art: Optional[str] = None         # Valor extraído da ART
    valor_atestado: Optional[str] = None    # Valor extraído do Atestado
    confianca: float = 1.0                  # 1.0 para exact match; GPT score para fuzzy
    detalhes: Optional[str] = None          # Explicação (obrigatório quando DIVERGENTE ou AUSENTE)
```

### Pattern 3: ResultadoCruzamento Pydantic Model

**What:** Aggregate result with all field comparisons and summary counts (D-06).

**Example:**
```python
class ResultadoCruzamento(BaseModel):
    comparacoes: list[ComparacaoCampo] = Field(default_factory=list)
    total_match: int = 0
    total_divergente: int = 0
    total_ausente: int = 0
    observacoes: Optional[str] = None
```

### Pattern 4: Exact Identifier Matching (D-02)

**What:** Pure Python. Normalize with `normalizar_crea_rnp` pattern, compare strings. Both absent → AUSENTE. One absent → AUSENTE. Values differ after normalization → DIVERGENTE.

**Example:**
```python
from crea_cat_ai.analysis import normalizar_crea_rnp

def _comparar_identificadores(
    art: ResultadoAnalise,
    atestado: ResultadoAnalise,
) -> list[ComparacaoCampo]:
    comparacoes = []

    # CREA/RNP — D-09: strip non-digits
    crea_art = normalizar_crea_rnp(
        art.profissional.crea_rnp if art.profissional else None
    )
    crea_atestado = normalizar_crea_rnp(
        atestado.profissional.crea_rnp if atestado.profissional else None
    )
    comparacoes.append(_status_exato("crea_rnp", crea_art, crea_atestado))

    # CPF do profissional
    cpf_art = normalizar_crea_rnp(
        art.profissional.cpf if art.profissional else None
    )
    cpf_atestado = normalizar_crea_rnp(
        atestado.profissional.cpf if atestado.profissional else None
    )
    comparacoes.append(_status_exato("cpf_profissional", cpf_art, cpf_atestado))

    # CNPJ contratante
    cnpj_art = normalizar_crea_rnp(
        art.contratante.cnpj if art.contratante else None
    )
    cnpj_atestado = normalizar_crea_rnp(
        atestado.contratante.cnpj if atestado.contratante else None
    )
    comparacoes.append(_status_exato("cnpj_contratante", cnpj_art, cnpj_atestado))

    return comparacoes


def _status_exato(campo: str, val_art: str | None, val_atestado: str | None) -> ComparacaoCampo:
    if val_art is None and val_atestado is None:
        return ComparacaoCampo(
            campo=campo, status=StatusCampo.AUSENTE,
            detalhes="Campo ausente em ambos os documentos",
        )
    if val_art is None or val_atestado is None:
        presente = val_art or val_atestado
        return ComparacaoCampo(
            campo=campo, status=StatusCampo.AUSENTE,
            valor_art=val_art, valor_atestado=val_atestado,
            detalhes=f"Campo presente somente em um documento: {presente}",
        )
    if val_art == val_atestado:
        return ComparacaoCampo(
            campo=campo, status=StatusCampo.MATCH,
            valor_art=val_art, valor_atestado=val_atestado,
            confianca=1.0,
        )
    return ComparacaoCampo(
        campo=campo, status=StatusCampo.DIVERGENTE,
        valor_art=val_art, valor_atestado=val_atestado,
        confianca=0.0,
        detalhes=f"Valores divergentes após normalização: {val_art!r} != {val_atestado!r}",
    )
```

### Pattern 5: Date Interval Validation (D-03, D-07, D-08)

**What:** Pure Python. Parse date strings in multiple formats (DD/MM/YYYY, YYYY-MM-DD, DD/MM/YY). Check atestado dates are WITHIN ART date range. Missing dates → AUSENTE (D-08).

**Date format priority order:** Try DD/MM/YYYY first (CREA documents), then ISO (YYYY-MM-DD), then DD/MM/YY.

**Example:**
```python
from datetime import date

DATE_FORMATS = ["%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"]

def _parse_date(valor: str | None) -> date | None:
    if not valor:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(valor.strip(), fmt).date()
        except ValueError:
            continue
    return None  # Malformed → treat as absent (D-08)


def _comparar_datas(
    art: ResultadoAnalise,
    atestado: ResultadoAnalise,
) -> ComparacaoCampo:
    inicio_art = _parse_date(art.datas.data_inicio)
    termino_art = _parse_date(art.datas.data_termino)
    inicio_atestado = _parse_date(atestado.datas.data_inicio)
    termino_atestado = _parse_date(atestado.datas.data_termino)

    # D-08: If ART interval not parseable, cannot validate
    if inicio_art is None or termino_art is None:
        return ComparacaoCampo(
            campo="intervalo_datas",
            status=StatusCampo.AUSENTE,
            detalhes="Datas da ART ausentes ou malformadas — não é possível validar intervalo",
        )

    # D-08: If atestado dates absent, AUSENTE
    if inicio_atestado is None and termino_atestado is None:
        return ComparacaoCampo(
            campo="intervalo_datas",
            status=StatusCampo.AUSENTE,
            valor_art=f"{art.datas.data_inicio} a {art.datas.data_termino}",
            detalhes="Datas do atestado ausentes ou malformadas",
        )

    # D-07: Strict containment check
    violacoes = []
    if inicio_atestado and inicio_atestado < inicio_art:
        violacoes.append(f"Início do atestado ({inicio_atestado}) é anterior ao início da ART ({inicio_art})")
    if termino_atestado and termino_atestado > termino_art:
        violacoes.append(f"Término do atestado ({termino_atestado}) é posterior ao término da ART ({termino_art})")

    if violacoes:
        return ComparacaoCampo(
            campo="intervalo_datas",
            status=StatusCampo.DIVERGENTE,
            valor_art=f"{art.datas.data_inicio} a {art.datas.data_termino}",
            valor_atestado=f"{atestado.datas.data_inicio} a {atestado.datas.data_termino}",
            confianca=0.0,
            detalhes="; ".join(violacoes),
        )

    return ComparacaoCampo(
        campo="intervalo_datas",
        status=StatusCampo.MATCH,
        valor_art=f"{art.datas.data_inicio} a {art.datas.data_termino}",
        valor_atestado=f"{atestado.datas.data_inicio} a {atestado.datas.data_termino}",
        confianca=1.0,
    )
```

### Pattern 6: Batched GPT Fuzzy/Semantic Call (D-01, D-10)

**What:** Single Responses API call. Input is a structured text block with both documents' values for: nome_profissional, empresa_contratante, empresa_executora, endereco_obra, escopo, valor_contrato, contrato_numero. GPT returns a structured list of field comparisons, each with status + confidence score + justification.

**GPT output schema for the batch call:**
```python
class ComparacaoGPT(BaseModel):
    campo: str
    status: StatusCampo
    confianca: float       # 0.0 a 1.0
    detalhes: str          # Justificativa obrigatória

class ResultadoGPTCruzamento(BaseModel):
    comparacoes: list[ComparacaoGPT]
```

**Prompt design (key constraint — D-11 must be DIVERGENTE):**

The prompt MUST include explicit guidance that semantically different entities are DIVERGENTE, not MATCH. The "AR CLIMA SOLUÇÕES" vs "HIDRO-CLIMA Construções" case is a real divergence — different companies entirely. The prompt must NOT be over-tolerant.

**Recommended prompt excerpt:**
```
REGRA CRÍTICA — Critério de MATCH vs DIVERGENTE:
- MATCH: variações de formatação, abreviação ou capitalização do MESMO nome/entidade.
  Exemplos de MATCH: "Taboca Agro" vs "TABOCA AGRO NEGÓCIOS LTDA", "Rua Dom Pedro II" vs "R. Dom Pedro 2"
- DIVERGENTE: nomes ou entidades DISTINTAS, mesmo que pareçam relacionados.
  Exemplos de DIVERGENTE: "AR CLIMA SOLUÇÕES" vs "HIDRO-CLIMA Construções" são empresas diferentes.
- AUSENTE: campo não informado em um ou ambos os documentos.

Para escopo/objeto: retorne confianca entre 0.0 e 1.0 indicando similaridade semântica.
confianca >= 0.7 + status MATCH = escopos compatíveis.
confianca < 0.7 + status DIVERGENTE = escopos incompatíveis.
```

**Input block format (texto para o GPT):**
```
Documento ART:
- Nome do profissional: {art.profissional.nome}
- Empresa contratante: {art.contratante.nome}
- Empresa executora: {art.empresa_executora.nome if art.empresa_executora else "N/A"}
- Endereço da obra: {endereco_formatado(art.endereco_obra)}
- Escopo: {art.escopo}
- Valor do contrato: {art.valor_contrato}
- Número do contrato: {art.contrato_numero}

Documento Atestado:
- Nome do profissional: {atestado.profissional.nome}
- Empresa contratante: {atestado.contratante.nome}
- Empresa executora: {atestado.empresa_executora.nome if atestado.empresa_executora else "N/A"}
- Endereço da obra: {endereco_formatado(atestado.endereco_obra)}
- Escopo: {atestado.escopo}
- Valor do contrato: {atestado.valor_contrato}
- Número do contrato: {atestado.contrato_numero}

Campos a comparar: nome_profissional, empresa_contratante, empresa_executora, endereco_obra, escopo, valor_contrato, contrato_numero
```

### Pattern 7: Public API — `cruzar_documentos()`

**What:** The single public function called by `main.py`. Receives two `ResultadoAnalise` objects, runs all three layers, merges results into `ResultadoCruzamento` with computed totals.

**Signature:**
```python
def cruzar_documentos(
    art: ResultadoAnalise,
    atestado: ResultadoAnalise,
) -> ResultadoCruzamento:
    comparacoes: list[ComparacaoCampo] = []

    # Layer 1: exact identifiers (local Python)
    comparacoes.extend(_comparar_identificadores(art, atestado))

    # Layer 2: date interval (local Python)
    comparacoes.append(_comparar_datas(art, atestado))

    # Layer 3: fuzzy/semantic (single GPT call)
    comparacoes.extend(_comparar_via_gpt(art, atestado))

    return ResultadoCruzamento(
        comparacoes=comparacoes,
        total_match=sum(1 for c in comparacoes if c.status == StatusCampo.MATCH),
        total_divergente=sum(1 for c in comparacoes if c.status == StatusCampo.DIVERGENTE),
        total_ausente=sum(1 for c in comparacoes if c.status == StatusCampo.AUSENTE),
    )
```

### Pattern 8: main.py Wiring

**What:** After Phase 3 (`resultados_analise`) is complete, call `cruzar_documentos()`. Requires ART and Atestado to be present in the results dict.

**Where to insert in main.py:** After "Fase 2" block (Phase 3 analysis), before the "Fases 5-7" placeholder comment.

```python
from crea_cat_ai import matching

# Phase 5: Cruzamento de Documentos
print()
print("--- Fase 4: Cruzamento de Documentos ---")
resultado_cruzamento = None
if pacote.art and pacote.atestado:
    art_analise = resultados_analise.get(TipoDocumento.ART.value)
    atestado_analise = resultados_analise.get(TipoDocumento.ATESTADO.value)
    if art_analise and atestado_analise:
        resultado_cruzamento = matching.cruzar_documentos(art_analise, atestado_analise)
        print(f"  Matches: {resultado_cruzamento.total_match}")
        print(f"  Divergências: {resultado_cruzamento.total_divergente}")
        print(f"  Ausentes: {resultado_cruzamento.total_ausente}")
        for comp in resultado_cruzamento.comparacoes:
            if comp.status != StatusCampo.MATCH:
                print(f"  [{comp.status.value}] {comp.campo}: {comp.detalhes}")
else:
    print("  ART ou Atestado ausente — cruzamento ignorado")
```

### Anti-Patterns to Avoid

- **Over-tolerant fuzzy matching:** Do NOT use Levenshtein distance alone. "AR CLIMA" and "HIDRO-CLIMA" have similar length and characters but are different companies. GPT semantic understanding is required.
- **DIVERGENTE for absent fields:** When a field is not present in one or both documents, use AUSENTE — not DIVERGENTE (D-08). DIVERGENTE implies presence with conflicting values.
- **Separate GPT calls per fuzzy field:** One batched call (D-01). Do not make 7 separate API calls for name, company, address, scope, etc.
- **Strict date parsing with single format:** Brazilian CREA documents use DD/MM/YYYY; some ISO dates may appear. Always try multiple format strings.
- **Slicing date strings:** Do not slice — use full `strptime`. This was a bug fixed in Phase 4 (`_parse_pdf_date`). Apply the same lesson here.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Semantic similarity of scope text | Custom cosine similarity + word embeddings | GPT-4.1 semantic comparison in batch call | GPT understands domain context (CREA, engineering terms); embeddings require a separate model |
| Company name fuzzy matching | Levenshtein / RapidFuzz | GPT-4.1 in batch call | "AR CLIMA SOLUÇÕES" vs "HIDRO-CLIMA Construções" — edit distance would give partial match, GPT correctly identifies them as distinct entities |
| Date format detection | Regex forest for DD/MM/YYYY, ISO, etc. | Simple `strptime` loop over `DATE_FORMATS` list | Python stdlib handles all needed formats; no custom regex needed |
| Identifier normalization | Custom CREA normalization | Reuse `normalizar_crea_rnp()` from analysis.py | Already tested, handles all known formats (1120893194MA, CREA MA 1015902979, 4388D/GO) |

**Key insight:** GPT-4.1 semantic matching is not just "nicer" — it is architecturally required for the D-11 blocker. Pure string similarity algorithms cannot reliably distinguish "different company" from "abbreviated company name" without domain knowledge.

---

## Runtime State Inventory

Phase 5 is a greenfield code addition — no rename, no migration. This section is not applicable.

---

## Common Pitfalls

### Pitfall 1: Over-Tolerant GPT Prompt

**What goes wrong:** GPT treats "AR CLIMA SOLUÇÕES" and "HIDRO-CLIMA Construções" as a minor name variation and returns MATCH or a high-confidence MATCH. Par 2 passes as ADERENTE when it should be PENDENTE/SUSPEITO.

**Why it happens:** Without explicit guidance, GPT may assume document data typically has formatting variations and lean toward MATCH to be "helpful."

**How to avoid:** The prompt must explicitly state the MATCH vs DIVERGENTE criterion with the "AR CLIMA" example (or a structurally equivalent example). Include: "Empresas com nomes completamente distintos como 'AR CLIMA SOLUÇÕES' e 'HIDRO-CLIMA Construções' são DIVERGENTE — não são variações da mesma empresa."

**Warning signs:** Integration test for Par 2 shows `empresa_executora` as MATCH.

### Pitfall 2: DIVERGENTE for Both-Absent Fields

**What goes wrong:** When `art.contratante` is `None` AND `atestado.contratante` is `None`, the comparison emits DIVERGENTE because both values are non-equal (`None != None` would be caught before this, but the GPT prompt might output DIVERGENTE for absent fields).

**Why it happens:** `_status_exato` helper must check for both-absent before comparing. GPT prompt must specify that absent = AUSENTE.

**How to avoid:** Always check for None before comparison in `_status_exato`. Include in GPT prompt: "Se o campo não estiver presente em nenhum dos documentos, retorne AUSENTE."

**Warning signs:** `total_ausente` is 0 even for documents with sparse data.

### Pitfall 3: Date Parsing Fails on Real CREA Documents

**What goes wrong:** Real ART PDFs extracted by GPT may return dates as "12/05/2025", "2025-05-12", or even "maio de 2025". `strptime` raises `ValueError` on unrecognized formats, crashing the pipeline.

**Why it happens:** GPT-extracted dates are free text — the model normalizes them but not always to a single format. "maio de 2025" is possible for month-only dates.

**How to avoid:** The `_parse_date` function must return `None` on parse failure (catch all `ValueError`, do not reraise). Per D-08, parse failure → AUSENTE, not a crash.

**Warning signs:** `ValueError: time data 'maio de 2025' does not match format '%d/%m/%Y'` in test logs.

### Pitfall 4: GPT Responses API Schema Mismatch

**What goes wrong:** `ResultadoGPTCruzamento` has `comparacoes: list[ComparacaoGPT]` but GPT returns a field named `campos` or `resultados`. The Responses API parse returns `None`, triggering the fallback path with empty comparisons.

**Why it happens:** GPT may deviate from schema field names unless they are clearly named. Pydantic field names must be unambiguous.

**How to avoid:** Use `Field(description=...)` on each Pydantic field in `ComparacaoGPT` to anchor GPT to the correct structure. Test with a unit test that mocks the client and verifies the correct schema.

**Warning signs:** `resultado_cruzamento.comparacoes` is empty after a GPT call.

### Pitfall 5: Reusing the Same Dict Key When Both ART and Atestado Are Same Type

**What goes wrong:** `resultados_analise` from `analisar_pacote()` is keyed by `doc.tipo.value`. If for some reason two documents share the same `TipoDocumento`, the second overwrites the first. Phase 5 must defensively handle the case where `resultados_analise.get(TipoDocumento.ART.value)` returns `None`.

**Why it happens:** Unlikely in practice (classification happens in Phase 2), but the `main.py` wiring must guard against it.

**How to avoid:** Check `if art_analise and atestado_analise` before calling `cruzar_documentos()`. Already shown in Pattern 8 above.

---

## Code Examples

### Verified Pattern: Responses API with Structured Output

From `crea_cat_ai/analysis.py` (Phase 3 — HIGH confidence, production code):

```python
# Source: crea_cat_ai/analysis.py, lines 290-303
response = client.responses.parse(
    model=config.OPENAI_MODEL,
    instructions=PROMPT_ANALISE_BASE,
    input=input_content,
    text_format=ResultadoAnalise,
)

if response.output_parsed is None:
    return ResultadoAnalise(
        confianca=0.0,
        observacoes="Modelo recusou análise do documento",
    )

return response.output_parsed
```

Phase 5 must follow this exact pattern for the GPT batch call. The `None` fallback must be handled: when `output_parsed` is `None`, return an empty `ResultadoCruzamento` (all fields AUSENTE) with an observation string.

### Verified Pattern: str Enum for TipoDocumento

From `crea_cat_ai/ingestion.py` (Phase 2 decision, confirmed in STATE.md):

```python
# Source: STATE.md "[Phase 02]: TipoDocumento as str Enum"
class TipoDocumento(str, Enum):
    ART = "ART"
    ATESTADO = "Atestado"
    ...
```

`StatusCampo` must follow the same pattern — `class StatusCampo(str, Enum)`.

### Verified Pattern: Module-Level OpenAI Client

From `crea_cat_ai/analysis.py` (line 123):

```python
# Source: crea_cat_ai/analysis.py, line 123
client = OpenAI(api_key=config.OPENAI_API_KEY)
```

`matching.py` must declare `client = OpenAI(api_key=config.OPENAI_API_KEY)` at module level and reuse it. Do not instantiate inside functions.

### Verified Pattern: normalizar_crea_rnp

From `crea_cat_ai/analysis.py` (lines 172–191):

```python
# Source: crea_cat_ai/analysis.py, lines 172-191
def normalizar_crea_rnp(valor: str | None) -> str | None:
    if valor is None:
        return None
    digitos = re.sub(r"\D", "", valor)
    return digitos if digitos else None
```

Import and reuse from `analysis.py`. Do NOT re-implement. This function has full unit test coverage in `tests/test_analysis.py`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 17 separate libraries (Tesseract, spaCy, LanguageTool, rapidfuzz, etc.) | GPT-4.1 as primary engine | 2026-03-28 (stack pivot) | Phase 5 must NOT introduce rapidfuzz or difflib for fuzzy matching — GPT handles it |
| chat.completions for structured data | Responses API with `text_format=Pydantic` | Phase 2 decision | All GPT calls in this project use Responses API — Phase 5 must too |
| Strict date format assumption | Multiple format fallback + None-on-failure | Phase 4 lesson (`_parse_pdf_date`) | Date parsing must be tolerant and never raise |

**Deprecated/outdated:**
- `rapidfuzz`, `python-Levenshtein`, `difflib` for document field comparison: replaced by GPT-4.1 in this project's stack
- `chat.completions.create()` for structured output: use `responses.parse()` instead

---

## Open Questions

1. **Contrato numero comparison: exact or fuzzy?**
   - What we know: `contrato_numero` is a structured field (e.g., "0352015"). Likely an exact string after stripping whitespace.
   - What's unclear: Formatting variants (e.g., "352015" vs "0352015" — leading zeros). Should normalization strip leading zeros?
   - Recommendation: Normalize by stripping non-digits and leading zeros for comparison. If both parse to same integer → MATCH. Batch to GPT only if one document has a text-format contract reference.

2. **What if atestado references an ART number that matches `art.numero_documento`?**
   - What we know: `atestado.art_referenciada` holds the ART number cited in the atestado. `art.numero_documento` holds the ART's own number (e.g., "MA20250929762").
   - What's unclear: Should Phase 5 compare `atestado.art_referenciada` with `art.numero_documento`? This is not in XREF-01 through XREF-07 explicitly.
   - Recommendation: Include this comparison under XREF-01 (identifier exact match). If present, it is a high-value integrity check — normalize and compare. If absent in atestado, AUSENTE (not DIVERGENTE).

3. **empresa_executora vs contratante — which field to use for XREF-07?**
   - What we know: `ResultadoAnalise` has both `contratante` and `empresa_executora`. Par 2 divergence is "AR CLIMA SOLUÇÕES" (ART) vs "HIDRO-CLIMA Construções" (Atestado) — both likely appear as `empresa_executora` or `contratante`.
   - What's unclear: Which field holds the divergent company name in the real extracted data. The GPT batch prompt should compare both fields separately.
   - Recommendation: Compare both `contratante.nome` and `empresa_executora.nome` as separate fields in the batch call. The divergence will surface in whichever field contains the company name.

---

## Environment Availability

All dependencies for Phase 5 are already installed and verified by Phase 1 (`setup_check.py`). No new installations required.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| openai SDK | GPT batch call (D-01) | Yes | latest (Phase 1 verified) | — |
| pydantic | ResultadoCruzamento model | Yes | bundled with openai | — |
| Python stdlib datetime | Date interval check (D-03) | Yes | Python 3.13 | — |
| Python stdlib re | Identifier normalization | Yes | Python 3.13 | — |
| OPENAI_API_KEY env var | GPT call | Yes (user has key) | — | Integration tests skip if absent |

**No missing dependencies. Phase 5 can execute immediately without any environment setup.**

---

## Validation Architecture

`nyquist_validation` is enabled (config.json `"nyquist_validation": true`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pytest.ini` (exists, root of project) |
| Quick run command | `pytest tests/test_matching.py -v` |
| Full suite command | `pytest tests/test_matching.py tests/test_integration_phase5.py -v` |
| Integration run command | `pytest tests/test_integration_phase5.py -v -m integration` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| XREF-01 | CPF/CNPJ/CREA exact match after normalization | unit | `pytest tests/test_matching.py::TestMatchExato -v` | No — Wave 0 |
| XREF-01 | Both absent → AUSENTE | unit | `pytest tests/test_matching.py::TestMatchExato::test_ambos_ausentes -v` | No — Wave 0 |
| XREF-01 | One absent → AUSENTE | unit | `pytest tests/test_matching.py::TestMatchExato::test_um_ausente -v` | No — Wave 0 |
| XREF-01 | Values differ → DIVERGENTE | unit | `pytest tests/test_matching.py::TestMatchExato::test_divergente -v` | No — Wave 0 |
| XREF-02 | Nome profissional fuzzy match via GPT mock | unit | `pytest tests/test_matching.py::TestGPTCruzamento -v` | No — Wave 0 |
| XREF-03 | Endereço fuzzy match via GPT mock | unit | `pytest tests/test_matching.py::TestGPTCruzamento -v` | No — Wave 0 |
| XREF-04 | Atestado dates within ART interval → MATCH | unit | `pytest tests/test_matching.py::TestValidacaoDatas -v` | No — Wave 0 |
| XREF-04 | Atestado dates outside ART interval → DIVERGENTE | unit | `pytest tests/test_matching.py::TestValidacaoDatas::test_data_fora_intervalo -v` | No — Wave 0 |
| XREF-04 | Missing atestado dates → AUSENTE | unit | `pytest tests/test_matching.py::TestValidacaoDatas::test_datas_ausentes -v` | No — Wave 0 |
| XREF-05 | Contract number exact match | unit | `pytest tests/test_matching.py::TestMatchExato -v` | No — Wave 0 |
| XREF-06 | Escopo semântico similar → MATCH with confidence | unit | `pytest tests/test_matching.py::TestGPTCruzamento::test_escopo_similar -v` | No — Wave 0 |
| XREF-07 | "AR CLIMA" vs "HIDRO-CLIMA" → DIVERGENTE | unit | `pytest tests/test_matching.py::TestGPTCruzamento::test_empresa_divergente -v` | No — Wave 0 |
| XREF-07 | Par 2 integration: empresa DIVERGENTE detected | integration | `pytest tests/test_integration_phase5.py::test_par2_empresa_divergente -v -m integration` | No — Wave 0 |
| All | cruzar_documentos returns ResultadoCruzamento | unit | `pytest tests/test_matching.py::TestCruzarDocumentos -v` | No — Wave 0 |
| All | GPT fallback (output_parsed=None) returns empty result | unit | `pytest tests/test_matching.py::TestCruzarDocumentos::test_gpt_fallback -v` | No — Wave 0 |

### Mock Fixture Pattern (follow conftest.py convention)

The `mock_matching_client` fixture must be added to `tests/conftest.py` following the same pattern as `mock_analysis_client`. It should return a `ResultadoGPTCruzamento` with mocked field comparisons.

### Sampling Rate

- **Per task commit:** `pytest tests/test_matching.py -v`
- **Per wave merge:** `pytest tests/test_matching.py tests/test_integration_phase5.py -v -m "not integration"`
- **Phase gate:** Full suite green including `pytest tests/ -v -m "not integration"` before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_matching.py` — covers XREF-01 through XREF-07 (unit tests with mocked GPT)
- [ ] `tests/test_integration_phase5.py` — integration tests against real PDFs (Par 1 and Par 2)
- [ ] `mock_matching_client` fixture in `tests/conftest.py` — returns `ResultadoGPTCruzamento` with known field values

---

## Sources

### Primary (HIGH confidence)

- `crea_cat_ai/analysis.py` (project codebase) — Pydantic model patterns, normalizar_crea_rnp implementation, Responses API pattern, module-level client
- `crea_cat_ai/matching.py` (project codebase) — stub confirming nothing exists yet
- `config.py` (project codebase) — PESO_* constants, OPENAI_MODEL, all thresholds
- `main.py` (project codebase) — pipeline wiring pattern, integration point for Phase 5
- `tests/conftest.py` (project codebase) — mock fixture pattern for OpenAI client
- `tests/test_analysis.py` (project codebase) — test class structure, mock pattern, integration test pattern
- `pytest.ini` (project codebase) — `addopts = -m "not integration"` confirmed
- `.planning/phases/05-cross-document-matching/05-CONTEXT.md` — all locked decisions D-01 through D-11
- `.planning/STATE.md` — accumulated decisions, known blockers

### Secondary (MEDIUM confidence)

- OpenAI Responses API `responses.parse()` — confirmed working in Phases 2 and 3 (production code)
- Python `datetime.strptime` multi-format loop — standard Python pattern, confirmed works in Phase 4 `_parse_pdf_date`

### Tertiary (LOW confidence)

- None — all findings verified against project codebase

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and in production use in this project
- Architecture patterns: HIGH — directly derived from working Phase 3 code (analysis.py) and locked decisions
- Pitfalls: HIGH for known ones (D-11 divergence, date parsing) — based on Phase 4 lessons; MEDIUM for edge cases
- Test patterns: HIGH — directly from working test infrastructure in tests/

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable — no external moving parts; all decisions locked)
