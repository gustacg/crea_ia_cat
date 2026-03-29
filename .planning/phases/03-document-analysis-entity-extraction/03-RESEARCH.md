# Phase 3: Document Analysis & Entity Extraction - Research

**Researched:** 2026-03-28
**Domain:** OpenAI Responses API structured output + entity extraction from Brazilian engineering documents (CREA-MA)
**Confidence:** HIGH

---

## Summary

Phase 3 implements `crea_cat_ai/analysis.py`. It receives a `PacoteDocumentos` from Phase 2 (already loaded, pages as images + native text) and produces a fully-annotated set of entities for each document: CPF, CNPJ, CREA/RNP (treated as equivalent), names, organizations, dates, addresses, service scope, plus visual analysis (timbre/logo and signature with name/cargo/CREA-CPF), plus spell-check for Atestado, plus a determination of whether the signer is a qualified engineer.

All 5 test documents have been inspected for their actual entity content. The entity schemas are designed around what these documents actually contain. The critical ANAL-02 requirement (RNP = CREA equivalence) is a normalization/comparison concern: the ART uses the label "RNP" while the Atestado uses the label "CREA" for the same number — GPT must be told they are the same type of identifier, and the pipeline must store both under a single normalized field.

The core pattern is identical to Phase 2: `client.responses.parse(text_format=PydanticModel)` with `"detail": "high"` for visual analysis (timbre, signature) versus `"detail": "low"` for text-only extraction. The saude indigena.pdf Atestado has 32 pages — entity extraction requires only the first and last page (first page has contratante data, last page has signer). Processing all 32 pages for visual analysis would waste tokens and time; the plan must account for selective page targeting.

**Primary recommendation:** Implement `analisar_documento(doc: DocumentoCarregado) -> ResultadoAnalise` as the public API. Use one GPT call per document with `"detail": "high"` images of the relevant pages (first page always; last page for multi-page Atestados where signer appears at the end). Return a rich Pydantic model covering all ANAL-01 through ANAL-06 requirements.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

No CONTEXT.md exists for Phase 3. All technical decisions are delegated to Claude per project memory and CLAUDE.md.

### Locked Decisions (from CLAUDE.md and STATE.md)
- Motor IA: OpenAI GPT-4.1 com Vision (model string `"gpt-4.1"`, via `config.OPENAI_MODEL`)
- Stack: openai + pymupdf + pikepdf + pyHanko + Pillow — NO additional dependencies
- Import: always `import pymupdf` (never `import fitz`)
- Paths: `pathlib.Path` for all file operations
- Language: all log/output messages in Portuguese (pt-BR)
- OpenAI API key via `OPENAI_API_KEY` environment variable, read from `config.OPENAI_API_KEY`
- Structured output: Responses API with Pydantic `text_format=` (not `chat.completions`)
- Windows 11, local, no Docker, no external servers (except OpenAI API)
- GPT-4.1 Vision does OCR, NER, spell check, timbre/signature visual detection — no external NLP libraries
- ELA and visual copy/paste detection are DEFERRED to V1 — do NOT implement here
- RNP and CREA are equivalent identifiers — must be treated as such throughout

### Claude's Discretion
All technical implementation decisions: Pydantic schema design, prompt content, page selection strategy, number of GPT calls per document, function signatures, error handling, test structure, confidence thresholds.

### Deferred Ideas (OUT OF SCOPE)
- ELA (Error Level Analysis) — V1
- OpenCV copy/paste detection — V1
- Cross-document matching (Phase 5)
- Compliance checking (Phase 6)
- Verdict/scoring (Phase 7)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANAL-01 | GPT-4.1 Vision extrai entidades estruturadas: CPF, CNPJ, CREA, RNP, nomes, organizações, datas, endereços, escopo | Verified entity structure from all 5 test documents (see Ground Truth section). Pydantic schema designed around actual document fields. |
| ANAL-02 | Pipeline trata RNP e CREA como identificadores equivalentes na comparação | RNP is used in ART ("RNP: 1120893194"), CREA label used in Atestado ("Registro CREA: 1120893194"). Same number. Single normalized field `crea_rnp` stores both; GPT prompt explicitly states equivalence. |
| ANAL-03 | GPT-4.1 verifica ortografia do atestado (ignorando termos técnicos de engenharia) | GPT-4.1 spell-check via prompt: list errors with corrections, skip technical terms (siglas ABNT, nomes de equipamentos, termos do glossário de engenharia). Applied only to Atestado type. |
| ANAL-04 | GPT-4.1 Vision detecta presença de timbre/logo da contratante no atestado | `"detail": "high"` on first page image. Prompt asks for visual description of letterhead, logo, timbre. Boolean `tem_timbre` + `descricao_timbre`. |
| ANAL-05 | GPT-4.1 Vision detecta assinatura visual e extrai nome, cargo, CREA/CPF do assinante | Last page (or first if single-page). `"detail": "high"` image. Prompt asks for visual signature presence, name/cargo/CREA/CPF below the signature line. |
| ANAL-06 | Pipeline identifica quando assinante NÃO é engenheiro habilitado na área do serviço | Rule derived from cargo: "ADMINISTRADOR" → not an engineer → `engenheiro_habilitado: false`. "ENGENHEIRO CIVIL"/"ENGENHEIRO ELETRICISTA" → `engenheiro_habilitado: true`. GPT classifies; pipeline enforces downstream logic. |
</phase_requirements>

