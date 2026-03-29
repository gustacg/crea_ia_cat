# Phase 7: Verdict, Exigencias & Report - Research

**Researched:** 2026-03-29
**Domain:** Scoring algorithm, verdict generation, report writing (JSON + Markdown), pipeline wiring
**Confidence:** HIGH

## Summary

Phase 7 is the final integration phase of CREA CAT AI. Its scope is purely computational and structural — no new external libraries are needed. All inputs are already computed by Phases 2-6 and available as local variables in `main.py`. The work is: (1) implement `verdict.py` with weighted scoring + knock-out rules; (2) implement `report.py` with JSON and Markdown output; (3) wire both modules into `main.py` replacing the Phase 7 placeholder; (4) validate end-to-end on both real test pairs.

The scoring algorithm is fully specified in CONTEXT.md (D-01 through D-04) and uses only Python arithmetic — no GPT calls are required. Report generation uses the standard library `json` module and string formatting with `pathlib.Path`. All Pydantic models from previous phases already have `.model_dump()` support, so JSON serialization of those structures is trivial.

The critical correctness requirement is the knock-out logic: CPF/CNPJ/CREA divergence must cap score at 0.49 (SUSPEITO), and empresa divergence must cap at 0.79 (never ADERENTE). Par 2 ("AR CLIMA" vs "HIDRO-CLIMA") is the smoke test for this — it MUST produce PENDENTE or SUSPEITO.

**Primary recommendation:** Implement `calcular_veredito()` in `verdict.py` as a pure function with no external calls. Keep knock-out rules as explicit if-branches before returning, not mixed into the weighted average loop. Write `gerar_relatorio_json()` and `gerar_relatorio_markdown()` in `report.py` as separate, independently testable functions.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Algoritmo de Scoring**
- D-01: Score calculado como media ponderada dos campos comparados, usando PESO_* de config.py. Para cada campo: MATCH=1.0, DIVERGENTE=0.0, AUSENTE=0.5 (ausencia nao e fraude). Score final = soma(peso_i * score_i) / soma(peso_i)
- D-02: Regras de knock-out (override da media ponderada):
  - CPF ou CNPJ DIVERGENTE → score maximo 0.49 (forca SUSPEITO)
  - CREA/RNP DIVERGENTE → score maximo 0.49 (forca SUSPEITO)
  - Empresa executora DIVERGENTE → score maximo 0.79 (nunca ADERENTE)
  - Metadados com anomalia de software suspeito → penalidade -0.15 no score
  - Declaracao obrigatoria ausente → penalidade -0.20 no score
- D-03: Thresholds ja definidos em config.py: ADERENTE >=0.80, PENDENTE >=0.50, SUSPEITO <0.50
- D-04: Par 2 (empresa divergente "AR CLIMA" vs "HIDRO-CLIMA") DEVE produzir PENDENTE ou SUSPEITO, nunca ADERENTE — validado pelo knock-out D-02

**Status dos Itens Verificados**
- D-05: Cada campo analisado recebe status final: OK (match ou conforme), DIVERGENTE (valores diferentes), AUSENTE (campo nao encontrado), SUSPEITO (anomalia de fraude detectada)
- D-06: Fontes dos itens: cruzamento (Phase 5 — ComparacaoCampo), compliance (Phase 6 — VerificacaoItem), metadados (Phase 4 — anomalias), assinatura digital (Phase 4 — validacao)
- D-07: Consolidar todos os itens em uma lista unica `ItemVerificado` com: campo, status, valor_encontrado, valor_esperado, detalhes, peso

**Geracao de Exigencias**
- D-08: Uma exigencia por nao-conformidade detectada. Formato CREA: frase declarativa em MAIUSCULAS com base legal
- D-09: Exigencias da Phase 6 (compliance.exigencias) sao reutilizadas diretamente — ja estao no formato correto
- D-10: Novas exigencias geradas para divergencias do cruzamento:
  - CPF divergente: "VERIFICAR DIVERGENCIA DE CPF ENTRE ART E ATESTADO — CPF DA ART: {x}, CPF DO ATESTADO: {y}"
  - Empresa divergente: "VERIFICAR DIVERGENCIA DE EMPRESA EXECUTORA ENTRE ART E ATESTADO — ART: {x}, ATESTADO: {y}"
  - Escopo divergente: "VERIFICAR COMPATIBILIDADE DO OBJETO/ESCOPO DO SERVICO ENTRE ART E ATESTADO"
  - Datas fora do intervalo: "VERIFICAR PERIODO DE EXECUCAO — DATAS DO ATESTADO NAO ESTAO DENTRO DO INTERVALO DA ART"
- D-11: Exigencias nao tem base legal quando sao divergencias de cruzamento (nao ha artigo especifico). Exigencias de compliance ja incluem base legal (Art. 59, Anexo IV, etc.)

**Relatorio Markdown**
- D-12: Estrutura do relatorio Markdown:
  1. Cabecalho com dados do par (ART numero, profissional, contratante)
  2. Veredito em destaque (ADERENTE/PENDENTE/SUSPEITO + score)
  3. Resumo executivo (2-3 frases sobre o resultado)
  4. Tabela de itens verificados (campo | status | detalhe)
  5. Secao de exigencias (lista numerada)
  6. Detalhes por area: cruzamento, compliance, metadados, assinatura digital
  7. Rodape: "Parecer gerado automaticamente — decisao final do analista humano do CREA"
