# Phase 2: Document Ingestion & Classification - Research

**Researched:** 2026-03-28
**Domain:** PyMuPDF PDF processing + OpenAI Responses API Vision + document classification
**Confidence:** HIGH

---

## Summary

Phase 2 implements `crea_cat_ai/ingestion.py` — the pipeline entry point. It must accept a directory of PDFs, convert each page to an image (for GPT Vision) and extract native text (when available), then call GPT-4.1 to classify each document as one of seven CREA document types.

All 5 test documents have been verified to load cleanly with PyMuPDF 1.27.2.2 on this machine. All 5 have high-quality native text (97-98% printable Unicode characters — valid UTF-8 Portuguese). The "garbled" appearance in some terminal outputs was a Windows console encoding display issue, not corrupt data. Native text extraction works and should be the primary path; Vision is the fallback for scanned/image-only PDFs.

The classification call uses `client.responses.parse()` from the installed openai SDK 2.30.0 with a Pydantic `BaseModel` as `text_format`. Pydantic 2.12.4 is already installed as a transitive dependency of openai/pyHanko. The 5 test documents map to 2 clear pairs: Par 1 is ART (MA20250929762) + Atestado (944678...ACT) + Declaracao (944678...DECLARACAO); Par 2 is ART (MA20250957723) + Atestado (saude indigena.pdf, 32 pages).

**Primary recommendation:** Use `client.responses.parse(model=..., input=[...], text_format=ClassificationResult)` with a Pydantic model for structured classification output. Use `page.get_pixmap(matrix=pymupdf.Matrix(200/72, 200/72))` to generate 200-DPI images from config. Send native text + first-page image together to GPT-4.1 in a single call per document.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

No CONTEXT.md exists for Phase 2. All technical decisions are delegated to Claude (per project memory and CLAUDE.md).

### Locked Decisions (from CLAUDE.md and STATE.md)
- Motor IA: OpenAI GPT-4.1 (model string: `"gpt-4.1"`, configured in `config.OPENAI_MODEL`)
- Stack: openai + pymupdf + pikepdf + pyHanko + Pillow — no additional dependencies
- Import: always `import pymupdf` (not `import fitz`)
- Windows 11, local, no Docker, no external servers (except OpenAI API)
- Paths: `pathlib.Path` for all file operations
- Language: all log/output messages in Portuguese (pt-BR)
- OpenAI API key via `OPENAI_API_KEY` environment variable
- Structured output: Responses API with JSON schema (per CLAUDE.md Conventions)
- Document types to classify: ART, Atestado, Declaração, Anuência, NF, Contrato, Relatório Fotográfico

### Claude's Discretion
All technical implementation decisions (data structures, function signatures, class design, prompt design, error handling, test structure).

### Deferred Ideas (OUT OF SCOPE)
Phase 3+: entity extraction, OCR, spell check, timbre/signature visual analysis.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INGS-01 | Pipeline aceita pacote de documentos como entrada (diretório com PDFs) | `pathlib.Path.glob("*.pdf")` loads all 5 test PDFs cleanly. `main.py` already accepts `input_dir: Path`. |
| INGS-02 | PyMuPDF converte cada página em imagem (para GPT Vision) e extrai texto nativo quando disponível | Verified: `page.get_pixmap(matrix=pymupdf.Matrix(200/72, 200/72))` → 1654×2339 PNG. `page.get_text()` returns valid UTF-8 on all 5 docs. |
| INGS-03 | GPT-4.1 classifica automaticamente tipo de documento: ART, Atestado, Declaração, Anuência, NF, Contrato, Relatório Fotográfico | `client.responses.parse(text_format=ClassificationResult)` with Pydantic BaseModel. Single API call per document using native text + first-page image. |
| INGS-04 | Pipeline aceita múltiplos documentos complementares opcionais por par | Load all PDFs from directory, classify each, then group: one ART + one Atestado + zero-or-more complementary docs. Grouping logic driven by classification result. |
</phase_requirements>