---

## Standard Stack

### Core (already installed — verified Phase 1/2)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| openai | 2.30.0 | Responses API with Vision + structured output | Motor principal — `client.responses.parse(text_format=PydanticModel)` |
| pydantic | 2.12.4 | Entity extraction schema definition | Transitive dep, already installed, required for `text_format=` |
| pymupdf | 1.27.2.2 | Access pages already loaded in Phase 2 | `PaginaDocumento.imagem_b64` already produced by ingestion.py |

### No additional dependencies needed
All required packages are already installed. Do NOT add anything to `requirements.txt`.

---

## Ground Truth: Entities in Test Documents

This section documents the actual entities verified from real document inspection. The planner MUST use these as the ground truth for test assertions.

### Par 1 — ART: MA20250929762

| Entity | Value |
|--------|-------|
| Número ART | MA20250929762 |
| Tipo ART | INICIAL |
| Responsável Técnico | ALEXANDRE DE MORAES BUENO NETO |
| Título profissional | ENGENHEIRO ELETRICISTA |
| RNP | 1120893194 |
| Registro | 1120893194MA |
| Contratante | TABOCA AGRO NEGOCIOS LTDA |
| CNPJ contratante | 36.408.654/0001-04 |
| Número do contrato | 0352015 |
| Data início | 12/05/2025 |
| Previsão término | 24/06/2025 |
| Endereço obra | FAZENDA FAZENDA PV CURRAL VELHO, S/N, CANTO BONITO, PASTOS BONS, MA, 65870000 |
| Escopo | Elaboração de projeto de sistema de iluminação (50 pontos), Fazenda PV Curral Velho |
| Proprietário | TABOCA AGRO NEGOCIOS LTDA |
| CPF/CNPJ proprietário | 36.408.654/0001-04 |
| Registrada em | 25/06/2025 |

### Par 1 — Atestado: 944678...ACT_Alexandre

| Entity | Value |
|--------|-------|
| Emitente | TABOCA AGRO NEGÓCIOS LTDA |
| CNPJ emitente | 36.408.654/0001-04 |
| Profissional atestado | ALEXANDRE DE MORAES BUENO NETO |
| Profissão | Engenheiro Eletricista |
| CREA do profissional | 1120893194 |
| Contrato | 0352015 |
| ART referenciada | MA20250929762 |
| Período | 12/05/2025 a 24/06/2025 |
| Local obra | Fazenda Pv. Curral Velho, Canto Bonito, Sn, Pastos Bons, MA |
| Escopo | Elaboração de projeto de sistema de iluminação contendo 50 pontos de iluminação, Fazenda PV Curral Velho, Pastos Bons, MA |
| Assinante nome | RUAN FERNANDES AZEVEDO DA NÓBREGA |
| Assinante cargo | ADMINISTRADOR |
| Assinante CPF | 620.456.233-94 |
| Assinante é engenheiro? | NÃO — cargo "ADMINISTRADOR" → `engenheiro_habilitado: false` |
| Assinatura digital | Sim (texto "Assinado de forma digital") |

**Critical for ANAL-06:** Par 1 Atestado is signed by an ADMINISTRADOR (Ruan), NOT by an engineer. This triggers the Declaração requirement downstream (Phase 6).

### Par 1 — Declaração: 944678...DECLARACAO

| Entity | Value |
|--------|-------|
| Tipo | Declaração Fiscal |
| Empresa auditada | J F EMPREENDIMENTOS LTDA |
| CNPJ empresa auditada | 26.575.201/0001-00 |
| Responsável técnico declarado | Rodolfo Pereira de Figueiredo |
| Título | Engenheiro Eletricista |
| CREA | MA 1015902979 |
| Contrato | 0352015 |
| ART do contrato | MA20250928588 (note: different from ART MA20250929762 in pair) |
| Período | 02/06/2025 a 23/06/2025 |
| Endereço | FAZ TABOCA NOVA POVOADO FEIRA DA VARZEA (truncated in text) |

### Par 2 — ART: MA20250957723

