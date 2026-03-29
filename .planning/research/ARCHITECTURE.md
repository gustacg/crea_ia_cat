# Architecture Patterns: CREA CAT Document Analysis Pipeline

**Domain:** Document forensics and compliance analysis pipeline
**Researched:** 2026-03-28
**Overall confidence:** HIGH (core patterns); MEDIUM (ICP-Brasil specifics)

---

## Recommended Architecture

A sequential, stage-gated pipeline where each document pair (ART + Atestado) flows
through 10 bounded modules. Each module receives a structured context object and
appends its findings before passing the enriched context forward. No module skips
a later module; later modules may short-circuit on error flags set by earlier modules.

```
[INPUT]
  PDF file pair
       │
       ▼
┌─────────────────────────────────┐
│  1. DocumentIngestion           │  Detects PDF type, extracts raw bytes
│     + type classification       │  Output: DocumentContext (type, pages)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  2. TextExtractionLayer         │  Hybrid: native first, OCR on image pages
│     (PyMuPDF + Tesseract)       │  Output: adds .text_pages[] to context
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  3. MetadataAnalyzer            │  CreationDate, ModDate, Producer, Author
│     (pikepdf)                   │  Output: adds .pdf_metadata to context
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  4. EntityExtractor             │  NER: name, CPF, CNPJ, CREA, date, address
│     (spaCy pt_core_news_lg      │  + regex fallback for structured fields
│      + custom EntityRuler)      │  Output: adds .entities to context
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  5. ImageForensicsAnalyzer      │  ELA per page, signature block detection,
│     (Pillow + OpenCV)           │  letterhead presence check
│                                 │  Output: adds .image_findings to context
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  6. DigitalSignatureValidator   │  ICP-Brasil cert chain + integrity check
│     (pyHanko + pyOpenSSL)       │  Output: adds .sig_validation to context
└────────────────┬────────────────┘
                 │
                 ▼

          ── PAIR MERGE POINT ──
     (ART context + Atestado context)
                 │
                 ▼
┌─────────────────────────────────┐
│  7. CrossDocumentComparator     │  Exact match (fields), fuzzy match
│     (rapidfuzz + GPT-4o)        │  (names/address), semantic match (scope)
│                                 │  Output: .comparison_results
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  8. ComplianceChecker           │  Anexo IV checklist + Res. 1.160/2025
│                                 │  SpellCheck (LanguageTool)
│                                 │  Output: .compliance_findings
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  9. VerdictEngine               │  Weighted scoring → ADERENTE / PENDENTE /
│                                 │  SUSPEITO + confidence 0.0–1.0
│                                 │  Output: .verdict, .confidence, .exigencias
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  10. ReportGenerator            │  JSON (structured) + Markdown (human)
│                                 │  per document pair
└────────────────┴────────────────┘
                 │
                 ▼
           [OUTPUT FILES]
```

---

## Central Data Structure: PipelineContext

Every module reads from and writes to a single `PipelineContext` object. No module
stores state externally. This is the pipeline's single source of truth.

```python
@dataclass
class PipelineContext:
    # --- Identity ---
    pair_id: str
    art_path: Path
    atestado_path: Path

    # --- Per-document sections (populated by modules 1-6) ---
    art: DocumentContext
    atestado: DocumentContext

    # --- Cross-document sections (populated by modules 7-8) ---
    comparison: ComparisonResult | None = None
    compliance: ComplianceResult | None = None

    # --- Final verdict (module 9) ---
    verdict: Verdict | None = None           # ADERENTE | PENDENTE | SUSPEITO
    confidence: float | None = None          # 0.0 – 1.0
    exigencias: list[str] = field(default_factory=list)

    # --- Error tracking ---
    errors: list[PipelineError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class DocumentContext:
    doc_type: DocType            # ART | ATESTADO | UNKNOWN
    pdf_type: PdfType            # NATIVE | SCANNED | MIXED | IMAGE_ONLY
    raw_path: Path
    text_pages: list[str]        # populated by module 2
    full_text: str               # concatenation of text_pages
    pdf_metadata: PdfMetadata    # populated by module 3
    entities: ExtractedEntities  # populated by module 4
    image_findings: ImageReport  # populated by module 5
    sig_validation: SigReport    # populated by module 6
```

Use Python `@dataclass` for all internal structures (no validation overhead at each
stage). Use `pydantic.BaseModel` only at the boundary — when serializing the final
`PipelineContext` to JSON for the report.

---

## Component Boundaries

### What Each Module Owns