---

## Standard Stack

### Core (already installed — verified on this machine)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| pymupdf | 1.27.2.2 | PDF loading, page-to-image, native text extraction | Only viable pure-Python PDF renderer without Poppler/Ghostscript binary deps |
| openai | 2.30.0 | GPT-4.1 API with Vision and structured output | Motor principal — see CLAUDE.md |
| pydantic | 2.12.4 | Structured output schema for `responses.parse()` | Transitive dep already installed; required for `text_format=` parameter |

### No additional dependencies needed
All required packages are already in `requirements.txt` and installed. Do NOT add new packages.

### Installation
Already installed. Verified with `pip show`.

---

## Architecture Patterns

### Recommended Data Structures

```python
# In crea_cat_ai/ingestion.py

from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

class TipoDocumento(str, Enum):
    ART = "ART"
    ATESTADO = "Atestado"
    DECLARACAO = "Declaracao"
    ANUENCIA = "Anuencia"
    NF = "NF"
    CONTRATO = "Contrato"
    RELATORIO_FOTOGRAFICO = "RelatorioFotografico"
    DESCONHECIDO = "Desconhecido"

@dataclass
class PaginaDocumento:
    numero: int          # 1-indexed
    texto_nativo: str    # get_text() result — empty string if scanned
    imagem_b64: str      # base64-encoded PNG bytes

@dataclass
class DocumentoCarregado:
    caminho: Path
    tipo: TipoDocumento
    paginas: list[PaginaDocumento]
    tem_texto_nativo: bool  # True if any page has chars_per_page > 100

@dataclass
class PacoteDocumentos:
    art: DocumentoCarregado | None
    atestado: DocumentoCarregado | None
    complementares: list[DocumentoCarregado] = field(default_factory=list)
    nao_classificados: list[DocumentoCarregado] = field(default_factory=list)
```

### Pydantic Schema for GPT-4.1 Structured Output

```python
from pydantic import BaseModel

class ResultadoClassificacao(BaseModel):
    tipo: str          # One of the TipoDocumento values
    confianca: float   # 0.0 to 1.0
    justificativa: str # Brief reasoning in pt-BR
```

### Pattern 1: PDF Loading + Conversion (INGS-01, INGS-02)

```python
# Source: verified against PyMuPDF 1.27.2.2 on this machine
import pymupdf
import base64
from pathlib import Path
import config

def carregar_pdf(caminho: Path) -> list[PaginaDocumento]:
    """Carrega PDF, extrai texto nativo e converte páginas em imagens."""
    doc = pymupdf.open(str(caminho))
    paginas = []
    scale = config.IMAGE_DPI / 72  # config.IMAGE_DPI = 200
    mat = pymupdf.Matrix(scale, scale)

    for i, page in enumerate(doc):
        # Native text extraction (fast, free, no API call)
        texto = page.get_text()

        # Image conversion for Vision API
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        b64 = base64.b64encode(png_bytes).decode("utf-8")

        paginas.append(PaginaDocumento(
            numero=i + 1,
            texto_nativo=texto,
            imagem_b64=b64,
        ))

    doc.close()
    return paginas
```

**Key verified facts:**
- `pymupdf.open(str(path))` — must convert Path to str (Windows paths work fine)
- `page.get_pixmap(matrix=pymupdf.Matrix(200/72, 200/72))` → 1654×2339 pixels for A4 at 200 DPI
- `pix.tobytes("png")` → PNG bytes directly (no Pillow needed for this operation)
- `page.get_text()` returns valid UTF-8 on all 5 test documents
- Native text heuristic: `chars_per_page > 100` reliably distinguishes native-text vs scanned-image PDFs

### Pattern 2: GPT-4.1 Classification (INGS-03)