| Entity | Value |
|--------|-------|
| Número ART | MA20250957723 |
| Tipo ART | SUBSTITUIÇÃO de MA20250890316 |
| Responsável Técnico | NIZO GONZAGA DE SOUZA |
| Título | ENGENHEIRO CIVIL |
| RNP | 1004245351 |
| Registro | 147573MA |
| Empresa contratada | AR CLIMA SOLUÇÕES E SERVIÇOS LTDA |
| Registro empresa | 0005532400-MA |
| Contratante | DISTRITO SANITÁRIO ESPECIAL INDÍGENA DO MARANHÃO |
| CNPJ contratante | 00.394.544/0106-52 |
| Endereço contratante | RUA CINCO DE JANEIRO, 166, S/C, JORDOA, SÃO LUÍS, MA, 65040450 |
| Contrato | 14/2024 |
| Celebrado em | 30/10/2024 |
| Valor | R$ 818.582,00 |
| CPF assinante (ART) | ***.870.451-** (masked) |

### Par 2 — Atestado: saude indigena.pdf

| Entity | Value |
|--------|-------|
| Emitente | DISTRITO SANITÁRIO ESPECIAL INDÍGENA DO MARANHÃO (Ministério da Saúde) |
| CNPJ emitente | 00.394.544/0106-52 |
| Empresa executora | HIDRO-CLIMA Construções e Manutenções Ltda. (page 1) |
| CNPJ empresa executora | 17.306.559/0001-47 |
| Eng. responsável | Nizo Gonzaga de Souza |
| Título | Engenheiro Civil |
| CREA eng. | 4388D/GO (form: state-register notation, not MA) |
| CPF eng. | 148.870.451-15 |
| RG eng. | 186.807 SSP-GO |
| ART referenciada | MA 20250890316 |
| Período | 21/02/2025 a 19/12/2025 |
| Cidade | São Luís/MA |
| Data emissão | 09 de janeiro de 2026 |
| Assinante 1 nome | Daniel Farias de Albuquerque |
| Assinante 1 cargo | Engenheiro Civil de Saúde Indígena |
| Assinante 2 nome | Lúcio Dienio Silva Santos Guajajara |
| Assinante 2 cargo | Coordenador Distrital de Saúde Indígena |
| Assinante 2 CREA | CREA-MA n° 111029613-4 |
| Assinante é engenheiro? | SIM — "Engenheiro Civil de Saúde Indígena" (assinante 1 has engineering title) |

**Critical cross-reference alert:** ART says "AR CLIMA SOLUÇÕES E SERVIÇOS LTDA" but Atestado says "HIDRO-CLIMA Construções e Manutenções Ltda." — this is the known company name divergence (STATE.md blocker). Phase 3 must extract both; Phase 5 will detect the mismatch.

**Critical for saude indigena.pdf:** 32 pages. Relevant entity content is on page 1 (contratante, empresa executora, CNPJ) and page 32 (eng. responsável, CPF, CREA, signers, dates). Pages 2–31 are tabular scope/BDI content — do NOT send all 32 page images to GPT for entity extraction.

---

## Architecture Patterns

### Recommended Module Structure for analysis.py

```
analysis.py exposes:
  - analisar_documento(doc: DocumentoCarregado) -> ResultadoAnalise
  - analisar_pacote(pacote: PacoteDocumentos) -> dict[str, ResultadoAnalise]
```

`ResultadoAnalise` is the central Pydantic model — its schema determines everything downstream (Phase 5 matching, Phase 6 compliance).

### Pattern 1: Entity Extraction via Responses API (ANAL-01, ANAL-02)

The schema must normalize RNP and CREA to a single field. The field is called `crea_rnp` to signal equivalence. Both the `RNP: 1120893194` in the ART and `Registro CREA: 1120893194` in the Atestado must be stored here.

```python
# Source: verified against openai SDK 2.30.0 (same pattern as Phase 2 classification)
from pydantic import BaseModel, Field
from typing import Optional
from openai import OpenAI
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)

class EntidadesProfissional(BaseModel):
    nome: str                         # Full name of engineer/professional
    titulo: str                       # Professional title (e.g., "Engenheiro Eletricista")
    crea_rnp: Optional[str] = None    # CREA or RNP number — treated as equivalent
    cpf: Optional[str] = None         # CPF (may be masked with ***)
    registro: Optional[str] = None    # Full CREA registration string (e.g., "1120893194MA")

class EntidadesOrganizacao(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    cpf: Optional[str] = None         # For individual contractors

class EntidadesEndereco(BaseModel):
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None

class EntidadesData(BaseModel):
    data_inicio: Optional[str] = None    # ISO or DD/MM/YYYY
    data_termino: Optional[str] = None   # ISO or DD/MM/YYYY
    data_emissao: Optional[str] = None

class AssianteInfo(BaseModel):
    nome: str
    cargo: str                           # "ADMINISTRADOR", "ENGENHEIRO CIVIL", etc.
    crea_rnp: Optional[str] = None
    cpf: Optional[str] = None
    engenheiro_habilitado: bool          # True only if cargo is an engineering title

class AnaliseVisual(BaseModel):
    tem_timbre: bool
    descricao_timbre: Optional[str] = None  # Brief description of letterhead/logo
    tem_assinatura_visual: bool
    assinantes: list[AssianteInfo] = Field(default_factory=list)

class ErroOrtografico(BaseModel):
    trecho: str          # The incorrect text
    sugestao: str        # The suggested correction

class ResultadoAnalise(BaseModel):
    # Core entities (ANAL-01)
    numero_documento: Optional[str] = None  # ART number, or contract number
    profissional: Optional[EntidadesProfissional] = None
    contratante: Optional[EntidadesOrganizacao] = None
    empresa_executora: Optional[EntidadesOrganizacao] = None
    endereco_obra: Optional[EntidadesEndereco] = None
    datas: EntidadesData = Field(default_factory=EntidadesData)
    escopo: Optional[str] = None            # Free text description of scope
    contrato_numero: Optional[str] = None
    art_referenciada: Optional[str] = None  # ART number referenced in Atestado/Declaração
    valor_contrato: Optional[str] = None

    # Visual analysis (ANAL-04, ANAL-05, ANAL-06)
    visual: AnaliseVisual = Field(default_factory=lambda: AnaliseVisual(
        tem_timbre=False, tem_assinatura_visual=False
    ))

    # Spell check (ANAL-03) — only populated for Atestado
    erros_ortograficos: list[ErroOrtografico] = Field(default_factory=list)

    # Confidence
    confianca: float = 1.0
    observacoes: Optional[str] = None  # Any anomalies noted by GPT
```