- D-13: Quando PENDENTE, incluir recomendacao ao analista sobre quais itens merecem atencao
- D-14: Relatorio em portugues (pt-BR), sem acentos nos nomes de arquivo

**Relatorio JSON**
- D-15: JSON aninhado por secao com campos: veredito, score, par, itens_verificados, exigencias, cruzamento, compliance, metadados, assinatura_digital, gerado_em, versao
- D-16: JSON usa model_dump() dos Pydantic models existentes para cruzamento e compliance. Metadados e assinatura serializados manualmente (ja feito em main.py)

**Pipeline End-to-End**
- D-17: main.py wire: substituir placeholder Phase 7 por chamadas a verdict.py e report.py
- D-18: Output em output/{par_name}/ com: relatorio.json e relatorio.md
- D-19: main.py processa cada par de teste separadamente (Par 1 e Par 2)
- D-20: Se ART ou Atestado ausente, nao gerar veredito — reportar como erro

### Claude's Discretion
- Implementacao interna do calculo de media ponderada
- Como formatar o resumo executivo no Markdown (frases exatas)
- Nomes internos dos Pydantic models (Veredito, ItemVerificado, RelatorioCAT, etc.)
- Se usar Enum ou Literal para o tipo de veredito
- Organizacao de funcoes dentro de verdict.py e report.py

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VERD-01 | Veredito ADERENTE/PENDENTE/SUSPEITO com score de confiança (0.0 a 1.0) | D-01 to D-04 define exact algorithm; config.py already has PESO_* and SCORE_* thresholds |
| VERD-02 | Lista de itens verificados com status (OK/DIVERGENTE/AUSENTE/SUSPEITO) | D-05 to D-07 define ItemVerificado structure; sources are matching.ComparacaoCampo + compliance.VerificacaoItem + metadata.anomalias |
| VERD-03 | Exigências automáticas no formato real do CREA (maiúsculas, base legal) | D-08 to D-11 define exact format strings; compliance.exigencias already formatted correctly |
| VERD-04 | Relatório estruturado em JSON | D-15/D-16: model_dump() for Pydantic models + manual serialization for dataclasses; standard library json module |
| VERD-05 | Relatório legível em Markdown | D-12/D-13/D-14: section structure and language rules fully defined |
| VERD-06 | Pipeline processa os 2 pares reais de teste e gera relatórios em output/ | D-17 to D-20: main.py wiring; output/{par_name}/relatorio.{json,md}; Par 2 must not be ADERENTE |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `json` | 3.13 built-in | JSON serialization and file writing | No new dependency needed; model_dump() produces dict, json.dumps() writes it |
| Python stdlib `pathlib` | 3.13 built-in | File path construction for output files | Established project convention — all existing code uses pathlib.Path |
| Python stdlib `datetime` | 3.13 built-in | gerado_em timestamp in reports | Already imported in metadata.py; stdlib only |
| pydantic `BaseModel` | already installed | Defining Veredito, ItemVerificado, RelatorioCAT models | Established project pattern — all structured data uses Pydantic |

### No New Dependencies
Phase 7 requires no new `pip install`. All calculation is Python arithmetic. All data structures are already in memory from prior phases. The `json` module writes files; `pathlib.Path` handles paths; `pydantic` defines new models. All are already present.

**Installation:** None required.

---

## Architecture Patterns

### Recommended Module Structure

**verdict.py** — pure computation, no I/O, no OpenAI calls:
```
verdict.py
├── StatusItem (str Enum)          # OK / DIVERGENTE / AUSENTE / SUSPEITO
├── TipoVeredito (str Enum)        # ADERENTE / PENDENTE / SUSPEITO
├── ItemVerificado (BaseModel)     # campo, status, valor_encontrado, valor_esperado, detalhes, peso
├── Veredito (BaseModel)           # tipo, score, itens_verificados, exigencias
├── _consolidar_itens()            # private: maps ComparacaoCampo + VerificacaoItem + anomalias → ItemVerificado list
├── _calcular_score()              # private: weighted average arithmetic
├── _aplicar_knockouts()           # private: cap/penalize based on D-02 rules
├── _gerar_exigencias_cruzamento() # private: generates CREA-format strings for matching divergences
└── calcular_veredito()            # PUBLIC API: all inputs → Veredito
```

**report.py** — I/O only, no computation:
```
report.py
├── RelatorioCAT (BaseModel)       # full report structure matching D-15 JSON schema
├── _resumo_executivo()            # private: generates 2-3 sentence executive summary
├── gerar_relatorio_json()         # writes output/{par_name}/relatorio.json
├── gerar_relatorio_markdown()     # writes output/{par_name}/relatorio.md
└── gerar_relatorios()             # PUBLIC API: calls both, ensures output dir exists
```

### Pattern 1: Weighted Average Scoring with Knock-outs

The scoring algorithm has two phases: (1) compute weighted average of all ComparacaoCampo items; (2) apply knock-out caps/penalties in order. The knock-outs are applied AFTER the average is computed — they override it.