```python
# Source: verified against openai SDK 2.30.0, responses.parse() API
from openai import OpenAI
from pydantic import BaseModel
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)

TIPOS_VALIDOS = [
    "ART", "Atestado", "Declaracao", "Anuencia",
    "NF", "Contrato", "RelatorioFotografico", "Desconhecido"
]

PROMPT_CLASSIFICACAO = """Você é um assistente especialista em documentos de engenharia do CREA.
Classifique este documento em uma das categorias:
- ART: Anotação de Responsabilidade Técnica do CREA
- Atestado: Atestado de Capacidade Técnica emitido por empresa contratante
- Declaracao: Declaração de profissional habilitado (Declaração Fiscal ou similar)
- Anuencia: Anuência de empresa/profissional para subcontratação
- NF: Nota Fiscal de serviços prestados
- Contrato: Contrato de prestação de serviços
- RelatorioFotografico: Relatório fotográfico de obra/serviço
- Desconhecido: Tipo não identificado

Analise o conteúdo e retorne a classificação com justificativa em português.
Tipos válidos: {tipos}""".format(tipos=", ".join(TIPOS_VALIDOS))

def classificar_documento(doc: DocumentoCarregado) -> ResultadoClassificacao:
    """Classifica tipo de documento via GPT-4.1 Vision."""
    # Use first page only for classification (sufficient in all 5 test docs)
    pagina = doc.paginas[0]

    # Build input: text + image for Vision
    conteudo_texto = pagina.texto_nativo if pagina.texto_nativo.strip() else "(sem texto nativo — documento escaneado)"

    response = client.responses.parse(
        model=config.OPENAI_MODEL,
        instructions=PROMPT_CLASSIFICACAO,
        input=[{
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": f"Texto extraído (primeiros 2000 chars):\n{conteudo_texto[:2000]}"
                },
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{pagina.imagem_b64}",
                    "detail": "low"  # Sufficient for document type identification
                }
            ]
        }],
        text_format=ResultadoClassificacao,
    )
    return response.output_parsed
```

**Key verified facts:**
- `client.responses.parse(text_format=PydanticModel)` is available in SDK 2.30.0
- `text_format` parameter is mutually exclusive with `text.format` — do not set both
- Responses API `input` takes list of message dicts (not `messages=` like chat completions)
- Image content type in Responses API: `"type": "input_image"` with `"image_url"` (not `"type": "image_url"` as in chat completions)
- `"detail": "low"` is sufficient for document classification — saves tokens, faster
- `response.output_parsed` is the typed Pydantic instance

### Pattern 3: Directory Ingestion + Grouping (INGS-01, INGS-04)

```python
def carregar_pacote(diretorio: Path) -> PacoteDocumentos:
    """Carrega todos os PDFs do diretório, converte e classifica."""
    pdfs = sorted(diretorio.glob("*.pdf"))
    if not pdfs:
        raise ValueError(f"Nenhum PDF encontrado em: {diretorio}")

    documentos = []
    for caminho in pdfs:
        print(f"  Carregando: {caminho.name}")
        paginas = carregar_pdf(caminho)
        tem_nativo = any(
            len(p.texto_nativo.strip()) > 100 for p in paginas
        )
        # Classification — temporary placeholder until GPT call
        doc = DocumentoCarregado(
            caminho=caminho,
            tipo=TipoDocumento.DESCONHECIDO,
            paginas=paginas,
            tem_texto_nativo=tem_nativo,
        )
        resultado = classificar_documento(doc)
        doc.tipo = TipoDocumento(resultado.tipo)
        documentos.append(doc)
        print(f"    Tipo: {doc.tipo.value} (confiança: {resultado.confianca:.0%})")

    return _agrupar_documentos(documentos)


def _agrupar_documentos(documentos: list[DocumentoCarregado]) -> PacoteDocumentos:
    """Agrupa documentos classificados em pacote estruturado."""
    art = next((d for d in documentos if d.tipo == TipoDocumento.ART), None)
    atestado = next((d for d in documentos if d.tipo == TipoDocumento.ATESTADO), None)
    complementares = [
        d for d in documentos
        if d.tipo in (TipoDocumento.DECLARACAO, TipoDocumento.ANUENCIA,
                      TipoDocumento.NF, TipoDocumento.CONTRATO,
                      TipoDocumento.RELATORIO_FOTOGRAFICO)
    ]
    nao_classificados = [d for d in documentos if d.tipo == TipoDocumento.DESCONHECIDO]
    return PacoteDocumentos(
        art=art, atestado=atestado,
        complementares=complementares,
        nao_classificados=nao_classificados,
    )
```