### Pattern 2: Page Selection for Multi-Page Documents

The saude indigena.pdf has 32 pages. Only pages 1 and 32 are relevant. Always send:
- Page 1 image (always): header, contratante, empresa, escopo início
- Last page image (if multi-page Atestado): assinante, datas finais, CREA/CPF

```python
def _selecionar_paginas_analise(doc: DocumentoCarregado) -> list[PaginaDocumento]:
    """
    Seleciona as páginas relevantes para extração de entidades.
    - Documentos com 1 página: apenas página 1
    - ARTs com 2 páginas: ambas (dados técnicos na 2ª página)
    - Atestados longos: página 1 + última página (assinante está no final)
    - Máximo: 3 páginas por documento (evita spike de tokens)
    """
    paginas = doc.paginas
    if len(paginas) <= 3:
        return paginas  # Send all pages when 3 or fewer
    # For long docs: first page + last page
    return [paginas[0], paginas[-1]]
```

### Pattern 3: Single GPT Call Per Document with Combined Analysis

One call handles all 6 requirements: entity extraction + spell check + visual analysis. This is more cost-efficient than separate calls per task.

```python
PROMPT_ANALISE_BASE = """Você é um especialista em análise de documentos técnicos do CREA (Conselho Regional de Engenharia e Agronomia do Brasil).

Analise o documento e extraia TODAS as informações estruturadas a seguir.

REGRA CRÍTICA — RNP e CREA são EQUIVALENTES:
- No formulário da ART, o número do registro profissional aparece com o rótulo "RNP:"
- Em atestados e declarações, o mesmo número aparece como "CREA:" ou "Registro CREA:"
- São o MESMO identificador. Sempre preencha o campo `crea_rnp` com este número.

EXTRAÇÃO DE ENTIDADES (campos obrigatórios se presentes no documento):
- profissional: nome completo, título profissional, número CREA/RNP, CPF (pode estar mascarado como ***), registro completo
- contratante: nome da empresa/órgão, CNPJ ou CPF
- empresa_executora: empresa que prestou o serviço (pode ser diferente da contratante)
- endereco_obra: endereço onde o serviço foi executado (logradouro, número, bairro, cidade, UF, CEP)
- datas: data de início, data de término/previsão, data de emissão do documento
- escopo: descrição do serviço/obra executado (texto livre, resumido em até 200 caracteres)
- contrato_numero: número do contrato
- art_referenciada: número da ART citada no documento (se for Atestado ou Declaração)
- valor_contrato: valor em R$

ANÁLISE VISUAL (examinar as imagens):
- tem_timbre: True se há logomarca, timbre ou papel timbrado identificável da contratante
- descricao_timbre: descrição breve do timbre/logo se presente
- tem_assinatura_visual: True se há assinatura manuscrita ou digital visível
- assinantes: lista de assinantes identificados. Para cada assinante:
  * nome: nome completo
  * cargo: cargo exato conforme aparece no documento (ex: "ADMINISTRADOR", "Engenheiro Civil de Saúde Indígena")
  * crea_rnp: número CREA ou RNP se presente abaixo da assinatura
  * cpf: CPF se presente
  * engenheiro_habilitado: true SOMENTE se o cargo for explicitamente um título de engenheiro, arquiteto, agrônomo ou similar. "ADMINISTRADOR", "Coordenador", "Diretor", etc. = false.

VERIFICAÇÃO ORTOGRÁFICA (apenas para Atestados):
- Identifique erros ortográficos em português — erros de digitação, acentuação incorreta, concordância verbal/nominal
- IGNORE: siglas técnicas (ART, CREA, RNP, ABNT, NBR), nomes próprios, endereços, termos técnicos de engenharia (ex: "fcK", "CA-50", "CHP"), nomes de equipamentos
- Para cada erro encontrado: informe o trecho incorreto e a sugestão correta
"""
```

