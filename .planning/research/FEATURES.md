# Feature Landscape

**Domain:** Document verification / fraud detection / regulatory compliance (CREA CAT)
**Project:** CREA CAT AI — automated analysis of ART + Atestado pairs
**Researched:** 2026-03-28
**Confidence:** HIGH (based on project requirements + domain research + IDP ecosystem analysis)

---

## Table Stakes

Features users (CREA analysts) expect. Missing = pipeline feels incomplete or unreliable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Text extraction from PDFs (native) | All documents are PDFs; without text there is nothing to analyze | Low | PyMuPDF / pdfplumber handle this; native text is always more accurate than OCR |
| OCR fallback for scanned/image PDFs | Many atestados are scanned; pure OCR path is mandatory | Medium | Tesseract 5 with Portuguese language pack; quality heavily affects downstream accuracy |
| Named entity extraction (CPF, CNPJ, CREA, names, dates) | Verification is impossible without extracted fields | Medium | spaCy pt_core_news_lg is insufficient for CPF/CNPJ — must add regex-based extractors on top of it (spaCy won't recognize these natively) |
| Cross-document field matching (Atestado vs ART) | Core value proposition; without this it's just an OCR tool | High | Every field in Anexo IV must be paired and compared; fuzzy matching required for name/address variants |
| Regulatory checklist (Anexo IV, Res. 1.137/2023) | Legal requirement; defines what a valid atestado must contain | Medium | Hard-coded rules derived from official regulation text |
| Verdict output (ADERENTE / PENDENTE / SUSPEITO) | Analysts need a clear, actionable conclusion | Low | Logic layer on top of all checks; confidence score (0.0–1.0) required alongside verdict |
| Structured report output (JSON + Markdown) | Reports must be archivable and human-readable | Low | JSON for programmatic consumption; Markdown for analyst review |
| List of exigências (deficiencies) when PENDENTE | Analysts cannot act on a bare "PENDENTE" verdict; they need to know what is missing | Medium | Must produce per-field failure reasons mapped to regulation text |
| PDF metadata extraction | Hidden in every PDF; creation/modification software reveals tampering | Low | pikepdf or PyPDF2 extract this; flag mismatch between claimed and actual creation date |
| Error Level Analysis (ELA) on embedded images | Detects re-compressed image patches indicating local edits to stamp/signature areas | High | JPEG re-save + difference analysis; useful for detecting date/value swaps in scanned docs |
| Human-readable confidence reasoning | Analysts are legally responsible; they must understand WHY the AI raised a flag | Medium | Explain each deduction: "CPF on atestado (123.456.789-00) does not match ART (123.456.780-00)" |

---

## Differentiators

Features that set this pipeline apart from a simple OCR dump. Not strictly required by any spec, but materially increase reliability and analyst confidence.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Semantic scope comparison via LLM (GPT-4o) | Object/escopo of service described in different words in ART vs Atestado is the hardest mismatch to detect with regex; LLM resolves "construção de rede elétrica" vs "instalação de sistema de distribuição de energia" | High | GPT-4o prompt: compare escopo field A vs field B, return MATCH / PARTIAL / MISMATCH + justification |
| ICP-Brasil digital signature validation (pyHanko) | A cryptographically valid ICP-Brasil signature is the strongest fraud deterrent available; if present and valid, confidence score increases significantly | High | pyHanko validates PAdES B-B through B-LTA profiles; must load Brazilian ITI root chain; absence of signature is NOT a fraud flag — most atestados are not digitally signed |
| Visual signature copy-paste detection (OpenCV) | Signatures copy-pasted from another document leave distinctive compression artifacts; ORB + RANSAC detects region duplication | High | Fragile with low-quality scans; should be LOW confidence signal only, not a hard SUSPEITO trigger |
| Orthographic quality check (LanguageTool) | Atestados with many spelling errors are a weak fraud signal; more usefully, catches documents that were OCR'd with systematic errors or machine-generated | Medium | Must run on Portuguese (pt-BR); flag systemic errors (>5% token error rate) not isolated typos |
| Document type classification | Before analysis, confirm the document is actually an atestado or ART, not an NF, contrato, or procuração submitted by mistake | Medium | Few-shot LLM prompt or regex pattern matching on structural features |
| Timbre (letterhead) presence detection | Res. 1.137/2023 Anexo IV requires PJ atestados on letterhead; absence is a mandatory compliance flag | Medium | Image-based: check top margin of page 1 for non-white content; low false-negative acceptable since it's a soft flag |
| Subcontratação document check | When escopo mentions subcontracted services, the regulation requires additional documents; the pipeline should detect the mention and flag for completeness | Medium | LLM extraction of subcontratação language from escopo text |
| Res. 1.160/2025 delta check | The March 2026 regulation changes are now in effect; any analysis must apply the updated rules and flag fields that changed | Medium | Rule layer version-controlled; requires manual input of the delta from the new resolution |
| Confidence score with per-check breakdown | Analysts can see not just the final score but which checks contributed how much | Low | Weighted average of individual check scores; easy to implement once checks exist |

---

## Anti-Features

Features to deliberately NOT build in this project. Each has a clear reason and alternative.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| External CNPJ validation via Receita Federal API | Adds network dependency, rate limits, privacy concerns, and is not required by the regulation — the rule is that CNPJ must match BETWEEN documents, not that it must be federally active | Validate only that CNPJ on atestado equals CNPJ on ART (string/format match) |
| ML model trained for fraud classification | Requires labeled fraud dataset that doesn't exist; false confidence in a model trained on synthetic data is dangerous in a legal-weight context | Use deterministic rules + LLM for semantic checks; flag anomalies, not fraud class |
| Continuous learning / feedback loop | Requires volume, labeling pipeline, model governance, and versioning infrastructure | Log verdicts to JSON files for future manual review; revisit after 100+ real cases |
| Professional risk scoring (historical data) | Requires access to CREA's SITAC database and professional history — not available | Flag document-level inconsistencies only; never infer intent or pattern behavior |
| Web UI / dashboard | Out of scope per PROJECT.md; adds substantial complexity with zero verification value for MVP | CLI output + Markdown reports are sufficient for analyst workflow |
| Real-time processing queue / async workers | Two test pairs don't justify the complexity; premature optimization | Sequential processing in a single Python process |
| Docker / deployment infra | Runs locally on analyst's Windows 11 machine; container adds complexity with no benefit | Virtual environment + requirements.txt |
| Cloud storage of documents | Documents are sensitive professional credentials; any cloud sync creates data governance issues | Process entirely in-memory; no files written except the report outputs |
| Biometric or face verification | Not applicable — atestados don't contain photos | N/A |
| Email/notification alerts | No user management layer exists | N/A |
| Multi-language support | All documents are in Brazilian Portuguese | Configure everything for pt-BR from the start; don't generalize |
| Automatic CREA number validation against national registry | Registry lookup not available offline; adds external dependency | Extract CREA number, validate format (e.g., 1234567890/SP), flag malformed values |

---

## Feature Dependencies

Dependencies must be resolved in build order. A feature that depends on another cannot be built first.

```
PDF ingestion (native text + OCR fallback)
  -> Document type classification
    -> Entity extraction (CPF, CNPJ, CREA, names, dates, values)
      -> Cross-document field matching (Atestado x ART)
        -> Regulatory checklist (Anexo IV)
          -> Verdict logic (ADERENTE / PENDENTE / SUSPEITO)
            -> Exigências list
              -> Report generation (JSON + Markdown)

PDF ingestion
  -> PDF metadata extraction
    -> Metadata anomaly detection (contributes to SUSPEITO)

PDF ingestion
  -> Image extraction from PDF
    -> ELA analysis
      -> Visual anomaly detection (contributes to SUSPEITO)
    -> Timbre detection
      -> Regulatory check (contributes to PENDENTE if missing)
    -> Visual signature detection (OpenCV)
      -> Signature anomaly detection (contributes to SUSPEITO)

Entity extraction
  -> Semantic scope comparison (GPT-4o)
    -> Scope match result (contributes to cross-document match)

ICP-Brasil signature detection (independent of OCR path)
  -> pyHanko validation
    -> Signature validity flag (contributes to confidence score)

All checks aggregate ->
  -> Confidence score (0.0 to 1.0) with per-check breakdown
  -> Verdict (ADERENTE / PENDENTE / SUSPEITO)
```

---

## MVP Recommendation

### Prioritize (must have for MVP)

1. **Native PDF text extraction + OCR fallback** — foundation for all analysis; without this nothing works
2. **Entity extraction** (regex for CPF/CNPJ/CREA + spaCy for names/dates) — required for cross-document matching
3. **Cross-document field matching (Atestado x ART)** — the core value proposition; this IS the product
4. **Regulatory checklist (Anexo IV)** — hard-coded rules; deterministic and testable
5. **PDF metadata extraction + anomaly detection** — low implementation effort, high fraud signal value
6. **Verdict logic + confidence score** — required to produce output the analyst can act on
7. **Report generation (JSON + Markdown)** — required for any usefulness beyond console output
8. **Exigências list for PENDENTE verdicts** — without this, PENDENTE is not actionable

### Second tier (high value, implement after core works)

9. **Semantic scope comparison via GPT-4o** — handles the hardest matching problem; needs entity extraction first
10. **ELA analysis on embedded images** — fraud detection signal; needs image extraction working
11. **ICP-Brasil digital signature validation** — strong confidence signal when signature is present; complex to set up (Brazilian ITI certificate chain)
12. **Timbre presence detection** — low effort image check; regulatory requirement for PJ atestados

### Defer until post-validation

13. **Visual signature copy-paste detection** — high complexity, fragile on scanned docs, LOW confidence signal
14. **Orthographic quality check** — nice-to-have signal; LanguageTool integration adds complexity
15. **Document type classification** — useful guardrail but not critical for 2-pair test
16. **Res. 1.160/2025 delta** — implement once core Res. 1.137/2023 rules are working; add the delta on top

---

## Confidence Assessment by Area

| Feature Area | Confidence | Rationale |
|--------------|------------|-----------|
| Cross-document matching | HIGH | Well-understood field extraction + comparison; deterministic logic |
| OCR + NER pipeline | MEDIUM | spaCy pt_core_news_lg requires supplementation with regex for CPF/CNPJ; accuracy depends on scan quality |
| ELA fraud detection | MEDIUM | Technique is established; effectiveness on PDF-embedded images (vs raw photos) is lower |
| ICP-Brasil signature validation | MEDIUM | pyHanko supports PAdES; Brazilian ITI certificate chain setup is non-trivial and under-documented |
| Visual signature forgery detection | LOW | OpenCV ORB+RANSAC works in ideal conditions; fragile on low-quality atestado scans |
| Regulatory checklist (Anexo IV) | HIGH | Regulation text is publicly available; rules are deterministic |
| Report generation | HIGH | Straightforward JSON + Markdown; no external dependencies |
| LLM semantic comparison | HIGH | GPT-4o is highly capable for Brazilian Portuguese scope comparison |

---

## Sources

- ELA technique and PDF forensics: [TrustDocHub — ELA for image manipulation detection](https://trustdochub.com/en/error-level-analysis-image/) and [Veryfi — AI in AML PDF fraud detection](https://www.veryfi.com/security/ai-in-aml-pdf-fraud-detection/)
- ICP-Brasil and pyHanko: [pyHanko GitHub](https://github.com/MatthiasValvekens/pyHanko) and [pyHanko validation docs](https://docs.pyhanko.eu/en/latest/lib-guide/validation.html)
- spaCy Portuguese NER: [spaCy Portuguese models](https://spacy.io/models/pt)
- Cross-document validation / fuzzy matching: [V7 Labs — AI document validation agent](https://www.v7labs.com/agents/documentation-verification-agent)
- Compliance automation patterns: [Turian — AI for regulatory compliance](https://www.turian.ai/blog/ai-for-regulatory-compliance-what-to-know)
- Document fraud landscape 2025: [Klippa — document fraud detection](https://www.klippa.com/en/blog/information/document-fraud/) and [Docupilot — signature forgery guide](https://www.docupilot.com/blog/signature-forgery)
- IDP accuracy and pitfalls: [ABBYY — Intelligent Document Processing](https://www.abbyy.com/blog/intelligent-document-processing/)
- CREA CAT regulation: [CONFEA — CAT overview](https://www.confea.org.br/servicos-prestados/certidao-de-acervo-tecnico-cat) and [Crea-SP — Acervo Técnico](https://www.creasp.org.br/servico/acervo-tecnico-cat/)
- PDF forensics tools: [SANS — PDF Forensics and Authenticity Detection](https://www.sans.org/presentations/pdf-forensics-and-authenticity-detection)