```python
# Source: CONTEXT.md D-01, D-02; config.py PESO_* constants

CAMPO_PESOS = {
    "cpf_profissional":  config.PESO_CPF,
    "cnpj_contratante":  config.PESO_CNPJ,
    "crea_rnp":          config.PESO_CREA_RNP,
    "nome_profissional": config.PESO_NOME,
    "empresa_executora": config.PESO_EMPRESA,
    "endereco_obra":     config.PESO_ENDERECO,
    "intervalo_datas":   config.PESO_DATA,
    "escopo":            config.PESO_ESCOPO,
    "valor_contrato":    config.PESO_VALOR,
    "contrato_numero":   config.PESO_CONTRATO,
    # Plus visual fields from analysis
}

STATUS_SCORE = {
    "MATCH": 1.0,
    "CONFORME": 1.0,
    "OK": 1.0,
    "DIVERGENTE": 0.0,
    "NAO_CONFORME": 0.0,
    "AUSENTE": 0.5,
    "NAO_APLICAVEL": 0.5,  # treat as neutral
    "SUSPEITO": 0.0,
}

def _calcular_score(itens: list[ItemVerificado]) -> float:
    soma_pesos = sum(i.peso for i in itens if i.peso > 0)
    if soma_pesos == 0:
        return 1.0
    soma_ponderada = sum(
        STATUS_SCORE.get(i.status.value, 0.5) * i.peso
        for i in itens if i.peso > 0
    )
    return soma_ponderada / soma_pesos

def _aplicar_knockouts(score: float, itens: list[ItemVerificado]) -> float:
    # D-02: CPF/CREA/CNPJ divergente → cap 0.49
    campos_criticos = {"cpf_profissional", "crea_rnp", "cnpj_contratante"}
    for item in itens:
        if item.campo in campos_criticos and item.status == StatusItem.DIVERGENTE:
            score = min(score, 0.49)
    # D-02: empresa executora divergente → cap 0.79
    for item in itens:
        if item.campo == "empresa_executora" and item.status == StatusItem.DIVERGENTE:
            score = min(score, 0.79)
    # D-02: metadados suspeitos → -0.15
    # (handled via anomalias passed in as separate flag)
    return score
```

### Pattern 2: Consolidating Items from Multiple Sources (D-06, D-07)

Each phase produces differently typed results. The consolidation step maps them to the unified `ItemVerificado` type.

```python
# Source: CONTEXT.md D-06, D-07; matching.StatusCampo; compliance.StatusCompliance

def _consolidar_itens(
    resultado_cruzamento: ResultadoCruzamento | None,
    resultado_compliance: ResultadoCompliance,
    resultados_metadata: dict[str, MetadadosPDF],
    resultados_assinatura: dict[str, ResultadoAssinatura],
) -> list[ItemVerificado]:
    itens = []

    # Source 1: cruzamento (ComparacaoCampo → ItemVerificado)
    if resultado_cruzamento:
        for comp in resultado_cruzamento.comparacoes:
            peso = CAMPO_PESOS.get(comp.campo, 0.0)
            status = _mapear_status_campo(comp.status)  # MATCH→OK, DIVERGENTE→DIVERGENTE, AUSENTE→AUSENTE
            itens.append(ItemVerificado(
                campo=comp.campo,
                status=status,
                valor_encontrado=comp.valor_atestado,
                valor_esperado=comp.valor_art,
                detalhes=comp.detalhes,
                peso=peso,
            ))

    # Source 2: compliance (VerificacaoItem → ItemVerificado)
    for verif in resultado_compliance.verificacoes:
        status = _mapear_status_compliance(verif.status)  # CONFORME→OK, NAO_CONFORME→DIVERGENTE, NAO_APLICAVEL→AUSENTE
        itens.append(ItemVerificado(
            campo=verif.requisito,
            status=status,
            detalhes=verif.detalhes,
            peso=0.0,  # compliance items don't contribute to weighted average directly
        ))

    # Source 3: metadados anomalias
    for tipo, meta in resultados_metadata.items():
        for anomalia in meta.anomalias:
            itens.append(ItemVerificado(
                campo=f"metadata_{tipo}",
                status=StatusItem.SUSPEITO,
                detalhes=anomalia,
                peso=0.0,  # handled via penalty in _aplicar_knockouts
            ))

    # Source 4: assinatura digital
    for tipo, assin in resultados_assinatura.items():
        if assin.presente:
            for sig in assin.signatarios:
                status_sig = StatusItem.OK if "valida" in sig.get("sumario", "").lower() else StatusItem.SUSPEITO
                itens.append(ItemVerificado(
                    campo=f"assinatura_digital_{tipo}",
                    status=status_sig,
                    detalhes=sig.get("sumario") or sig.get("erro"),
                    peso=0.0,
                ))

    return itens
```

### Pattern 3: StatusItem Mapping Between Enums

Three existing status enums (StatusCampo, StatusCompliance, and a new StatusItem) must map cleanly. Use explicit dict maps, not string comparison.