| Module | Reads | Writes | External Deps |
|--------|-------|--------|---------------|
| 1. DocumentIngestion | PDF file bytes | `doc.pdf_type`, `doc.doc_type` | PyMuPDF, pikepdf |
| 2. TextExtractionLayer | `doc.pdf_type`, raw file | `doc.text_pages`, `doc.full_text` | PyMuPDF, pytesseract |
| 3. MetadataAnalyzer | raw file | `doc.pdf_metadata` | pikepdf |
| 4. EntityExtractor | `doc.full_text` | `doc.entities` | spaCy + EntityRuler, regex |
| 5. ImageForensicsAnalyzer | raw file + page images | `doc.image_findings` | Pillow, OpenCV |
| 6. DigitalSignatureValidator | raw file | `doc.sig_validation` | pyHanko, pyOpenSSL |
| 7. CrossDocumentComparator | `art.entities` + `atestado.entities` + `full_text` | `ctx.comparison` | rapidfuzz, OpenAI GPT-4o |
| 8. ComplianceChecker | `ctx.comparison`, both `entities`, both `full_text` | `ctx.compliance` | LanguageTool |
| 9. VerdictEngine | `ctx.compliance`, `ctx.comparison`, all `image_findings`, all `sig_validation` | `ctx.verdict`, `ctx.confidence`, `ctx.exigencias` | none (pure logic) |
| 10. ReportGenerator | entire `PipelineContext` | files on disk | pydantic (serialization) |

**Rule:** No module imports another module. All communication is through
`PipelineContext`. This allows replacing any module without cascading changes.

---

## Data Flow Direction (Explicit)

```
PDF bytes
  → DocType + PdfType (classification)
    → RawText per page (extraction)
      → PdfMetadata (forensic metadata)
        → ExtractedEntities (NER)
          → ImageFindings (ELA + visual)
            → SigValidation (ICP-Brasil check)

[PAIR MERGE]

(ART entities + Atestado entities + texts)
  → ComparisonResult (field-by-field + semantic)
    → ComplianceResult (Anexo IV checklist + spell)
      → Verdict + Confidence + Exigencias
        → JSON report + Markdown report
```

At the pair merge point (module 7 boundary), individual `DocumentContext` objects
become read-only. Only `PipelineContext`-level fields are written from that point
forward.

---

## Error Handling Strategy

### Principle: Degrade Gracefully, Never Abort

A missing signature should not stop the NER extraction. A failed OCR pass should
still return whatever native text was available. The pipeline always produces a
verdict, but with reduced confidence and explicit warnings.

### Two Error Tiers

**Tier 1 — Module Error (soft failure):**
The module catches its own exceptions, appends a `PipelineError` to
`ctx.errors`, sets the affected field to `None` or an empty/default value, and
returns. The pipeline continues with the next module.

```python
@dataclass
class PipelineError:
    module: str          # e.g., "DigitalSignatureValidator"
    message: str
    severity: Severity   # WARNING | ERROR | CRITICAL
    recoverable: bool
```

**Tier 2 — Critical failure (hard stop):**
Only if text extraction produces zero text for both documents does the pipeline
halt early and return a `PENDENTE` verdict with the error as the sole exigencia.
This is the only legitimate early-exit scenario.

### Confidence Penalty System

Each module error contributes a confidence penalty applied in the VerdictEngine:

| Error Type | Confidence Penalty |
|---|---|
| OCR partial failure (some pages) | -0.05 |
| NER found < 3 required fields | -0.10 |
| Metadata analysis failed | -0.05 |
| ELA analysis failed | -0.08 |
| Sig validation failed (no sig present) | -0.15 |
| Sig validation failed (invalid sig) | -0.25 |
| LLM semantic comparison unavailable | -0.15 |

Verdict thresholds are adjusted up when confidence is penalized, so a degraded
pipeline is more conservative (favors PENDENTE over ADERENTE when uncertain).

---

## Module-Level Design Notes

### Module 1: Document Ingestion

Detection heuristic (in order):
1. Open with PyMuPDF → count pages with `get_text()` returning > 50 chars
2. Count pages dominated by large images (> 80% of page area)
3. Classify: all native → `NATIVE`; all image-dominant → `SCANNED`; mixed → `MIXED`

Document type classification (ART vs Atestado) uses keyword matching on first
500 chars: "Anotação de Responsabilidade Técnica", "ART nº", "Atesta que",
"certifica". Falls back to filename heuristic.

### Module 2: Text Extraction Layer