### Pattern 4: Building the GPT Request

```python
def _construir_input_analise(
    doc: DocumentoCarregado,
    paginas: list[PaginaDocumento]
) -> list[dict]:
    """Constrói o input da Responses API para análise de entidades."""

    # Native text from selected pages (faster/cheaper than pure Vision)
    texto_combinado = "\n\n---\n\n".join(
        f"[Página {p.numero}]\n{p.texto_nativo}"
        for p in paginas
        if p.texto_nativo.strip()
    )

    content = []

    # Text content (priority: native text when available)
    if texto_combinado.strip():
        content.append({
            "type": "input_text",
            "text": f"Tipo de documento: {doc.tipo.value}\n\nTexto extraído:\n{texto_combinado[:6000]}"
        })

    # Images — "high" detail for visual analysis (timbre, signature)
    for pagina in paginas:
        content.append({
            "type": "input_image",
            "image_url": f"data:image/png;base64,{pagina.imagem_b64}",
            "detail": "high"  # Required for timbre/signature detection (ANAL-04, ANAL-05)
        })

    return [{"role": "user", "content": content}]
```

### Pattern 5: The Main Analysis Function

```python
def analisar_documento(doc: DocumentoCarregado) -> ResultadoAnalise:
    """
    Extrai entidades estruturadas, analisa visualmente e verifica ortografia.
    Ponto de entrada principal do Phase 3.
    """
    paginas = _selecionar_paginas_analise(doc)
    input_content = _construir_input_analise(doc, paginas)

    response = client.responses.parse(
        model=config.OPENAI_MODEL,
        instructions=PROMPT_ANALISE_BASE,
        input=input_content,
        text_format=ResultadoAnalise,
    )

    if response.output_parsed is None:
        return ResultadoAnalise(confianca=0.0, observacoes="Modelo recusou análise")

    return response.output_parsed


def analisar_pacote(pacote: PacoteDocumentos) -> dict[str, ResultadoAnalise]:
    """
    Analisa todos os documentos do pacote.
    Retorna dict com chave = tipo_documento (ex: "ART", "Atestado").
    """
    resultados = {}

    documentos = []
    if pacote.art:
        documentos.append(pacote.art)
    if pacote.atestado:
        documentos.append(pacote.atestado)
    documentos.extend(pacote.complementares)

    for doc in documentos:
        print(f"  Analisando: {doc.caminho.name} ({doc.tipo.value})")
        resultado = analisar_documento(doc)
        resultados[doc.tipo.value] = resultado
        print(f"    Profissional: {resultado.profissional.nome if resultado.profissional else 'N/A'}")

    return resultados
```

### Pattern 6: CREA/RNP Normalization (ANAL-02)

The comparison between ART and Atestado requires normalization. This helper should live in `analysis.py`:

```python
def normalizar_crea_rnp(valor: str | None) -> str | None:
    """
    Normaliza identificador CREA/RNP para comparação.
    Remove sufixos de UF (ex: '1120893194MA' → '1120893194').
    Remove prefixos de UF e barras (ex: 'CREA MA 1015902979' → '1015902979').
    Remove formatação com pontos/hífens/espaços.
    """
    if valor is None:
        return None
    import re
    # Remove non-digit characters, keep only the numeric sequence
    digits = re.sub(r'\D', '', valor)
    return digits if digits else None
```

**Key insight:** ART has `RNP: 1120893194` and `Registro: 1120893194MA`. Atestado has `Registro CREA: 1120893194`. After normalization: both → `"1120893194"`. The Declaração has `CREA MA 1015902979` → `"1015902979"`.

### Anti-Patterns to Avoid