```python
# StatusCampo (matching.py) → StatusItem (verdict.py)
_CAMPO_TO_ITEM = {
    "MATCH": StatusItem.OK,
    "DIVERGENTE": StatusItem.DIVERGENTE,
    "AUSENTE": StatusItem.AUSENTE,
}

# StatusCompliance (compliance.py) → StatusItem (verdict.py)
_COMPLIANCE_TO_ITEM = {
    "CONFORME": StatusItem.OK,
    "NAO_CONFORME": StatusItem.DIVERGENTE,
    "NAO_APLICAVEL": StatusItem.AUSENTE,
}
```

### Pattern 4: JSON Serialization of Mixed Types

`ResultadoCruzamento` and `ResultadoCompliance` are Pydantic models — use `.model_dump()`. `MetadadosPDF` and `ResultadoAssinatura` are dataclasses — serialize manually (same pattern already in `main.py` lines 173-194).

```python
# Source: main.py lines 163-194 (existing serialization pattern)
relatorio_dict = {
    "veredito": veredito.tipo.value,
    "score": round(veredito.score, 4),
    "par": {
        "art": pacote.art.caminho.name if pacote.art else None,
        "atestado": pacote.atestado.caminho.name if pacote.atestado else None,
        "profissional": profissional_nome,
    },
    "itens_verificados": [i.model_dump() for i in veredito.itens_verificados],
    "exigencias": veredito.exigencias,
    "cruzamento": resultado_cruzamento.model_dump() if resultado_cruzamento else None,
    "compliance": resultado_compliance.model_dump(),
    "metadados": {
        tipo: {
            "creator": m.creator,
            "producer": m.producer,
            "anomalias": m.anomalias,
        }
        for tipo, m in resultados_metadata.items()
    },
    "assinatura_digital": {
        tipo: {
            "presente": a.presente,
            "quantidade": a.quantidade,
            "signatarios": a.signatarios,
        }
        for tipo, a in resultados_assinatura.items()
    },
    "gerado_em": datetime.now().isoformat(),
    "versao": "1.0",
}
```

### Pattern 5: Markdown Report Generation

Use Python f-strings and multiline string concatenation. No Markdown library needed. The existing main.py uses plain `print()` with string formatting — same style applies to report building.

```python
# Source: CONTEXT.md D-12, D-14
def _gerar_markdown(
    veredito: Veredito,
    pacote: PacoteDocumentos,
    resultado_cruzamento: ResultadoCruzamento | None,
    resultado_compliance: ResultadoCompliance,
    profissional_nome: str | None,
    contratante_nome: str | None,
) -> str:
    linhas = []
    # 1. Cabecalho
    linhas.append(f"# PARECER CAT - {pacote.art.caminho.stem if pacote.art else 'SEM ART'}")
    linhas.append("")
    if profissional_nome:
        linhas.append(f"**Profissional:** {profissional_nome}")
    if contratante_nome:
        linhas.append(f"**Contratante:** {contratante_nome}")
    linhas.append("")

    # 2. Veredito em destaque
    linhas.append(f"## VEREDITO: {veredito.tipo.value}")
    linhas.append(f"**Score de confianca:** {veredito.score:.2f} / 1.00")
    linhas.append("")

    # 3. Resumo executivo
    linhas.append("## Resumo Executivo")
    linhas.append(_resumo_executivo(veredito))
    linhas.append("")

    # 4. Tabela de itens verificados
    linhas.append("## Itens Verificados")
    linhas.append("")
    linhas.append("| Campo | Status | Detalhe |")
    linhas.append("|-------|--------|---------|")
    for item in veredito.itens_verificados:
        detalhe = (item.detalhes or "")[:100]
        linhas.append(f"| {item.campo} | {item.status.value} | {detalhe} |")
    linhas.append("")

    # 5. Exigencias
    if veredito.exigencias:
        linhas.append("## Exigencias")
        linhas.append("")
        for i, exig in enumerate(veredito.exigencias, 1):
            linhas.append(f"{i}. {exig}")
        linhas.append("")

    # 6. (Detalhes por area - cruzamento, compliance, etc.)
    # ...

    # 7. Rodape (D-14, specifics section)
    linhas.append("---")
    linhas.append("")
    linhas.append("PARECER GERADO AUTOMATICAMENTE PELO SISTEMA CREA CAT AI — A DECISAO FINAL E DO ANALISTA HUMANO DO CREA")

    return "\n".join(linhas)
```

### Pattern 6: Output Directory Creation

```python
# Source: config.OUTPUT_DIR already defined in config.py
output_par_dir = config.OUTPUT_DIR / par_name
output_par_dir.mkdir(parents=True, exist_ok=True)

json_path = output_par_dir / "relatorio.json"
md_path = output_par_dir / "relatorio.md"

json_path.write_text(
    json.dumps(relatorio_dict, ensure_ascii=False, indent=2, default=str),
    encoding="utf-8",
)
md_path.write_text(markdown_content, encoding="utf-8")
```

Note: `default=str` in `json.dumps` handles any remaining non-serializable objects (datetime, Path, Enum values not already converted).

### Pattern 7: main.py Multi-Par Processing

The current `main.py` processes a single `input_dir`. For VERD-06, the plan must account for running both Par 1 and Par 2. Two approaches are acceptable per D-19:

**Option A:** Two separate `main()` calls from a top-level script:
```python
# In main.py __main__ block or a new run_pares.py
par1_dir = config.INPUT_DIR / "Par1"
par2_dir = config.INPUT_DIR / "Par2"
for par_dir in [par1_dir, par2_dir]:
    if par_dir.exists():
        main(par_dir)
```

**Option B:** `main()` takes optional `par_name` parameter for output subdirectory naming.

Currently the test documents all live in `Documentos que crea recebe/` (single flat directory). The integration tests use `conftest.PDF_DIR` which points there. For Par 2 to be tested, it likely requires a `Par2/` subdirectory or a second call with different document paths. The planner must decide how to handle this given the current flat structure.

### Anti-Patterns to Avoid

- **Calling GPT in verdict.py:** The scoring algorithm is pure arithmetic. No AI calls belong here.
- **Mixing I/O and computation in verdict.py:** `calcular_veredito()` should return a `Veredito` object; writing files belongs in `report.py`.
- **Duplicating compliance exigencias:** D-09 says to reuse `resultado_compliance.exigencias` directly. Do not regenerate them from `verificacoes`.
- **Using str concatenation instead of `json.dumps`:** Markdown is string concat, but JSON must use `json.dumps` with `ensure_ascii=False` to handle accented chars in document names/fields.
- **Forgetting `default=str` in json.dumps:** `datetime` objects from `MetadadosPDF.creation_date` are not JSON-serializable by default.
- **Hardcoding knock-out thresholds:** Use `config.SCORE_ADERENTE` and `config.SCORE_PENDENTE`. Knock-out caps (0.49, 0.79) are business rules not in config — document them as constants at module top.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON serialization | Custom recursive serializer | `json.dumps(..., default=str)` + `.model_dump()` | Pydantic already handles nested models; `default=str` catches edge cases |
| File encoding | Manual bytes manipulation | `.write_text(..., encoding="utf-8")` | pathlib handles encoding cleanly |
| Output directory creation | os.makedirs or try/except | `Path.mkdir(parents=True, exist_ok=True)` | Already used in project |
| Markdown table formatting | Custom table library | f-strings with `|` separators | No Markdown library needed for this format |

---

## Common Pitfalls

### Pitfall 1: Knock-out Order Matters
**What goes wrong:** Applying knock-outs before computing the weighted average can produce wrong scores if multiple knock-outs overlap.
**Why it happens:** Knock-outs are caps/penalties on the FINAL score — they must be applied after `_calcular_score()` finishes.
**How to avoid:** Always compute weighted average first, then iterate through knock-out rules in sequence. Each rule operates on the current score (after previous knock-outs).
**Warning signs:** Par 2 getting ADERENTE despite empresa_executora DIVERGENTE.

### Pitfall 2: Compliance Items With Zero Weight Inflate the Average
**What goes wrong:** VerificacaoItem entries (CDOC-01, COMP-01.x) don't map to PESO_* constants. If they're included in the weighted sum with nonzero weight, they distort the score.
**Why it happens:** The CAMPO_PESOS dict only covers the 13 matching/visual fields — compliance requisito IDs won't match.
**How to avoid:** Assign `peso=0.0` to all compliance-sourced ItemVerificado objects. Only cruzamento fields contribute to the weighted average. Compliance NAO_CONFORME items instead trigger the declaracao_ausente penalty (-0.20) via D-02.
**Warning signs:** Score calculation returning unexpected values when compliance checks are NAO_CONFORME.

### Pitfall 3: StatusCampo vs StatusItem Enum Confusion
**What goes wrong:** `StatusCampo.MATCH` from `matching.py` and `StatusItem.OK` from `verdict.py` are distinct objects. Comparing them directly (`item.status == StatusCampo.MATCH`) raises no error but returns False.
**Why it happens:** Python `str` Enums with different classes compare False even if their `.value` is the same string.
**How to avoid:** Always map StatusCampo → StatusItem via the explicit `_CAMPO_TO_ITEM` dict during consolidation. Never store raw StatusCampo in ItemVerificado.
**Warning signs:** All items showing AUSENTE despite matching data present.

### Pitfall 4: datetime Serialization in JSON
**What goes wrong:** `MetadadosPDF.creation_date` and `mod_date` are `datetime` objects. `json.dumps()` raises `TypeError: Object of type datetime is not JSON serializable`.
**Why it happens:** `main.py` already handles this via `str(m.creation_date)` in the return dict — but if `gerar_relatorio_json()` receives the raw dataclass, it may forget this conversion.
**How to avoid:** Use `json.dumps(..., default=str)` as the global fallback. This converts datetime, Path, and any remaining non-serializable objects to their string representation.
**Warning signs:** `TypeError` when writing the JSON report with metadata present.

### Pitfall 5: Par 2 Document Directory Structure
**What goes wrong:** The integration test for VERD-06 (Par 2 processing) may fail if there is no `Par2/` subdirectory under `Documentos que crea recebe/`.
**Why it happens:** Current conftest.py and main.py assume a flat single-par directory. Par 2 documents may be in a different location or not yet organized.
**How to avoid:** The integration test for Par 2 should use `pytest.skip()` if the Par 2 directory doesn't exist (consistent with existing pattern in `test_integration_phase5.py` and `test_integration_phase6.py`). The test should NOT fail — it should skip.
**Warning signs:** `FileNotFoundError` or assertion errors in Par 2 integration tests when run in CI without real documents.

