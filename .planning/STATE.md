---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Checkpoint — awaiting human verification
stopped_at: Phase 07 Plan 03 Task 1 complete — main.py wired with verdict + report (4 integration tests passing). Task 2 checkpoint:human-verify pending.
last_updated: "2026-03-29T07:10:00.000Z"
progress:
  total_phases: 7
  completed_phases: 6
  total_plans: 15
  completed_plans: 14
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-28)

**Core value:** Cruzamento preciso entre Atestado, ART e documentos complementares com detecção de inconsistências e fraudes, gerando parecer confiável no formato real do CREA.
**Current focus:** Phase 07 — verdict-exigencias-report

## Current Position

Phase: 07 (verdict-exigencias-report) — EXECUTING
Plan: 3 of 3 (checkpoint:human-verify)

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

*Note: Phase 1 anterior (stack overengineered) completada mas invalidada pelo pivot de stack*

## Accumulated Context

### Decisions

- Init: OpenAI GPT-4.1 como motor principal (usuário tem chave OpenAI, não tem Anthropic)
- Init: Pipeline local sem servidor (Windows 11, no Docker)
- Pivot (2026-03-28): Stack simplificada — GPT-4.1 Vision substitui Tesseract, spaCy, LanguageTool, OpenCV
- Pivot (2026-03-28): Apenas 5 dependências core: openai, pymupdf, pikepdf, pyHanko, Pillow
- Pivot (2026-03-28): ELA e análise visual forense deferidos para V1
- Carried: RNP e CREA tratados como identificadores equivalentes
- Carried: Datas da ART definem INTERVALO
- Carried: Exigências no formato CREA maiúsculo com base legal
- [Phase 01-environment-setup]: Stack simplificada: 5 deps (openai, pymupdf, pikepdf, pyhanko, Pillow) instaladas cleanly no Python 3.13 Windows 11
- [Phase 01-environment-setup]: config.py com OPENAI_MODEL=gpt-4.1 e thresholds de scoring/pesos editáveis sem tocar no pipeline
- [Phase 02-document-ingestion-classification]: ingestion.py: Responses API (text_format=Pydantic) over chat.completions for structured GPT output
- [Phase 02-document-ingestion-classification]: ingestion.py: First page only for classification — sufficient for all 5 test docs, avoids memory spike on 32-page docs
- [Phase 02-document-ingestion-classification]: ingestion.py: TipoDocumento as str Enum — allows direct comparison with GPT response string values
- [Phase 02-document-ingestion-classification]: main.py imports only crea_cat_ai.ingestion — avoids import errors from stub modules in future phases
- [Phase 03-document-analysis-entity-extraction]: analysis.py: Single GPT call per document covers entities + visual + spell-check — reduces cost and maintains context coherence
- [Phase 03-document-analysis-entity-extraction]: analysis.py: normalizar_crea_rnp strips all non-digits — handles 1120893194MA, CREA MA 1015902979, 4388D/GO variants
- [Phase 03-document-analysis-entity-extraction]: analysis.py: detail:high for all analysis images — detail:low misses signature text and timbre (ANAL-04/05)
- [Phase 03-document-analysis-entity-extraction]: analysis.py: page selection sends first+last for docs >3 pages — prevents 32-page token spike on saude indigena.pdf
- [Phase 03]: pytest.ini addopts = -m 'not integration' — integration tests excluded from default runs to prevent 401 failures without API key
- [Phase 03]: main.py: resultados_analise serialized via model_dump() in return dict
- [Phase 04-metadata-digital-signature]: _parse_pdf_date uses full string strptime (no slice) — PDF timezone offset adds chars, slicing broke tz parsing
- [Phase 04]: strict=False in PdfFileReader — Gov-Br PDFs are hybrid-reference and fail with strict=True
- [Phase 04]: KeyUsageConstraints(digital_signature) — Gov-Br certs lack non_repudiation, pyHanko default rejects them
- [Phase 04]: moment=self_reported_timestamp — validates expired certs that were valid at signing time (saude indigena.pdf Sig1)
- [Phase 04]: No anomalias field in ResultadoAssinatura — SIGN-03: absence of digital signature is a valid state
- [Phase 04-metadata-digital-signature]: processar_documento() is the canonical public API for main.py — wraps extrair_metadados + detectar_anomalias
- [Phase 04]: validate_pdf_signature requires file handle open: moved entire sig loop inside with-block
- [Phase 05-01]: Three-layer matching: exact local (identifiers) + local (dates) + single GPT batch (fuzzy/semantic)
- [Phase 05-01]: StatusCampo as str Enum — direct JSON serialization, consistent with TipoDocumento pattern from ingestion.py
- [Phase 05-01]: Missing/malformed dates → AUSENTE not DIVERGENTE (absence is not fraud per D-08)
- [Phase 05-02]: TipoDocumento.ART.value used as dict key to look up resultados_analise from analysis.analisar_pacote()
- [Phase 05-02]: resultado_cruzamento=None when ART/Atestado absent — distinguishes not-run from ran-with-no-results
- [Phase 05-02]: Integration tests skip (not fail) when PDFs/Par2 dir absent — correct CI behavior without test documents
- [Phase 06-complementary-docs-compliance]: Exigencia texto PAR. 1 uppercase (not par. 1) to match CREA all-caps declarative format
- [Phase 06-complementary-docs-compliance]: _verificacoes_1160_overrides returns empty list — Res. 1.160/2025 text not available in PDF provided
- [Phase 06-complementary-docs-compliance]: Auto-approved Task 2 checkpoint (auto_advance=true) — pipeline wired correctly, unit tests pass
- [Phase 07-01-verdict]: Compliance items use peso=0.0 — they generate exigencias already; adding to weighted average would double-penalize
- [Phase 07-01-verdict]: Single PENALIDADE_METADATA_SUSPEITO applied per analysis run (break after first anomalous doc)
- [Phase 07-01-verdict]: KNOCKOUT_CAP_CRITICO=0.49 (CPF/CNPJ/CREA), KNOCKOUT_CAP_EMPRESA=0.79 (empresa divergente)
- [Phase 07-02-report]: Pydantic model_dump() for Cruzamento/Compliance; manual dict for MetadadosPDF/ResultadoAssinatura dataclasses
- [Phase 07-02-report]: json.dumps default=str handles datetime/Path without custom encoder; ensure_ascii=False for utf-8 pt-BR text
- [Phase 07-02-report]: Exigencias section omitted when empty — cleaner ADERENTE reports; section guard in markdown generator
- [Phase 07-03-integration]: D-20 guard in main.py: early return when ART or Atestado absent prevents verdict generation on incomplete pars
- [Phase 07-03-integration]: Multi-par __main__ block iterates INPUT_DIR subdirectories automatically (D-19)
- [Phase 07-03-integration]: Return dict simplified to veredito/score/exigencias/relatorio_paths — removed redundant intermediate data

### Blockers/Concerns

- Phase 4: ICP-Brasil root CA não está no trust store padrão do pyHanko — precisa bundlear certificados ITI
- Phase 5: Divergência de empresa conhecida no Par 2 ("AR CLIMA" vs "HIDRO-CLIMA") deve ser detectada

## Session Continuity

Last session: 2026-03-29T07:10:00.000Z
Stopped at: Phase 07 Plan 03 Task 1 complete — checkpoint:human-verify reached for real pipeline run
Resume file: None