- **`"detail": "low"` for visual analysis**: ANAL-04 (timbre) and ANAL-05 (signature with text) require `"detail": "high"`. Low detail compresses the image too much to read handwritten/stamped text near signatures.
- **Sending all 32 pages of saude indigena.pdf**: This wastes ~32× the image tokens. Only pages 1 and last contain entity-relevant content.
- **Separate GPT calls for text vs visual**: Combined in one call per document — entities + visual + spell-check together. Reduces cost, maintains context coherence.
- **Assuming the signer's CPF is complete**: In ARTs, CPF is masked (`***.983.483-**`). Store what's available; do not error on masked CPFs.
- **Treating "CREA MA 1015902979" as not matching "1015902979"**: The normalization function must strip UF prefixes and non-numeric characters before comparison.
- **Hardcoding document type checks for spell-check**: Use `doc.tipo == TipoDocumento.ATESTADO` — not string comparison — to decide whether to request spell-check.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CREA/RNP entity recognition | Regex patterns for CREA numbers | GPT-4.1 extraction + `normalizar_crea_rnp()` normalization | CREA formats vary: "1120893194", "1120893194MA", "CREA MA 1015902979", "4388D/GO", "147573MA" |
| Spell-check in Portuguese | LanguageTool / external service | GPT-4.1 spell check via prompt | Already in stack; GPT handles domain terms (avoids false positives on engineering vocabulary) |
| Signature region detection | OpenCV contour detection | GPT-4.1 Vision with `"detail": "high"` | OpenCV deferred to V1; GPT Vision is sufficient for MVP |
| Engineer qualification detection | Hardcoded cargo lists | GPT-4.1 `engenheiro_habilitado` field in Pydantic schema | Cargo variants too numerous to enumerate; GPT handles "Engenheiro de Saúde Indígena", "Coordenador Distrital", etc. |
| OCR of scanned text near signature | Tesseract | GPT-4.1 Vision | Same pattern as classification — no binary deps |

---

## Common Pitfalls

### Pitfall 1: `"detail": "low"` misses signature text
**What goes wrong:** With `"detail": "low"`, GPT Vision downsamples the image significantly. Handwritten signatures and small printed text below signatures (name, CREA, CPF) become unreadable.
**Why it happens:** Phase 2 used `"detail": "low"` for classification — that was correct for identifying document type. For reading fine text near signatures, `"detail": "high"` is required.
**How to avoid:** Always use `"detail": "high"` in analysis.py. The cost increase is acceptable for 5 test documents.
**Warning signs:** `tem_assinatura_visual: false` for the Atestado Par 1 (which clearly has a digital signature block), or `assinantes: []` for the saude indigena.pdf.

### Pitfall 2: saude indigena.pdf token spike
**What goes wrong:** Sending all 32 pages as images = ~32 × (high-detail image cost) = excessive token usage and potential timeout.
**Why it happens:** `doc.paginas` has 32 items; iterating naively sends all 32.
**How to avoid:** Use `_selecionar_paginas_analise()` which sends page 1 + last page for documents > 3 pages.
**Warning signs:** API call taking >30 seconds, token count > 50K for a single analysis call.

### Pitfall 3: Masked CPF fields causing validation errors
**What goes wrong:** ARTs contain masked CPFs like `***.983.483-**`. If the Pydantic schema enforces CPF format (e.g., 11 digits), it will fail.
**Why it happens:** CREA masks CPFs in ART printouts for privacy.
**How to avoid:** All CPF/CNPJ fields use `Optional[str] = None` — no format validation in the schema. Raw string as-is from document.
**Warning signs:** `ValidationError: value is not a valid...` when parsing ART documents.

### Pitfall 4: Single `assinantes` field vs multiple signers
**What goes wrong:** saude indigena.pdf has TWO signers (Daniel Farias + Lúcio Dienio). If schema uses a single `assinante: AssinanteInfo` field, one signer is dropped.
**Why it happens:** Assuming all Atestados have a single signer.
**How to avoid:** `assinantes: list[AssinanteInfo]` — always a list. Phase 6 (compliance) picks the relevant signer.
**Warning signs:** Only one signer extracted for saude indigena.pdf.

### Pitfall 5: "CREA 4388D/GO" not recognized as same type as "RNP: 1120893194"
**What goes wrong:** The Atestado saude indigena.pdf has `CREA 4388D/GO` for Nizo Gonzaga — this is a Goiás-registered engineer. `normalizar_crea_rnp("4388D/GO")` → `"4388"` (only digits). This won't match the RNP `1004245351` in the ART.
**Why it happens:** The ART RNP is the federal RNP number; the Atestado CREA is the state registration number. These CAN be different valid representations.
**How to avoid:** Store both raw and normalized values. The cross-matching in Phase 5 should note this divergence as a warning, not a hard mismatch — the name match (Nizo Gonzaga de Souza) provides additional confirmation.
**Warning signs:** Phase 5 reporting false DIVERGENTE on Par 2 CREA/RNP despite same professional.

### Pitfall 6: Spell-check false positives on engineering terms
**What goes wrong:** GPT flags "fcK=20MPA", "CA-50", "SESANI", "DSEI" as spelling errors.
**Why it happens:** These are engineering notation and acronyms, not Portuguese words.
**How to avoid:** Explicit exclusion list in the prompt: "IGNORE siglas, nomes próprios, termos técnicos (normas ABNT, especificações de materiais, nomes de equipamentos, designações de obra)".
**Warning signs:** `erros_ortograficos` list with 10+ items for the saude indigena.pdf scope tables.

### Pitfall 7: Responses API `output_parsed` is None on complex schemas
**What goes wrong:** With a deeply nested Pydantic schema, GPT occasionally fails to produce valid JSON, causing `output_parsed = None`.
**Why it happens:** Complex nested schemas increase the chance of JSON generation errors even with structured output.
**How to avoid:** Keep the schema flat where possible. Use `Optional[str]` for leaf fields rather than nested validation. Always check `if response.output_parsed is None` and return a fallback `ResultadoAnalise`.
**Warning signs:** `output_parsed` is None for some documents but not others.

