# Phase 7: Verdict, Exigencias & Report - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Calcular score de confianca (0.0-1.0), gerar veredito ADERENTE/PENDENTE/SUSPEITO, formatar exigencias no formato CREA, produzir relatorios JSON + Markdown em output/, e validar pipeline end-to-end nos 2 pares reais de teste.

</domain>

<decisions>
## Implementation Decisions

### Algoritmo de Scoring
- **D-01:** Score calculado como media ponderada dos campos comparados, usando PESO_* de config.py. Para cada campo: MATCH=1.0, DIVERGENTE=0.0, AUSENTE=0.5 (ausencia nao e fraude). Score final = soma(peso_i * score_i) / soma(peso_i)
- **D-02:** Regras de knock-out (override da media ponderada):
  - CPF ou CNPJ DIVERGENTE → score maximo 0.49 (forca SUSPEITO)
  - CREA/RNP DIVERGENTE → score maximo 0.49 (forca SUSPEITO)
  - Empresa executora DIVERGENTE → score maximo 0.79 (nunca ADERENTE)
  - Metadados com anomalia de software suspeito → penalidade -0.15 no score
  - Declaracao obrigatoria ausente → penalidade -0.20 no score
- **D-03:** Thresholds ja definidos em config.py: ADERENTE >=0.80, PENDENTE >=0.50, SUSPEITO <0.50
- **D-04:** Par 2 (empresa divergente "AR CLIMA" vs "HIDRO-CLIMA") DEVE produzir PENDENTE ou SUSPEITO, nunca ADERENTE — validado pelo knock-out D-02

### Status dos Itens Verificados
- **D-05:** Cada campo analisado recebe status final: OK (match ou conforme), DIVERGENTE (valores diferentes), AUSENTE (campo nao encontrado), SUSPEITO (anomalia de fraude detectada)
- **D-06:** Fontes dos itens: cruzamento (Phase 5 — ComparacaoCampo), compliance (Phase 6 — VerificacaoItem), metadados (Phase 4 — anomalias), assinatura digital (Phase 4 — validacao)
- **D-07:** Consolidar todos os itens em uma lista unica `ItemVerificado` com: campo, status, valor_encontrado, valor_esperado, detalhes, peso

### Geracao de Exigencias
- **D-08:** Uma exigencia por nao-conformidade detectada. Formato CREA: frase declarativa em MAIUSCULAS com base legal
- **D-09:** Exigencias da Phase 6 (compliance.exigencias) sao reutilizadas diretamente — ja estao no formato correto
- **D-10:** Novas exigencias geradas para divergencias do cruzamento:
  - CPF divergente: "VERIFICAR DIVERGENCIA DE CPF ENTRE ART E ATESTADO — CPF DA ART: {x}, CPF DO ATESTADO: {y}"
  - Empresa divergente: "VERIFICAR DIVERGENCIA DE EMPRESA EXECUTORA ENTRE ART E ATESTADO — ART: {x}, ATESTADO: {y}"
  - Escopo divergente: "VERIFICAR COMPATIBILIDADE DO OBJETO/ESCOPO DO SERVICO ENTRE ART E ATESTADO"
  - Datas fora do intervalo: "VERIFICAR PERIODO DE EXECUCAO — DATAS DO ATESTADO NAO ESTAO DENTRO DO INTERVALO DA ART"
- **D-11:** Exigencias nao tem base legal quando sao divergencias de cruzamento (nao ha artigo especifico). Exigencias de compliance ja incluem base legal (Art. 59, Anexo IV, etc.)

### Relatorio Markdown
- **D-12:** Estrutura do relatorio Markdown:
  1. Cabecalho com dados do par (ART numero, profissional, contratante)
  2. Veredito em destaque (ADERENTE/PENDENTE/SUSPEITO + score)
  3. Resumo executivo (2-3 frases sobre o resultado)
  4. Tabela de itens verificados (campo | status | detalhe)
  5. Secao de exigencias (lista numerada)
  6. Detalhes por area: cruzamento, compliance, metadados, assinatura digital
  7. Rodape: "Parecer gerado automaticamente — decisao final do analista humano do CREA"
- **D-13:** Quando PENDENTE, incluir recomendacao ao analista sobre quais itens merecem atencao
- **D-14:** Relatorio em portugues (pt-BR), sem acentos nos nomes de arquivo

### Relatorio JSON
- **D-15:** JSON aninhado por secao:
  ```json
  {
    "veredito": "ADERENTE|PENDENTE|SUSPEITO",
    "score": 0.85,
    "par": { "art": "...", "atestado": "...", "profissional": "..." },
    "itens_verificados": [...],
    "exigencias": [...],
    "cruzamento": { ... },
    "compliance": { ... },
    "metadados": { ... },
    "assinatura_digital": { ... },
    "gerado_em": "2026-03-29T...",
    "versao": "1.0"
  }
  ```