Strategy: page-by-page hybrid.

```
for each page:
  native_text = pymupdf.get_text()
  if len(native_text.strip()) < 50:      # page is image-dominant
    ocr_text = pytesseract.image_to_string(page_as_image, lang="por")
    use ocr_text
  else:
    use native_text
```

pdfplumber is used as fallback for table-heavy pages where PyMuPDF produces
garbled column ordering. PyMuPDF is the primary extractor.

### Module 3: Metadata Analyzer

Extract via pikepdf: `/CreationDate`, `/ModDate`, `/Producer`, `/Author`,
`/Creator`. Parse PDF date strings using `pikepdf.models.metadata.decode_pdf_date`.

Forensic flag triggers:
- `ModDate` newer than `CreationDate` by > 1 minute → flag "metadata_modified"
- `Producer` contains image editors (Photoshop, GIMP, Canva) → flag "non_pdf_origin"
- `ModDate` in the future → flag "future_date"

### Module 4: Entity Extractor

Two-pass approach:

**Pass 1 — Regex patterns (HIGH confidence, structured fields):**
- CPF: `\d{3}\.?\d{3}\.?\d{3}-?\d{2}`
- CNPJ: `\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}`
- CREA registration: `CREA[-\s]?\w{2}[-\s]?\d+`
- Date patterns (DD/MM/YYYY and variations)
- Monetary values

**Pass 2 — spaCy NER (MEDIUM confidence, unstructured fields):**
- `pt_core_news_lg` for PER (person names), ORG (company names), LOC (addresses)
- Custom `EntityRuler` component added to pipeline before NER for the regex
  patterns above, so CPF/CNPJ found by regex are promoted to spaCy spans

This prevents the NER model from hallucinating CPFs it didn't see.

### Module 5: Image Forensics Analyzer

Two sub-checks run independently:

**ELA sub-check:**
1. Render each PDF page to RGB image at 150 DPI
2. Save as JPEG at quality=75 (introduce compression)
3. Compute `ImageChops.difference(original, recompressed)`
4. Amplify differences by 20x
5. Compute mean brightness of amplified diff → ELA score
6. Flag if ELA score > threshold (empirically: 15/255 for B&W documents)

**Signature visual detection sub-check (OpenCV):**
1. Convert page to grayscale
2. Apply Canny edge detection
3. Find contours in signature-likely zones (bottom 30% of page)
4. Flag copy-paste signature if the signature region's JPEG quality is
   inconsistent with surrounding content (ELA brightness spike in signature zone)

**Letterhead detection:**
1. Check top 15% of page 1 for non-white pixel density > 20%
2. Flag presence or absence for compliance check

### Module 6: Digital Signature Validator

ICP-Brasil certificate chain validation via pyHanko:

```python
from pyhanko.sign import validation
from pyhanko.sign.validation import StandardPdfValidator

# Build validation context with ICP-Brasil root CAs
vc = validation.RevocationInfoFetchingContext(
    allow_fetching=False,          # offline — MVP constraint
    trust_roots=load_icp_brasil_roots()
)
result = validate_pdf_signature(reader, sig, vc)
```

Key outputs captured:
- `intact`: document bytes unchanged since signing
- `valid`: certificate chain valid to ICP-Brasil root
- `trusted`: signer cert issued by trusted CA
- `signer_cert.subject`: name/CPF embedded in cert (cross-reference with NER)

ICP-Brasil root certificates must be bundled with the project
(offline, no OCSP in MVP). Source: ITI.gov.br PKI repository.

Note: Many CREA atestados use NO digital signature (paper letterhead only).
Module 6 must handle `no_signature_found` as a valid non-error state — it
contributes to compliance scoring, not a pipeline error.

### Module 7: Cross-Document Comparator

Three comparison tiers applied in sequence:

**Tier A — Exact match:**
CPF, CNPJ, CREA number. Must be identical strings after normalization (remove
punctuation, normalize whitespace). Mismatch is high-severity finding.

**Tier B — Fuzzy match (rapidfuzz):**
Person names, company names, addresses. Use `fuzz.token_sort_ratio` (handles
word reordering). Threshold: >= 85 for match, 70-84 for "similar" (flag for
review), < 70 for mismatch.

**Tier C — Semantic match (GPT-4o):**
Service scope/object description. Single prompt comparing the "objeto" field
from ART vs the "Descrição dos Serviços" from Atestado. Ask GPT-4o to return:
- `compatible`: bool
- `similarity_score`: 0.0–1.0
- `divergences`: list[str]
- `reasoning`: str