---

## Code Examples

### Full call pattern (verified Responses API pattern from Phase 2)

```python
# Source: same pattern as crea_cat_ai/ingestion.py — verified openai 2.30.0
response = client.responses.parse(
    model=config.OPENAI_MODEL,
    instructions=PROMPT_ANALISE_BASE,
    input=[{
        "role": "user",
        "content": [
            {
                "type": "input_text",
                "text": f"Tipo: {doc.tipo.value}\n\nTexto:\n{texto[:6000]}"
            },
            {
                "type": "input_image",
                "image_url": f"data:image/png;base64,{pagina.imagem_b64}",
                "detail": "high"  # MUST be high for signature/timbre reading
            }
        ]
    }],
    text_format=ResultadoAnalise,
)

if response.output_parsed is None:
    return ResultadoAnalise(confianca=0.0, observacoes="Modelo recusou análise")

return response.output_parsed
```

### CREA/RNP Normalization

```python
import re

def normalizar_crea_rnp(valor: str | None) -> str | None:
    """Remove non-digit chars for numeric comparison. Returns None if input is None."""
    if valor is None:
        return None
    digits = re.sub(r'\D', '', valor)
    return digits if digits else None

# Test cases from real documents:
assert normalizar_crea_rnp("1120893194") == "1120893194"      # ART RNP
assert normalizar_crea_rnp("1120893194MA") == "1120893194"    # ART Registro
assert normalizar_crea_rnp("CREA MA 1015902979") == "1015902979"  # Declaracao
assert normalizar_crea_rnp("4388D/GO") == "4388"              # State reg (Goiás)
assert normalizar_crea_rnp(None) is None
```

### Engineer qualification logic