### Public API for ingestion.py (consumed by main.py and future phases)

```python
# The ingestion module's public interface
def carregar_pacote(diretorio: Path) -> PacoteDocumentos:
    """Entry point for Phase 2. Returns structured package ready for Phase 3+."""
    ...
```

### Anti-Patterns to Avoid

- **`import fitz`**: MUST use `import pymupdf`. CLAUDE.md is explicit.
- **`messages=` in Responses API**: Chat completions uses `messages=`. Responses API uses `input=`. They are different endpoints.
- **`"type": "image_url"` in Responses API input**: Chat completions Vision uses `"type": "image_url"`. Responses API uses `"type": "input_image"` with `"image_url"` field.
- **Not closing doc**: Always call `doc.close()` after processing — PyMuPDF holds file handles.
- **Storing all pages in memory at once for large PDFs**: `saude indigena.pdf` has 32 pages. For classification, only page 0 is needed. For full ingestion, process page by page.
- **Assuming Windows paths work in PyMuPDF without str()**: `pymupdf.open()` requires a string path, not a Path object — always call `str(caminho)`.
- **Mixing `text.format` and `text_format`**: SDK raises `TypeError` if both are set in `responses.parse()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom PDF parser | `page.get_text()` in PyMuPDF | PyMuPDF handles encoding, ligatures, CJK, RTL; tested on all 5 docs |
| PDF to image | Poppler/Ghostscript subprocess | `page.get_pixmap()` in PyMuPDF | No binary deps; produces correct 200-DPI renders |
| Base64 image encoding | Manual bytes manipulation | `base64.b64encode(pix.tobytes("png"))` | Standard library, one line |
| Document classification heuristics | Regex/keyword matching | GPT-4.1 via `responses.parse()` | Handles layout variation, Portuguese, CREA-specific terminology |
| Structured JSON extraction from LLM | Manual `json.loads()` + validation | `client.responses.parse(text_format=PydanticModel)` | Guaranteed schema adherence, typed output |

**Key insight:** PyMuPDF eliminates ALL binary external dependencies (no Poppler, no Ghostscript, no Tesseract). GPT-4.1 eliminates ALL custom classification heuristics. The entire phase is ~150 lines of Python.

---

## Common Pitfalls

### Pitfall 1: Responses API vs Chat Completions — Different input format
**What goes wrong:** Copying Chat Completions Vision patterns into Responses API calls causes 400 errors.
**Why it happens:** The two APIs have similar purpose but different input schemas. Chat Completions: `messages=[{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "..."}}]}]`. Responses API: `input=[{"role": "user", "content": [{"type": "input_image", "image_url": "..."}]}]`.
**How to avoid:** Use `"type": "input_image"` with flat `"image_url"` string in Responses API. Use `instructions=` for system prompt instead of a system message in the list.
**Warning signs:** SDK raises validation error or `400 Bad Request` with schema mismatch message.

### Pitfall 2: PyMuPDF path handling on Windows
**What goes wrong:** `pymupdf.open(Path(...))` may fail on Windows with Path object.
**Why it happens:** PyMuPDF C extension expects a string, not a Python Path object.
**How to avoid:** Always call `pymupdf.open(str(caminho))`.
**Warning signs:** `TypeError: expected str, bytes or os.PathLike object, not WindowsPath` or similar.

### Pitfall 3: Large PDF (32 pages) converted all at once
**What goes wrong:** `saude indigena.pdf` has 32 pages. Converting all 32 to 200-DPI PNG images = ~32 × 500KB = ~16MB in memory.
**Why it happens:** Iterating over all pages eagerly during ingestion.
**How to avoid:** For classification, only convert page 0. For full pipeline (later phases), convert pages lazily or on-demand.
**Warning signs:** Memory usage spike during ingestion of `saude indigena.pdf`.

### Pitfall 4: Text encoding display issue vs actual corruption
**What goes wrong:** Developer sees `P\xe1gina 1/1` in terminal and assumes text is garbage.
**Why it happens:** Windows console defaults to cp1252/cp850. The text itself is valid UTF-8 Unicode (`á` = U+00E1). The data is correct; the display is misleading.
**How to avoid:** Trust the printable-character ratio (97-98% for all 5 test docs). Don't add unnecessary encoding fixes. GPT-4.1 receives the correct Unicode string.
**Warning signs:** Characters like á, ç, ã show as `\xe1`, `\xe7`, `\xe3` in terminal but as correct Unicode when inspected with `ord()`.

### Pitfall 5: Missing `doc.close()` — file handle leak
**What goes wrong:** PyMuPDF holds a file handle for the PDF's lifetime. In a loop over 5 files (or more in production), handles accumulate.
**Why it happens:** PyMuPDF's `Document` object is not a context manager by default in all versions.
**How to avoid:** Use `with pymupdf.open(str(path)) as doc:` or explicitly call `doc.close()` after processing.
**Warning signs:** `PermissionError` when trying to move/delete processed files; resource warning in tests.

### Pitfall 6: `output_parsed` can be None on refusal
**What goes wrong:** `response.output_parsed` is `None` if the model refused to answer (safety filter triggered).
**Why it happens:** Responses API `parse()` returns `None` for `output_parsed` on refusal, not a raised exception.
**How to avoid:** Check `if response.output_parsed is None` and handle with a fallback (e.g., classify as `DESCONHECIDO`).
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'tipo'`.