GPT-4o is called ONCE per pair for the semantic comparison, not per field.
Consolidate all semantic questions into one prompt to minimize cost/latency.

### Module 8: Compliance Checker

Checklist-driven. For each Anexo IV item, a `ComplianceItem` is produced:

```python
@dataclass
class ComplianceItem:
    item_id: str                 # "ANEXO_IV_1_1" etc.
    description: str
    status: Status               # PRESENT | ABSENT | UNCLEAR
    evidence: str | None         # extracted text that proves presence
    notes: str | None
```

Spell check via LanguageTool: run against the full Atestado text, collect
errors with their positions. Flag if error count > 5 (heuristic for generated/
translated documents).

### Module 9: Verdict Engine

Pure Python logic — no external calls. Applies a weighted scoring model:

```
base_score = 1.0

# Hard blockers → force SUSPEITO
if image_findings.ela_manipulation_detected:        base_score = 0.0
if sig_validation.intact == False:                  base_score = 0.0

# Severe deductions
if comparison.cpf_mismatch:                         base_score -= 0.40
if comparison.cnpj_mismatch:                        base_score -= 0.30
if sig_validation.trusted == False:                 base_score -= 0.25

# Moderate deductions
if compliance.missing_required_fields > 0:         base_score -= 0.10 * count
if comparison.name_fuzzy_score < 70:               base_score -= 0.15
if comparison.semantic_compatible == False:         base_score -= 0.20

# Minor deductions
if metadata.metadata_modified:                      base_score -= 0.05
if compliance.spell_errors > 5:                     base_score -= 0.05
```

Verdict mapping:
- `score >= 0.80` → **ADERENTE**
- `0.50 <= score < 0.80` → **PENDENTE** (generate exigências list)
- `score < 0.50` → **SUSPEITO** (generate exigências + flag for human review)

Confidence = final score after module-failure penalties.

### Module 10: Report Generator

Two outputs per pair:

**`report_{pair_id}.json`** — Full `PipelineContext` serialized via pydantic.
Used for downstream tooling, audit trails, re-processing.

**`report_{pair_id}.md`** — Human-readable Markdown structured as:
1. Summary (verdict badge + confidence)
2. Document classification table
3. Entity comparison table (ART vs Atestado, field by field)
4. Compliance checklist (Anexo IV items with PRESENT/ABSENT)
5. Forensic findings (metadata anomalies, ELA results, signature status)
6. Semantic analysis (GPT-4o scope comparison)
7. Exigências list (numbered, if PENDENTE/SUSPEITO)
8. Analyst notes section (blank — for human to fill)

---

## Suggested Build Order

Build order follows data dependencies: later modules depend on earlier modules'
outputs. This also allows incremental testing — each module can be tested with
a mock `DocumentContext`.

