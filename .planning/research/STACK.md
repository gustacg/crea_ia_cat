# Technology Stack

**Project:** CREA CAT AI — Python Document Analysis & Fraud Detection Pipeline
**Researched:** 2026-03-28
**Platform:** Windows 11, Python 3.13, local execution (no Docker, no server)

---

## Recommended Stack

### PDF Parsing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PyMuPDF (`pymupdf`) | 1.27.2.2 | Primary PDF text extraction, image extraction, metadata | Fastest Python PDF library, low memory, handles native text PDFs with layout preservation. The new import name is `pymupdf` (fitz still works as alias). Extracts embedded images directly — critical for ELA. |
| pdfplumber | 0.11.9 | Table extraction from ART forms | ART PDFs frequently use tables for fields (contrato, parcelas, valores). pdfplumber gives per-character coordinates and table bounding boxes. PyMuPDF cannot detect tables as tables. |

**Decision:** Use both. PyMuPDF as primary extraction engine; pdfplumber specifically for table/form field detection. Do NOT use pdfminer.six directly — pdfplumber wraps it and adds layout intelligence.

**What NOT to use:**
- `pdfminer.six` directly: lower-level than pdfplumber, more setup for no gain
- `pypdf` (formerly PyPDF2): adequate for merging/splitting but poor text fidelity versus PyMuPDF

---

### OCR

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytesseract | 0.3.13 | OCR wrapper for Tesseract 5 | Constrained by PROJECT.md. Tesseract 5 with LSTM engine (--oem 1) achieves 80–85% accuracy on clean scans. Portuguese language pack (`por`) is mature. |
| Tesseract 5 (binary) | 5.x | OCR engine | Must be installed separately on Windows (UB Mannheim builds). Use `--psm 6` for uniform blocks, `--psm 3` (default) for mixed layouts, `--oem 1` (LSTM only). |
| pdf2image | latest | Convert PDF pages to PIL images for OCR | Wraps poppler's `pdftoppm`. Required when PDF has no native text layer. |
| Pillow (PIL) | latest | Image preprocessing before Tesseract | Grayscale conversion, thresholding (binarization), deskew. Quality preprocessing is the single highest-impact lever for Tesseract accuracy. |

**Tesseract confidence level:** MEDIUM. 80–85% accuracy is sufficient for structured fields (CPF, CNPJ, dates) but may require fallback logic for low-contrast scans.

**OCR alternatives considered and rejected:**

| Alternative | Why Rejected |
|-------------|-------------|
| EasyOCR | GPU-optional but higher RAM usage on CPU; no meaningful accuracy gain over Tesseract 5 LSTM for clean Brazilian document scans; adds heavy PyTorch dependency |
| PaddleOCR | Excellent multilingual accuracy, BUT requires PaddlePaddle framework (~1.5GB), complex Windows install, overkill for 2-document MVP |
| Claude Vision / GPT-4o Vision | Requires API call per page; cost and latency scale with document volume; good as fallback for unreadable pages, but not primary OCR for a local pipeline |

**Recommendation for hard cases:** If Tesseract confidence falls below threshold (e.g., `<70` from `image_to_data`), send that specific page crop to GPT-4o Vision as fallback. This is the pragmatic hybrid approach — local-first, API fallback.

---

### Metadata Extraction

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pikepdf | 10.5.1 | Deep PDF metadata extraction | Exposes both `docinfo` (legacy) and XMP metadata streams. Read creation date, modification date, producer application (e.g., "Microsoft Word" vs "Adobe Acrobat" — mismatch is a fraud signal). Powered by QPDF C++ library, reliable on malformed PDFs. |
| PyMuPDF | 1.27.2.2 | Quick metadata via `doc.metadata` | Cross-verify against pikepdf. PyMuPDF metadata is fast but limited to the trailer dictionary. |

**What NOT to use:**
- `exiftool` (subprocess): works, but requires Perl runtime on Windows; pikepdf+PyMuPDF covers all required PDF metadata fields without Perl
- `pypdf` metadata: incomplete XMP support

---