```python
_TITULOS_ENGENHEIRO = {
    "engenheiro", "engineer", "arquiteto", "agrônomo", "agronomist",
    "geólogo", "geógrafo", "meteorologista"
}

def _classificar_engenheiro(cargo: str) -> bool:
    """
    Classifica se um cargo é de profissional habilitado de engenharia.
    GPT já faz isso via engenheiro_habilitado no schema — esta função
    serve como fallback/override para casos edge.
    """
    cargo_lower = cargo.lower()
    return any(titulo in cargo_lower for titulo in _TITULOS_ENGENHEIRO)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| spaCy NER for entity extraction | GPT-4.1 Vision with Pydantic schema | Stack pivot 2026-03-28 | No training required, handles CREA-specific terminology |
| Tesseract OCR for scanned docs | GPT-4.1 Vision `"detail": "high"` | Stack pivot 2026-03-28 | No binary deps, multilingual |
| LanguageTool (Java) spell check | GPT-4.1 prompt-based spell check | Stack pivot 2026-03-28 | Eliminates Java JRE dependency |
| `beta.chat.completions.parse()` | `responses.parse()` | openai SDK 2.x | Responses API is current convention per CLAUDE.md |

**Deprecated/outdated:**
- `import fitz`: CLAUDE.md requires `import pymupdf` — never use `fitz`.

---

## Runtime State Inventory

Step 2.5 SKIPPED — this is a greenfield implementation phase, not a rename/refactor/migration.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| openai Python SDK | All analysis calls | Yes | 2.30.0 | — |
| pydantic | `responses.parse(text_format=...)` | Yes | 2.12.4 | — |
| pymupdf | Page access via PaginaDocumento | Yes | 1.27.2.2 | — |
| pytest | Test execution | Yes | 9.0.2 | — |
| OPENAI_API_KEY | Live API calls | Unknown | — | Mock in unit tests; `@pytest.mark.integration` for live tests |
| Input PDFs | Ground truth tests | Yes | 5 files verified | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:**
- OPENAI_API_KEY: Must mock in unit tests. Integration tests skip when key absent (established pattern from Phase 2).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pytest.ini` (exists — integration marker defined) |
| Quick run command | `python -m pytest tests/test_analysis.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANAL-01 | `analisar_documento()` returns `ResultadoAnalise` with all entity fields populated | unit (mock) | `python -m pytest tests/test_analysis.py::test_extrai_entidades_art -x` | No — Wave 0 |
| ANAL-01 | CNPJ/CPF extracted correctly from real ART | integration | `python -m pytest tests/test_analysis.py::test_analise_art_real -x -m integration` | No — Wave 0 |
| ANAL-02 | `normalizar_crea_rnp()` normalizes "RNP: 1120893194" and "Registro CREA: 1120893194" to same value | unit | `python -m pytest tests/test_analysis.py::test_normalizar_crea_rnp -x` | No — Wave 0 |
| ANAL-03 | Spell check returns empty list for ART (technical doc — not spell-checked) | unit (mock) | `python -m pytest tests/test_analysis.py::test_ortografia_art_vazia -x` | No — Wave 0 |
| ANAL-04 | `visual.tem_timbre` is True for saude indigena.pdf (Ministry of Health letterhead) | integration | `python -m pytest tests/test_analysis.py::test_timbre_saude_indigena -x -m integration` | No — Wave 0 |
| ANAL-05 | `visual.assinantes` contains "RUAN FERNANDES" with cargo "ADMINISTRADOR" for Par 1 Atestado | integration | `python -m pytest tests/test_analysis.py::test_assinante_ruan -x -m integration` | No — Wave 0 |
| ANAL-06 | `engenheiro_habilitado: false` when cargo is "ADMINISTRADOR" | unit | `python -m pytest tests/test_analysis.py::test_nao_engenheiro -x` | No — Wave 0 |
| ANAL-06 | `engenheiro_habilitado: true` when cargo is "Engenheiro Civil de Saúde Indígena" | unit | `python -m pytest tests/test_analysis.py::test_engenheiro_habilitado -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_analysis.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_analysis.py` — covers ANAL-01 through ANAL-06
- [ ] `tests/conftest.py` — add `mock_analysis_client` fixture (same pattern as `mock_openai_client` in Phase 2, targeting `crea_cat_ai.analysis.client`)

*(No framework install needed — pytest 9.0.2 and pytest.ini already configured)*

---

## Open Questions

1. **CREA 4388D/GO vs RNP 1004245351 — same professional, different numbers**
   - What we know: ART for Par 2 has `RNP: 1004245351`. The Atestado saude indigena.pdf has `CREA 4388D/GO` for Nizo Gonzaga de Souza (same name, different number format).
   - What's unclear: Is 4388D/GO the Goiás state CREA and 1004245351 the federal RNP? Can the pipeline treat these as matching?
   - Recommendation: Phase 3 must store both raw values. Phase 5 (matching) should flag this as a warning (not hard mismatch) when names match but CREA/RNP numbers don't normalize to the same value. This is a known limitation, not a bug.

2. **Spell-check threshold for Atestados**
   - What we know: GPT will return a list of spelling errors. No threshold is defined for when errors become a signal.
   - What's unclear: Should `erros_ortograficos` with 2 errors vs 10 errors produce different verdicts?
   - Recommendation: Phase 3 just extracts and stores the list. Phase 7 (verdict/scoring) applies `config.PESO_ORTOGRAFIA` to compute impact on score. Phase 3 has no opinion on threshold.

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 3 |
|-----------|-------------------|
| `import pymupdf` (never `import fitz`) | No PyMuPDF imports needed in analysis.py (pages already loaded) — but if needed, use correct import |
| `OPENAI_API_KEY` via env var | Read from `config.OPENAI_API_KEY` |
| Model: `gpt-4.1` | Use `config.OPENAI_MODEL` |
| Responses API with structured output | `client.responses.parse(text_format=ResultadoAnalise)` |
| `pathlib.Path` for all paths | Paths inherited from Phase 2 `DocumentoCarregado.caminho` |
| Messages in pt-BR | All `print()` statements in Portuguese |
| No new dependencies | Do not add to `requirements.txt` |
| Windows 11, no Docker | No Unix-only assumptions |
| GPT-4.1 does spell check | No LanguageTool, no external spell check service |
| GPT-4.1 Vision detects timbre/signature | No OpenCV, no custom image processing |

---

## Sources

### Primary (HIGH confidence)
- Verified by directly reading all 5 test documents with `pymupdf` — entity ground truth tables are from actual document content
- openai SDK 2.30.0 — `responses.parse()` pattern verified working in Phase 2 (`ingestion.py` in production)
- Verified page counts: 5 docs confirmed (1, 1, 1, 2, 32 pages respectively)

### Secondary (MEDIUM confidence)
- OpenAI Vision documentation: `"detail": "high"` vs `"detail": "low"` — high detail preserves fine text near signatures
- CLAUDE.md explicit: GPT-4.1 Vision handles timbre/signature/spell-check, eliminating OpenCV/LanguageTool

### Tertiary (LOW confidence)
- None — all critical claims verified from installed SDK and real documents.

---

## Metadata

**Confidence breakdown:**
- Entity schema design: HIGH — designed from actual document field inspection, not hypothetical
- GPT call pattern: HIGH — identical to working Phase 2 pattern (responses.parse + Pydantic)
- Page selection strategy: HIGH — confirmed 32-page doc, first/last page strategy directly verified
- Prompt content: MEDIUM — prompt design is untested against real API; needs integration test to validate all 6 fields populated correctly
- CREA 4388D/GO issue: LOW — state vs federal registration number ambiguity, needs domain expert clarification

**Research date:** 2026-03-28
**Valid until:** 2026-06-28 (stable APIs — openai SDK and GPT-4.1 model behavior changes slowly for structured output)