- **D-16:** JSON usa model_dump() dos Pydantic models existentes para cruzamento e compliance. Metadados e assinatura serializados manualmente (ja feito em main.py)

### Pipeline End-to-End
- **D-17:** main.py wire: substituir placeholder Phase 7 por chamadas a verdict.py e report.py
- **D-18:** Output em output/{par_name}/ com: relatorio.json e relatorio.md
- **D-19:** main.py processa cada par de teste separadamente (Par 1 e Par 2)
- **D-20:** Se ART ou Atestado ausente, nao gerar veredito — reportar como erro

### Claude's Discretion
- Implementacao interna do calculo de media ponderada
- Como formatar o resumo executivo no Markdown (frases exatas)
- Nomes internos dos Pydantic models (Veredito, ItemVerificado, RelatorioCAT, etc.)
- Se usar Enum ou Literal para o tipo de veredito
- Organizacao de funcoes dentro de verdict.py e report.py

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core Implementation References
- `crea_cat_ai/verdict.py` — Stub file for verdict/scoring implementation
- `crea_cat_ai/report.py` — Stub file for report generation
- `crea_cat_ai/matching.py` — Defines `ResultadoCruzamento`, `ComparacaoCampo`, `StatusCampo` (MATCH/DIVERGENTE/AUSENTE) — input data for scoring
- `crea_cat_ai/compliance.py` — Defines `ResultadoCompliance`, `VerificacaoItem`, `StatusCompliance` (CONFORME/NAO_CONFORME/NAO_APLICAVEL), `exigencias` list — input data for scoring and exigencias
- `crea_cat_ai/metadata.py` — Defines `ResultadoMetadados` with `anomalias` list — input for fraud flags
- `crea_cat_ai/signature.py` — Defines `ResultadoAssinatura` with `presente`, `signatarios` — input for verification items
- `crea_cat_ai/analysis.py` — Defines `ResultadoAnalise` with all entity fields — used for report header data
- `crea_cat_ai/ingestion.py` — Defines `PacoteDocumentos`, `TipoDocumento`
- `config.py` — PESO_* weights, SCORE_ADERENTE/SCORE_PENDENTE thresholds, OUTPUT_DIR
- `main.py` — Pipeline entry point, has Phase 7 placeholder at lines 158-161, return dict at 163-194

### Business Rules
- `.planning/PROJECT.md` section Context — Test pairs, known divergences, CREA format rules
- `.planning/STATE.md` section Decisions — All accumulated architectural decisions

### Prior Phase Context
- `.planning/phases/05-cross-document-matching/05-CONTEXT.md` — Matching patterns and decisions
- `.planning/phases/06-complementary-docs-compliance/06-CONTEXT.md` — Compliance patterns and exigencia format

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `matching.ResultadoCruzamento` — Has `comparacoes` (list[ComparacaoCampo]), `total_match`, `total_divergente`, `total_ausente`
- `matching.StatusCampo` — MATCH/DIVERGENTE/AUSENTE enum
- `compliance.ResultadoCompliance` — Has `verificacoes`, `exigencias`, `declaracao_necessaria/encontrada`, `anuencia_necessaria/encontrada`, `anexo_iv_completo`
- `compliance.StatusCompliance` — CONFORME/NAO_CONFORME/NAO_APLICAVEL enum
- `config.PESO_*` — 13 weight constants already defined
- `config.SCORE_ADERENTE/SCORE_PENDENTE` — Threshold constants
- `config.OUTPUT_DIR` — Path for output files
- `main.py` return dict — Already serializes all results, can be adapted for JSON report

### Established Patterns
- Pydantic models for all structured data (BaseModel, Field, Optional, str Enum)
- `model_dump()` for JSON serialization
- All logs/output in pt-BR
- `pathlib.Path` for all file paths
- Integration tests marked with `@pytest.mark.integration`

### Integration Points
- `main.py` lines 158-161: Phase 7 placeholder to replace
- `main.py` lines 163-194: Return dict to replace with verdict + report generation
- `config.OUTPUT_DIR` (PROJECT_ROOT / "output") for report files
- All Phase 4-6 results available as local variables in main.py main() function

</code_context>

<specifics>
## Specific Ideas

- Par 1 (Alexandre): Deve ser PENDENTE (Declaracao necessaria por Ruan ser Administrador, mas Declaracao encontrada e verificada — resultado depende do cruzamento)
- Par 2 (Nizo): Deve ser PENDENTE ou SUSPEITO (divergencia "AR CLIMA" vs "HIDRO-CLIMA" forca knock-out de empresa)
- Rodape do relatorio: "PARECER GERADO AUTOMATICAMENTE PELO SISTEMA CREA CAT AI — A DECISAO FINAL E DO ANALISTA HUMANO DO CREA"
- Exigencias da Phase 6 ja no formato correto — nao duplicar, apenas agregar

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-verdict-exigencias-report*
*Context gathered: 2026-03-29*