### Pitfall 6: Markdown Special Characters in Table Cells
**What goes wrong:** Detail text from `ComparacaoCampo.detalhes` may contain `|` characters, breaking the Markdown table.
**Why it happens:** The `detalhes` field is free-form text generated by GPT. It may contain pipe characters.
**How to avoid:** Replace `|` with `-` or strip them from cell content: `detalhe.replace("|", "-")`.
**Warning signs:** Malformed Markdown tables that render incorrectly in the browser.

### Pitfall 7: Missing Output Directory
**What goes wrong:** `relatorio.json` write fails with `FileNotFoundError` if `output/` or `output/{par_name}/` doesn't exist.
**Why it happens:** `config.OUTPUT_DIR` is defined but not created at startup.
**How to avoid:** Always call `output_par_dir.mkdir(parents=True, exist_ok=True)` before any file write in `report.py`. The `output/` directory already exists in the repo (confirmed by `ls` output) but subdirs must be created.
**Warning signs:** `FileNotFoundError: [Errno 2] No such file or directory: 'output/par1/relatorio.json'`

---

## Code Examples

### Weighted Average Core (D-01)
```python
# Source: CONTEXT.md D-01; config.py PESO_* constants
def _calcular_score(itens: list["ItemVerificado"]) -> float:
    """Score = soma(peso_i * score_i) / soma(peso_i). Apenas itens com peso > 0."""
    STATUS_SCORE = {
        "OK": 1.0,
        "MATCH": 1.0,
        "DIVERGENTE": 0.0,
        "AUSENTE": 0.5,
        "SUSPEITO": 0.0,
    }
    itens_com_peso = [i for i in itens if i.peso > 0]
    if not itens_com_peso:
        return 1.0  # sem campos com peso → nao ha divergencias conhecidas
    soma_pesos = sum(i.peso for i in itens_com_peso)
    soma_ponderada = sum(
        STATUS_SCORE.get(i.status.value, 0.5) * i.peso
        for i in itens_com_peso
    )
    return soma_ponderada / soma_pesos
```

### Knock-out Application (D-02)
```python
# Source: CONTEXT.md D-02
KNOCKOUTS_SUSPEITO = {"cpf_profissional", "crea_rnp", "cnpj_contratante"}
KNOCKOUT_EMPRESA_CAP = 0.79
KNOCKOUT_SUSPEITO_CAP = 0.49
PENALIDADE_METADATA_SUSPEITO = 0.15
PENALIDADE_DECLARACAO_AUSENTE = 0.20

def _aplicar_knockouts(
    score: float,
    itens: list["ItemVerificado"],
    tem_metadata_suspeita: bool,
    declaracao_necessaria_ausente: bool,
) -> float:
    for item in itens:
        if item.campo in KNOCKOUTS_SUSPEITO and item.status.value == "DIVERGENTE":
            score = min(score, KNOCKOUT_SUSPEITO_CAP)
        if item.campo == "empresa_executora" and item.status.value == "DIVERGENTE":
            score = min(score, KNOCKOUT_EMPRESA_CAP)
    if tem_metadata_suspeita:
        score = max(0.0, score - PENALIDADE_METADATA_SUSPEITO)
    if declaracao_necessaria_ausente:
        score = max(0.0, score - PENALIDADE_DECLARACAO_AUSENTE)
    return score
```

### Exigencias for Cruzamento Divergences (D-10)
```python
# Source: CONTEXT.md D-10
def _gerar_exigencias_cruzamento(
    resultado_cruzamento: "ResultadoCruzamento",
) -> list[str]:
    exigencias = []
    for comp in resultado_cruzamento.comparacoes:
        if comp.status.value != "DIVERGENTE":
            continue
        if comp.campo == "cpf_profissional":
            exigencias.append(
                f"VERIFICAR DIVERGENCIA DE CPF ENTRE ART E ATESTADO"
                f" — CPF DA ART: {comp.valor_art or 'N/A'},"
                f" CPF DO ATESTADO: {comp.valor_atestado or 'N/A'}"
            )
        elif comp.campo == "empresa_executora":
            exigencias.append(
                f"VERIFICAR DIVERGENCIA DE EMPRESA EXECUTORA ENTRE ART E ATESTADO"
                f" — ART: {comp.valor_art or 'N/A'},"
                f" ATESTADO: {comp.valor_atestado or 'N/A'}"
            )
        elif comp.campo == "escopo":
            exigencias.append(
                "VERIFICAR COMPATIBILIDADE DO OBJETO/ESCOPO DO SERVICO ENTRE ART E ATESTADO"
            )
        elif comp.campo == "intervalo_datas":
            exigencias.append(
                "VERIFICAR PERIODO DE EXECUCAO"
                " — DATAS DO ATESTADO NAO ESTAO DENTRO DO INTERVALO DA ART"
            )
    return exigencias
```