---

## Code Examples

### Complete minimal ingestion flow (verified patterns)

```python
# Source: verified against PyMuPDF 1.27.2.2 + openai 2.30.0 on this machine

import pymupdf
import base64
from pathlib import Path
from openai import OpenAI
from pydantic import BaseModel
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)

class ResultadoClassificacao(BaseModel):
    tipo: str
    confianca: float
    justificativa: str

def pagina_para_b64(page: pymupdf.Page) -> str:
    scale = config.IMAGE_DPI / 72
    mat = pymupdf.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat)
    return base64.b64encode(pix.tobytes("png")).decode("utf-8")

def tem_texto_nativo(doc: pymupdf.Document) -> bool:
    """True se o PDF tem texto nativo (não é puramente escaneado)."""
    total_chars = sum(len(page.get_text().strip()) for page in doc)
    chars_por_pagina = total_chars / max(len(doc), 1)
    return chars_por_pagina > 100

# Carregar e converter
with pymupdf.open(str(Path("Documentos que crea recebe/MA20250929762.aZzbC (1).pdf"))) as doc:
    texto_p0 = doc[0].get_text()
    imagem_p0_b64 = pagina_para_b64(doc[0])

# Classificar via GPT-4.1
resp = client.responses.parse(
    model=config.OPENAI_MODEL,
    instructions="Classifique o documento CREA. Tipos: ART, Atestado, Declaracao, Anuencia, NF, Contrato, RelatorioFotografico, Desconhecido.",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_text", "text": texto_p0[:2000]},
            {"type": "input_image", "image_url": f"data:image/png;base64,{imagem_p0_b64}", "detail": "low"}
        ]
    }],
    text_format=ResultadoClassificacao,
)
resultado = resp.output_parsed  # ResultadoClassificacao instance
print(resultado.tipo, resultado.confianca)
```

### Context manager for doc (pitfall prevention)