### Digital Signature Validation (ICP-Brasil)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pyHanko | 0.34.1 | ICP-Brasil digital signature validation | The only production-grade Python library for PDF digital signature validation implementing AdES (ETSI EN 319 102-1). Validates: certificate chain, signature integrity, revocation status (CRL/OCSP). Requires Python 3.10+. |
| pyhanko-certvalidator | (bundled with pyHanko) | Certificate chain validation | Implements RFC 5280 path validation. Fetches CRLs from ICP-Brasil distribution points. Note: ICP-Brasil root CA does not support OCSP — validation falls back to CRL only at root level. |
| cryptography | 46.0.0+ | Low-level crypto primitives | Required by pyHanko. Also useful for direct X.509 certificate parsing (issuer, subject, validity dates, SANs). |
| pyOpenSSL | 26.0.0 | Legacy certificate operations | Use only if pyHanko cannot handle a specific certificate format. The `cryptography` library is preferred for new code (PyCA's own recommendation). |

**ICP-Brasil configuration notes (MEDIUM confidence):**
- Download the ICP-Brasil root certificate bundle from `https://acraiz.icpbrasil.gov.br/`
- Configure pyHanko with `trust: /path/to/icp-brasil-chain.pem` and `trust-replace: true`
- CRL validation is the primary revocation mechanism (OCSP only available at sub-CA level)
- ICP-Brasil CRLs are refreshed every 6 hours maximum — for offline validation (MVP), accept CRL staleness up to 24 hours

**What NOT to use:**
- Manual OpenSSL subprocess calls: brittle, platform-dependent
- `pdf-signature-validate` (unmaintained): last commit 2021

---

### Image Analysis (ELA + Visual Fraud Detection)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| opencv-python | 4.13.0.92 | Template matching, edge detection, image comparison | Industry standard for computer vision in Python. Use `cv2.matchTemplate()` for letterhead/signature detection. Use `cv2.Canny()` for edge anomalies. No GPU required for this workload. |
| Pillow | latest | ELA (Error Level Analysis) | ELA requires JPEG re-save and `ImageChops.difference()` — Pillow's native operations are the standard implementation. OpenCV reads the result for visualization. |

**ELA Implementation Pattern:**
```python
from PIL import Image, ImageChops, ImageEnhance
import io

def compute_ela(image_path: str, quality: int = 95) -> Image.Image:
    original = Image.open(image_path).convert("RGB")
    buffer = io.BytesIO()
    original.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    resaved = Image.open(buffer)
    ela_image = ImageChops.difference(original, resaved)
    # Amplify differences for visibility
    extrema = ela_image.getextrema()
    max_diff = max(ex[1] for ex in extrema) or 1
    scale = 255.0 / max_diff
    ela_image = ImageEnhance.Brightness(ela_image).enhance(scale)
    return ela_image
```

**ELA limitations (important for fraud scoring):**
- ELA is a heuristic, not forensic proof. A HIGH ELA region could be a logo, photo, or shadow — not necessarily manipulation.
- ELA is more reliable for detecting pasted-in text (CPF, dates, values) than for detecting subtle signature overlay.
- For the MVP: flag ELA anomalies as SUSPEITO signal, require human analyst confirmation.

**What NOT to use:**
- Deep learning ELA (VGG16, ResNet): 96% accuracy but requires GPU and training data; overkill for MVP with 2 document pairs
- `imageio` for ELA: less control over JPEG quality parameter than Pillow

---

### Named Entity Recognition (NER) — Portuguese

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| spaCy | 3.7.x | NER pipeline runner | Fast, production-grade NLP framework. CPU-optimized. |
| pt_core_news_lg | 3.7.0 | Portuguese NER model | Largest pre-trained Portuguese model. F1=90.31% on NER. 500K word vectors (300-dim). Entities: PER, ORG, LOC, MISC. |

**Supported NER entity types (pt_core_news_lg 3.7.0):**
- `PER` — Person names (engenheiros, signatários)
- `ORG` — Organizations (empresas contratantes/contratadas)
- `LOC` — Locations (endereços de obra)
- `MISC` — Miscellaneous (may capture some project names)

**Critical limitation — HIGH confidence:** pt_core_news_lg does NOT natively extract CPF, CNPJ, RNP, or CREA registration numbers. These require custom regex patterns on top of spaCy output.

**Recommended pattern:** spaCy for PER/ORG/LOC extraction + regex for structured identifiers:
```python
import re

CPF_PATTERN   = re.compile(r'\d{3}\.\d{3}\.\d{3}-\d{2}')
CNPJ_PATTERN  = re.compile(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}')
CREA_PATTERN  = re.compile(r'CREA[-\s]?[A-Z]{2}[-\s]?\d+')
RNP_PATTERN   = re.compile(r'RNP[-\s]?\d+')
DATE_PATTERN  = re.compile(r'\d{2}/\d{2}/\d{4}|\d{2}\s+de\s+\w+\s+de\s+\d{4}')
```

**What NOT to use:**
- `pt_core_news_sm` or `pt_core_news_md`: smaller models, lower NER accuracy, no word vectors in sm
- BERTimbau fine-tuned NER: superior accuracy but requires HuggingFace + PyTorch (heavy dependency) — reserve for post-MVP improvement
- NLTK Portuguese: lacks modern NER pipeline

---

### LLM Integration (Semantic Analysis)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| openai (Python SDK) | 2.30.0 | GPT-4o API calls for semantic comparison | Constrained by PROJECT.md (user has existing key). Use Chat Completions API for structured output (JSON mode). |

**GPT-4o usage in pipeline:**
- Semantic comparison of "objeto/escopo do serviço" between Atestado and ART
- Final parecer synthesis (ADERENTE / PENDENTE / SUSPEITO) with reasoning
- Fallback OCR for unreadable page regions

**API pattern — use structured outputs:**
```python
from openai import OpenAI
import json

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o",
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": "Você é um analista do CREA..."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.1  # Low temperature for deterministic analysis
)
result = json.loads(response.choices[0].message.content)
```

**Model choice note (MEDIUM confidence):** As of March 2026, OpenAI has released newer models (GPT-4.1, o3). GPT-4o remains a strong choice for structured semantic analysis with JSON mode and is cost-effective. The user's existing key constrains to GPT-4o unless they have access to newer models. Do not switch to o3 — reasoning models are slower and more expensive for this use case.

---

### Spell Checking (pt-BR)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| language_tool_python | 3.3.0 | Portuguese (pt-BR) grammar and spell checking | Wraps LanguageTool 6.x, runs local JVM server (no API key required). Detects non-words, obvious typos, and grammar errors in atestado text. Supports pt-BR natively. |

**Configuration:**
```python
import language_tool_python

tool = language_tool_python.LanguageTool('pt-BR')
matches = tool.check(text)
errors = [m for m in matches if m.ruleId.startswith('MORFOLOGIK')]
```

**Operational note:** On first run, language_tool_python downloads LanguageTool JAR (~200MB). Requires Java 8+ on the system. For the MVP (Windows 11 local), Java must be pre-installed.

**What NOT to use:**
- `pyspellchecker`: No pt-BR grammar rules, only word list matching
- `hunspell`: More complex setup, pt-BR dictionaries need manual import
- LanguageTool API (remote): Requires API key, adds network dependency

---

### Report Generation

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python `json` (stdlib) | built-in | Structured JSON output | Zero dependency. Pipeline output is a JSON dict with verdict, confidence score (0.0–1.0), field comparison results, and fraud flags. |
| Python `pathlib` + string templates | built-in | Markdown report generation | No external dependency. Use f-strings or simple template class for generating `.md` report per document pair. |

**What NOT to use:**
- Jinja2: Useful but an unnecessary dependency for MVP with simple templates
- WeasyPrint/ReportLab for PDF reports: Out of scope for MVP (CLI/script only)

---

## Complete Dependency List

```bash
# Core PDF processing
pip install pymupdf==1.27.2.2
pip install pdfplumber==0.11.9
pip install pikepdf==10.5.1
pip install pdf2image  # requires poppler binary on Windows

# OCR
pip install pytesseract==0.3.13
pip install Pillow

# Digital signatures
pip install pyHanko==0.34.1
pip install pyhanko-certvalidator
pip install cryptography>=46.0.0

# Image analysis
pip install opencv-python==4.13.0.92

# NLP / NER
pip install spacy==3.7.*
python -m spacy download pt_core_news_lg

# LLM integration
pip install openai==2.30.0

# Spell checking
pip install language_tool_python==3.3.0
# Requires: Java 8+ (JRE) on the system
```

**External binary dependencies (Windows):**
1. **Tesseract 5** — Install from UB Mannheim builds: `https://github.com/UB-Mannheim/tesseract/wiki`
   - Add to PATH or set `pytesseract.pytesseract.tesseract_cmd = r'C:\...\tesseract.exe'`
   - Install Portuguese language pack: `tessdata/por.traineddata`
2. **Poppler** — Download from `https://github.com/oschwartz10612/poppler-windows/releases`
   - Set `PDF2IMAGE_POPPLER_PATH` env var to `bin/` folder
3. **Java 8+ JRE** — Required by LanguageTool server JAR
   - Download from `https://adoptium.net/`

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| OCR | pytesseract (Tesseract 5) | EasyOCR | Heavy PyTorch dependency; no accuracy gain for clean Brazilian document scans on CPU |
| OCR | pytesseract | PaddleOCR | ~1.5GB PaddlePaddle runtime; complex Windows install; overkill for MVP |
| OCR | pytesseract | GPT-4o Vision | API cost per page; use as targeted fallback only |
| PDF primary | PyMuPDF | pdfminer.six | pdfplumber wraps it better; PyMuPDF is faster and extracts images |
| PDF tables | pdfplumber | camelot-py | camelot requires Ghostscript or Tk; pdfplumber has fewer system dependencies |
| NER | spaCy pt_core_news_lg | BERTimbau | PyTorch dependency (heavy); superior accuracy not needed for MVP structured fields |
| Spell check | language_tool_python | pyspellchecker | No grammar rules; only word lists; won't catch pt-BR morphological errors |
| Metadata | pikepdf | exiftool subprocess | Requires Perl on Windows; pikepdf is pure Python + QPDF |
| Signatures | pyHanko | Manual OpenSSL | Brittle subprocess; pyHanko implements AdES properly |
| Crypto low-level | cryptography | pyOpenSSL | PyCA recommends `cryptography` directly; pyOpenSSL is a thin wrapper being deprecated for new code |
| Reports | stdlib json + strings | Jinja2 | Unnecessary dependency for MVP simple templates |

---

## Confidence Assessment

| Component | Confidence | Basis |
|-----------|------------|-------|
| PyMuPDF 1.27.2.2 | HIGH | PyPI verified March 2026 |
| pdfplumber 0.11.9 | HIGH | PyPI verified |
| pikepdf 10.5.1 | HIGH | PyPI verified March 2026 |
| pytesseract 0.3.13 | HIGH | PyPI verified August 2024 (no update — stable wrapper) |
| pyHanko 0.34.1 | HIGH | PyPI verified March 2026 |
| ICP-Brasil CRL validation via pyHanko | MEDIUM | Confirmed CRL/OCSP support from docs; ICP-Brasil root has no OCSP — CRL only. No tested Brazilian example found. |
| opencv-python 4.13.0.92 | HIGH | PyPI verified February 2026 |
| ELA fraud detection efficacy | LOW | Research-grade method; high false positive rate; no validated benchmark on Brazilian legal documents |
| spaCy pt_core_news_lg 3.7.0 | HIGH | HuggingFace verified; F1=90.31% NER |
| spaCy extracting CPF/CNPJ natively | HIGH (negative) | Confirmed: pt_core_news_lg has 4 entity types only — CPF/CNPJ/CREA require regex |
| openai SDK 2.30.0 | HIGH | PyPI verified March 2026 |
| GPT-4o semantic analysis quality | MEDIUM | Strong for Portuguese text; no specific benchmark on ART/Atestado CREA domain |
| language_tool_python 3.3.0 | HIGH | PyPI verified March 2026 |
| Java runtime requirement for LanguageTool | HIGH | language_tool_python downloads LanguageTool JAR — requires JRE |

---

## Sources

- [PyMuPDF on PyPI](https://pypi.org/project/PyMuPDF/) — version 1.27.2.2, Mar 2026
- [pdfplumber on PyPI](https://pypi.org/project/pdfplumber/) — version 0.11.9, Jan 2026
- [pikepdf on PyPI](https://pypi.org/project/pikepdf/) — version 10.5.1, Mar 2026
- [pikepdf Metadata Docs](https://pikepdf.readthedocs.io/en/latest/topics/metadata.html)
- [pytesseract on PyPI](https://pypi.org/project/pytesseract/) — version 0.3.13
- [pyHanko on PyPI](https://pypi.org/project/pyHanko/) — version 0.34.1, Mar 2026
- [pyHanko Validation Docs](https://docs.pyhanko.eu/en/latest/lib-guide/validation.html)
- [pyhanko-certvalidator on PyPI](https://pypi.org/project/pyhanko-certvalidator/)
- [ICP-Brasil CPS Root CA](https://acraiz.icpbrasil.gov.br/cpsrootca.pdf) — CRL policy (6hr max)
- [opencv-python on PyPI](https://pypi.org/project/opencv-python/) — version 4.13.0.92, Feb 2026
- [spaCy Portuguese Models](https://spacy.io/models/pt)
- [spaCy pt_core_news_lg on HuggingFace](https://huggingface.co/spacy/pt_core_news_lg) — version 3.7.0, NER F1=90.31%
- [openai SDK on PyPI](https://pypi.org/project/openai/) — version 2.30.0, Mar 2026
- [language_tool_python on PyPI](https://pypi.org/project/language_tool_python/) — version 3.3.0, Mar 2026
- [PyMuPDF vs pdfplumber 2025 comparison (DEV Community)](https://dev.to/onlyoneaman/i-tested-7-python-pdf-extractors-so-you-dont-have-to-2025-edition-akm)
- [PaddleOCR vs Tesseract comparison 2025 (CodeSOTA)](https://www.codesota.com/ocr/paddleocr-vs-tesseract)
- [pyOpenSSL 26.0.0 docs](https://www.pyopenssl.org/en/stable/api/crypto.html)