### Public API: calcular_veredito
```python
# Source: CONTEXT.md D-01 to D-11; verdict.py stub docstring
def calcular_veredito(
    resultado_cruzamento: "ResultadoCruzamento | None",
    resultado_compliance: "ResultadoCompliance",
    resultados_metadata: "dict[str, MetadadosPDF]",
    resultados_assinatura: "dict[str, ResultadoAssinatura]",
) -> "Veredito":
    # Step 1: Consolidate items from all sources
    itens = _consolidar_itens(
        resultado_cruzamento, resultado_compliance,
        resultados_metadata, resultados_assinatura,
    )

    # Step 2: Generate exigencias from cruzamento divergences + pass compliance exigencias
    exigencias_cruzamento = (
        _gerar_exigencias_cruzamento(resultado_cruzamento)
        if resultado_cruzamento else []
    )
    todas_exigencias = exigencias_cruzamento + resultado_compliance.exigencias

    # Step 3: Compute weighted average score
    score = _calcular_score(itens)

    # Step 4: Apply knock-out rules
    tem_metadata_suspeita = any(
        item.status == StatusItem.SUSPEITO and item.campo.startswith("metadata_")
        for item in itens
    )
    declaracao_necessaria_ausente = (
        resultado_compliance.declaracao_necessaria
        and not resultado_compliance.declaracao_encontrada
    )
    score = _aplicar_knockouts(score, itens, tem_metadata_suspeita, declaracao_necessaria_ausente)

    # Step 5: Classify verdict
    if score >= config.SCORE_ADERENTE:
        tipo = TipoVeredito.ADERENTE
    elif score >= config.SCORE_PENDENTE:
        tipo = TipoVeredito.PENDENTE
    else:
        tipo = TipoVeredito.SUSPEITO

    return Veredito(tipo=tipo, score=score, itens_verificados=itens, exigencias=todas_exigencias)
```