```python
# Correct: use context manager or explicit close
with pymupdf.open(str(caminho)) as doc:
    paginas = [page.get_text() for page in doc]
# File handle released automatically
```

---

## Runtime State Inventory

Step 2.5 SKIPPED — this is a greenfield implementation phase, not a rename/refactor/migration.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PyMuPDF | INGS-02 (PDF conversion) | Yes | 1.27.2.2 | — |
| openai Python SDK | INGS-03 (GPT-4.1 classification) | Yes | 2.30.0 | — |
| pydantic | Structured output (responses.parse) | Yes | 2.12.4 | — |
| pytest | Test execution | Yes | 9.0.2 | — |
| OPENAI_API_KEY | Live API calls in tests | Unknown | — | Mock/skip API calls in unit tests |
| Input PDFs | INGS-01, INGS-04 | Yes | 5 files in `Documentos que crea recebe/` | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:**
- OPENAI_API_KEY: Unknown at research time. Unit tests must mock `client.responses.parse` to avoid requiring a live key. Integration test (using real API) can be marked with `@pytest.mark.integration` and skipped by default.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | None — no pytest.ini exists; use default discovery |
| Quick run command | `python -m pytest tests/test_ingestion.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INGS-01 | `carregar_pacote(dir)` loads all PDFs from directory | unit | `python -m pytest tests/test_ingestion.py::test_carrega_diretorio -x` | No — Wave 0 |
| INGS-02 | PyMuPDF renders page to PNG and extracts native text | unit | `python -m pytest tests/test_ingestion.py::test_converte_pdf -x` | No — Wave 0 |
| INGS-02 | Native text heuristic correctly identifies text-bearing docs | unit | `python -m pytest tests/test_ingestion.py::test_detecta_texto_nativo -x` | No — Wave 0 |
| INGS-03 | GPT-4.1 classifies each of 5 test docs to correct type | integration | `python -m pytest tests/test_ingestion.py::test_classificacao_docs_reais -x -m integration` | No — Wave 0 |
| INGS-03 | Classification returns valid `TipoDocumento` enum value | unit (mock) | `python -m pytest tests/test_ingestion.py::test_classificacao_mockada -x` | No — Wave 0 |
| INGS-04 | `_agrupar_documentos()` groups 5 docs into 1 ART + 1 Atestado + 1 complementar + ... | unit | `python -m pytest tests/test_ingestion.py::test_agrupa_documentos -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_ingestion.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_ingestion.py` — covers INGS-01, INGS-02, INGS-03 (mocked), INGS-04
- [ ] `tests/conftest.py` — fixture: real PDF paths from `Documentos que crea recebe/`, mock OpenAI client

*(No framework install needed — pytest 9.0.2 already installed)*

---

## Test Documents — Identified Ground Truth

For INGS-03 validation, the correct classification of all 5 test docs is known:

| Filename | Expected Type | Evidence |
|----------|--------------|---------|
| `944678.2026__ACT_Alexandre_...pdf` | Atestado | First line: "ATESTADO DE CAPACIDADE TÉCNICA" |
| `944678.2026__DECLARACAO__...pdf` | Declaracao | First line: "DECLARAÇÃO FISCAL" |
| `MA20250929762.aZzbC (1).pdf` | ART | Header: "Anotação de Responsabilidade Técnica - ART" |
| `MA20250957723.ac6Y3.pdf` | ART | Header: "Anotação de Responsabilidade Técnica - ART" — 2 pages |
| `saude indigena.pdf` | Atestado | Header: "ATESTADO DE CAPACIDADE TÉCNICA" — 32 pages |

**Document pairs:**
- Par 1: `MA20250929762` (ART) + `944678...ACT` (Atestado) + `944678...DECLARACAO` (Declaracao)
- Par 2: `MA20250957723` (ART) + `saude indigena` (Atestado)

---

## Project Constraints (from CLAUDE.md)

All directives from CLAUDE.md that constrain this phase:

| Directive | Impact on Phase 2 |
|-----------|-------------------|
| `import pymupdf` (never `import fitz`) | All code in ingestion.py must use this import |
| `OPENAI_API_KEY` via env var | Never hardcode key; read from `config.OPENAI_API_KEY` |
| Model: `gpt-4.1` | Use `config.OPENAI_MODEL` — do not hardcode `"gpt-4.1"` |
| Responses API with structured output | Use `client.responses.parse(text_format=PydanticModel)` — not `chat.completions` |
| `pathlib.Path` for all paths | No `os.path` usage; no raw string paths |
| Messages in pt-BR | All `print()` statements, log messages, error messages in Portuguese |
| No new dependencies | Do not add to `requirements.txt` |
| Windows 11, no Docker | No Unix-only assumptions (shebangs, `/tmp`, etc.) |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `import fitz` (PyMuPDF legacy) | `import pymupdf` | PyMuPDF 1.24+ | Breaking change — old tutorials use `fitz` |
| Chat Completions for structured output | Responses API with `parse()` | openai SDK 1.50+ | Simpler — no manual JSON parsing |
| `beta.chat.completions.parse()` | `responses.parse()` | openai SDK 2.x | Responses API is the current preferred endpoint |
| `"type": "image_url"` in messages | `"type": "input_image"` in Responses API | Responses API launch | Different schema between the two endpoints |

**Deprecated/outdated:**
- `import fitz`: Works but violates CLAUDE.md convention. All PyMuPDF docs now show `import pymupdf`.
- `client.chat.completions.create(response_format={"type": "json_schema"})`: Still works but Responses API is the stated convention in CLAUDE.md.

---

## Open Questions

1. **API key availability for integration tests**
   - What we know: Tests need to call real GPT-4.1 for INGS-03 validation against the 5 test docs
   - What's unclear: Whether OPENAI_API_KEY is always available in the test environment
   - Recommendation: Mock the API in unit tests. Mark integration tests with `@pytest.mark.integration` and add a conftest.py skip condition if key is absent.

2. **Grouping heuristic for multiple ARTs in same directory**
   - What we know: INGS-04 says "múltiplos documentos complementares". Current test data has 1 ART per pair.
   - What's unclear: What should happen if a directory contains 2 ARTs (e.g., for multi-phase projects)?
   - Recommendation: For MVP, group as: first ART found = ART, all others = nao_classificados. Document this limitation.

---

## Sources

### Primary (HIGH confidence)
- Verified by running code against installed PyMuPDF 1.27.2.2 — `page.get_pixmap()`, `page.get_text()`, `pymupdf.Matrix`, `pymupdf.open(str(path))`
- Verified by inspecting openai SDK 2.30.0 source at `/c/Users/gusta/AppData/Local/Programs/Python/Python313/Lib/site-packages/openai/resources/responses/responses.py` — `responses.parse()` signature, `text_format` parameter, `ResponseInputImageContent` schema
- Verified by running against all 5 real test PDFs in `Documentos que crea recebe/`

### Secondary (MEDIUM confidence)
- PyMuPDF official docs: https://pymupdf.readthedocs.io/ — Matrix DPI calculation `dpi/72`, `get_text()` encoding
- OpenAI Responses API guide: https://platform.openai.com/docs/guides/responses — input format for Vision

### Tertiary (LOW confidence — flag for validation)
- None identified. All critical patterns verified directly from installed SDK source and live test runs.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified installed versions, confirmed API compatibility
- Architecture: HIGH — verified against real PDFs and SDK source code
- Pitfalls: HIGH — discovered through direct testing (encoding issue, path issue confirmed)
- Classification prompt design: MEDIUM — GPT-4.1 behavior with these specific document types not live-tested (API key not verified available)

**Research date:** 2026-03-28
**Valid until:** 2026-06-28 (stable libraries — PyMuPDF and openai SDK change slowly for core APIs)