```
Phase 1 — Foundation (modules 1 + 2)
  Rationale: All later modules need text. Can't build anything without this.
  Test gate: assert full_text is not empty for test PDFs

Phase 2 — Per-document enrichment (modules 3 + 4 + 5)
  Rationale: No cross-document dependencies. Can be built and tested in parallel.
  Test gate: entities contains CPF from known test PDF

Phase 3 — Digital signature (module 6)
  Rationale: Separate because requires bundled ICP-Brasil certs and pyHanko
  setup. Most likely to have environment issues on Windows 11.
  Test gate: no exception on unsigned PDF (graceful no_sig handling)

Phase 4 — Cross-document logic (module 7)
  Rationale: Requires both DocumentContexts fully populated. GPT-4o call here.
  Test gate: comparison_results populated for known-matching test pair

Phase 5 — Compliance + Verdict (modules 8 + 9)
  Rationale: Sequential dependency. Verdict needs compliance findings.
  Test gate: ADERENTE verdict for known-clean test pair

Phase 6 — Report generation (module 10)
  Rationale: Terminal. All data must be correct before formatting.
  Test gate: valid JSON + Markdown files written to disk

Phase 7 — End-to-end integration
  Run full pipeline on 2 real test pairs. Verify verdict correctness.
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Shared Mutable State Outside PipelineContext
**What:** Global variables or module-level caches holding document data.
**Why bad:** Makes testing non-deterministic, breaks pair-level isolation.
**Instead:** All state flows through `PipelineContext`. Module functions are pure
input→output with side effects only to the context object they receive.

### Anti-Pattern 2: Calling GPT-4o Per Field
**What:** Sending 10 separate API calls for 10 comparison fields.
**Why bad:** Latency (10x), cost (10x), rate-limit risk.
**Instead:** Batch all semantic questions into one structured prompt. Use
GPT-4o's JSON mode (`response_format={"type": "json_object"}`) to get
structured multi-field output in a single call.

### Anti-Pattern 3: Treating OCR Failure as Pipeline Failure
**What:** Raising an exception if Tesseract produces empty output.
**Why bad:** Scanned PDFs may have low-quality pages. One bad page stops everything.
**Instead:** Empty OCR output → store empty string + `PipelineError(severity=WARNING)`.
VerdictEngine penalizes confidence, but pipeline continues.

### Anti-Pattern 4: Validating Digital Signature Online
**What:** Making OCSP/CRL requests to ICP-Brasil servers at runtime.
**Why bad:** No internet guarantee in CLI tool, latency, privacy concern.
**Instead:** Bundle ICP-Brasil root CA chain offline. Accept `unable_to_verify_revocation`
as a warning, not an error. Document the limitation clearly in the report.

### Anti-Pattern 5: Storing Per-Module State in Module-Level Variables
**What:** A module keeps a cache of processed documents between runs.
**Why bad:** Pairs bleed into each other if the pipeline is run on multiple pairs.
**Instead:** Each `run_module(ctx)` call is stateless. Initialize fresh objects
inside the function. The spaCy model and GPT-4o client are loaded once at
pipeline startup and passed as dependencies.

---

## Scalability Considerations

This is an MVP for 2 test pairs. The architecture, however, supports growth:

| Concern | MVP (2 pairs) | Future (100+ pairs) |
|---------|---------------|---------------------|
| Processing | Sequential, in-memory | `concurrent.futures.ProcessPoolExecutor` per pair |
| Storage | Files on disk | SQLite or simple JSON store |
| LLM calls | One per pair | Batch API or caching by hash |
| OCR | Tesseract local | Keep local; add GPU Tesseract option |
| Reporting | Per-pair files | Aggregated summary report |

The `PipelineContext` dataclass is serializable to JSON from day 1 (pydantic at
boundary). This means adding a database later requires only the write layer, not
a data structure change.

---

## Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Sequential pipeline over parallel stages | 2 pairs, MVP; sequential is debuggable and sufficient |
| Single `PipelineContext` object | Zero inter-module coupling; full auditability |
| Dataclasses internal, Pydantic at boundary | Performance in hot path, validation at serialization |
| Degrade gracefully on module failure | Pipeline must always produce a verdict, even with partial data |
| GPT-4o called once per pair (batched) | Cost and latency control; JSON mode for structured output |
| Bundle ICP-Brasil certs offline | No runtime network dependency; reproducible results |
| Per-page hybrid OCR decision | Avoids OCR on native pages (10-50x speed gain) |
| Regex before NER for structured fields | CPF/CNPJ regex is 100% reliable; NER is for unstructured fields only |

---

## Sources

- [PyMuPDF Text Extraction Strategies — Artifex](https://artifex.com/blog/text-extraction-strategies-with-pymupdf)
- [Best Python PDF to Text Parser Libraries — Unstract 2026](https://unstract.com/blog/evaluating-python-pdf-to-text-libraries/)
- [pyHanko Validation Functionality — Official Docs](https://docs.pyhanko.eu/en/latest/lib-guide/validation.html)
- [pyHanko GitHub — MatthiasValvekens](https://github.com/MatthiasValvekens/pyHanko)
- [spaCy Industrial-strength NLP](https://spacy.io/)
- [Named Entity Recognition for Portuguese — Melanie Walsh](https://melaniewalsh.github.io/Intro-Cultural-Analytics/05-Text-Analysis/Multilingual/Portuguese/02-Named-Entity-Recognition-Portuguese.html)
- [ELA for Document Forensics — Medium](https://arvindn-iitkgp.medium.com/on-document-forensics-for-id-card-fraud-detection-using-ela-and-rpa-23c68dd8f3e0)
- [ELA Python Implementation — GitHub](https://github.com/Neo31415/ELA/)
- [pikepdf Metadata — Official Docs](https://pikepdf.readthedocs.io/en/latest/topics/metadata.html)
- [Pydantic Data Pipeline Validation — Medium](https://medium.com/@caodanju/python-data-pipeline-data-validation-with-pydantic-a5145ac4432b)
- [Fuzzy Matching with LLMs — Jonathan Soma](https://jonathansoma.com/everything/ai-ml/fuzzy-matching-with-llms/)