### main.py Wiring (D-17, D-18, D-19, D-20)
```python
# Replace Phase 7 placeholder (lines 158-161 in main.py)
# Source: CONTEXT.md D-17 to D-20

print()
print("--- Fase 6: Veredito, Exigencias e Relatorio ---")

if not pacote.art or not pacote.atestado:
    print("  ART ou Atestado ausente — veredito nao gerado")
    return {"status": "erro", "motivo": "ART ou Atestado ausente"}

from crea_cat_ai import verdict, report

veredito = verdict.calcular_veredito(
    resultado_cruzamento=resultado_cruzamento,
    resultado_compliance=resultado_compliance,
    resultados_metadata=resultados_metadata,
    resultados_assinatura=resultados_assinatura,
)

print(f"  Veredito: {veredito.tipo.value} (score={veredito.score:.2f})")
print(f"  Exigencias: {len(veredito.exigencias)}")

par_name = input_dir.name  # use the directory name as par identifier
report.gerar_relatorios(
    veredito=veredito,
    pacote=pacote,
    resultado_cruzamento=resultado_cruzamento,
    resultado_compliance=resultado_compliance,
    resultados_metadata=resultados_metadata,
    resultados_assinatura=resultados_assinatura,
    resultados_analise=resultados_analise,
    par_name=par_name,
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| String-based status comparisons | str Enum with `.value` | Phase 2 (TipoDocumento) | Must continue — use `.value` for comparisons, not raw string |
| Separate GPT calls per field | Single batch GPT call | Phase 5 | No new GPT calls needed in Phase 7 |
| Import all modules at top level | Import only used modules to avoid stub errors | Phase 2 decision | Add `from crea_cat_ai import verdict, report` inside Phase 7 block in main.py |

---

## Environment Availability

Step 2.6: SKIPPED — Phase 7 is purely code/computation changes with no external dependencies beyond those already installed and validated in Phase 1 (openai, pymupdf, pikepdf, pyhanko, Pillow). No new tools required.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already configured) |
| Config file | `pytest.ini` (project root) |
| Quick run command | `python -m pytest tests/test_verdict.py -x` |
| Full suite command | `python -m pytest tests/ -m "not integration"` |
| Integration run | `python -m pytest tests/ -m integration` (requires OPENAI_API_KEY) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VERD-01 | Weighted score + thresholds → correct TipoVeredito | unit | `pytest tests/test_verdict.py::TestScoring -x` | Wave 0 |
| VERD-01 | Knock-out: CPF divergente → SUSPEITO | unit | `pytest tests/test_verdict.py::TestKnockouts -x` | Wave 0 |
| VERD-01 | Knock-out: empresa divergente → never ADERENTE | unit | `pytest tests/test_verdict.py::TestKnockoutEmpresa -x` | Wave 0 |
| VERD-02 | ItemVerificado consolidated from all 4 sources | unit | `pytest tests/test_verdict.py::TestConsolidarItens -x` | Wave 0 |
| VERD-03 | Exigencias format: MAIUSCULAS, correct template strings | unit | `pytest tests/test_verdict.py::TestExigencias -x` | Wave 0 |
| VERD-04 | JSON report: valid JSON, all required keys present | unit | `pytest tests/test_report.py::TestRelatórioJSON -x` | Wave 0 |
| VERD-05 | Markdown report: contains veredito, exigencias, rodape | unit | `pytest tests/test_report.py::TestRelatorioMarkdown -x` | Wave 0 |
| VERD-06 | Par 2 produces PENDENTE or SUSPEITO, never ADERENTE | integration | `pytest tests/test_integration_phase7.py -m integration` | Wave 0 |
| VERD-06 | Output files written to output/{par_name}/ | integration | `pytest tests/test_integration_phase7.py::TestOutputFiles -m integration` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_verdict.py tests/test_report.py -x`
- **Per wave merge:** `python -m pytest tests/ -m "not integration"`
- **Phase gate:** Full suite green (including integration tests with real API key) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_verdict.py` — covers VERD-01, VERD-02, VERD-03 (unit, no mocks needed — pure functions)
- [ ] `tests/test_report.py` — covers VERD-04, VERD-05 (unit, uses tmp_path fixture)
- [ ] `tests/test_integration_phase7.py` — covers VERD-06 (integration, requires real PDFs + API key)

---

## Open Questions

1. **Par 2 document directory structure**
   - What we know: Par 1 documents are in `Documentos que crea recebe/` (flat). `conftest.py` `PDF_DIR` points there. CONTEXT.md D-19 says "main.py processa cada par de teste separadamente".
   - What's unclear: Are Par 2 documents in a subdirectory (`Par2/`)? Or is the `par_name` derived differently? The actual filesystem was not confirmed to have a `Par2/` directory.
   - Recommendation: Planner should define a `Par2/` subdirectory location OR design `main.py __main__` to accept multiple input dirs. Integration test should skip gracefully if Par2 dir absent.

2. **Peso for compliance-sourced ItemVerificado items**
   - What we know: CAMPO_PESOS maps 13 field names from matching/analysis. Compliance items use requisito IDs (CDOC-01, COMP-01.x) as `campo`.
   - What's unclear: Should NAO_CONFORME compliance items contribute to the weighted average (with some peso), or only via the declaracao_ausente penalty (-0.20)?
   - Recommendation: Assign `peso=0.0` to compliance items. The declaracao_ausente penalty in D-02 already handles the only compliance-triggered knock-out. This avoids double-counting.

3. **Visual fields (assinatura_visual, timbre) in scoring**
   - What we know: `config.py` has `PESO_ASSINATURA_VISUAL = 0.4` and `PESO_TIMBRE = 0.3`. These are not ComparacaoCampo items (they come from ResultadoAnalise.visual, not from cruzamento).
   - What's unclear: Should `tem_assinatura_visual=False` produce an ItemVerificado with status AUSENTE and PESO_ASSINATURA_VISUAL? The CAMPO_PESOS mapping for these is not present in ResultadoCruzamento.
   - Recommendation: Add visual items explicitly during consolidation from `resultados_analise[TipoDocumento.ATESTADO.value].visual`.

---

## Project Constraints (from CLAUDE.md)

| Directive | Implication for Phase 7 |
|-----------|------------------------|
| `import pymupdf` (not `import fitz`) | Not directly used in Phase 7 — but if any helper in verdict/report imports from other modules, pattern must be respected |
| OpenAI API key via `OPENAI_API_KEY` env var | Not used in Phase 7 (no GPT calls) |
| Model: `gpt-4.1` for main tasks | Not applicable — Phase 7 has no GPT calls |
| Responses API with structured output (JSON schema) | Not applicable |
| All log/output messages in pt-BR | All `print()` calls in main.py Phase 7 section must be pt-BR |
| `pathlib.Path` for all paths | Use `config.OUTPUT_DIR / par_name / "relatorio.json"` — no string path concatenation |
| No external servers; local only | No HTTP calls in Phase 7 |
| Decision tool: GPT-4.1 does heavy lifting | Phase 7 confirms this — scoring is pure Python, no new AI calls |

---

## Sources

### Primary (HIGH confidence)
- `07-CONTEXT.md` — All implementation decisions D-01 to D-20, fully specified by user
- `config.py` — All PESO_* constants and SCORE_* thresholds verified by reading the file
- `main.py` lines 158-194 — Integration point verified by reading; existing serialization patterns confirmed
- `matching.py` — `StatusCampo`, `ComparacaoCampo`, `ResultadoCruzamento` interfaces verified
- `compliance.py` — `StatusCompliance`, `VerificacaoItem`, `ResultadoCompliance` interfaces verified
- `metadata.py` — `MetadadosPDF.anomalias: list[str]` verified
- `signature.py` — `ResultadoAssinatura.presente`, `.signatarios` verified
- `analysis.py` — `ResultadoAnalise.visual` fields verified
- `pytest.ini` — Test framework config confirmed: default run excludes integration tests
- `tests/conftest.py` — Existing fixtures and PDF_DIR conventions confirmed

### Secondary (MEDIUM confidence)
- `tests/test_compliance.py`, `tests/test_matching.py` — Test patterns confirmed for new test files to follow

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all existing libraries confirmed present
- Architecture: HIGH — all interfaces read directly from source; no inference needed
- Pitfalls: HIGH — identified from direct code reading (datetime serialization, enum comparison, knock-out ordering)
- Test map: HIGH — existing test pattern (pytest + @pytest.mark.integration + conftest.py) is well-established

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (stable — no external APIs, all local code)
