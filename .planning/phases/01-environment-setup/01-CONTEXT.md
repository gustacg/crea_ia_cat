# Phase 1: Environment Setup - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Instalar as 5 dependências core (openai, pymupdf, pikepdf, pyHanko, Pillow), criar config.py com thresholds do pipeline, setup_check.py que valida tudo, e estrutura do projeto crea_cat_ai/ com módulos placeholder.

**Stack simplificada:** GPT-4.1 Vision faz 80% do trabalho. Só 5 pacotes Python.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

Todas as decisões técnicas delegadas ao Claude pelo usuário.

- **D-01: Stack core** — Apenas 5 dependências: openai, pymupdf>=1.27.0, pikepdf>=10.0, pyHanko>=0.34, Pillow. Nada mais.
- **D-02: Modelo OpenAI** — GPT-4.1 como modelo padrão. Configurável em config.py.
- **D-03: Estrutura do projeto** — Pacote `crea_cat_ai/` com módulos flat (não subpacotes): ingestion.py, analysis.py, metadata.py, signature.py, matching.py, compliance.py, verdict.py, report.py
- **D-04: Configuração** — `config.py` com constantes Python. Thresholds de scoring, paths, modelo OpenAI.
- **D-05: Setup check** — `setup_check.py` verifica: OpenAI API key funcional, PyMuPDF importável, pikepdf importável, pyHanko importável, Pillow importável. Output em português.
- **D-06: Sem binários externos** — Diferente da stack antiga, NÃO precisa de Tesseract, Poppler, Java. Tudo é `pip install`.
- **D-07: Documentos de teste** — Em `Documentos que crea recebe/` no root. Path com espaços e acentos — usar pathlib.

</decisions>

<canonical_refs>
## Canonical References

### Project Specs
- `.planning/PROJECT.md` — Projeto, constraints, regras de negócio
- `.planning/REQUIREMENTS.md` — SETUP-01, SETUP-02, SETUP-03
- `.planning/ROADMAP.md` — Phase 1 success criteria
- `CLAUDE.md` — Technology stack simplificada com rationale

### Test Documents
- `Documentos que crea recebe/` — 5 PDFs reais do CREA-MA

</canonical_refs>

<code_context>
## Existing Code Insights

Nenhum código existe — ponto zero após cleanup da stack antiga.

</code_context>

<specifics>
## Specific Ideas

- Sem binários externos = setup muito mais simples
- `pip install -r requirements.txt` e pronto
- Mensagens de setup_check.py em português (pt-BR)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-environment-setup*
*Context gathered: 2026-03-28*
