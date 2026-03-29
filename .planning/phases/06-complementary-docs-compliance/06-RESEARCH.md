# Phase 6: Complementary Docs & Compliance - Research

**Researched:** 2026-03-29
**Domain:** Compliance regulatório CONFEA (Res. 1.137/2023 + Res. 1.160/2025), verificação de documentos complementares (Declaração, Anuência), Python puro + GPT-4.1
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Declaração Trigger & Verification (CDOC-01, CDOC-02, CDOC-03, COMP-03)**
- D-01: Trigger: `engenheiro_habilitado == False` em qualquer assinante do atestado em `ResultadoAnalise.visual.assinantes` — já extraído na Phase 3, sem nova chamada GPT
- D-02: Quando trigado, buscar em `pacote.complementares` documento com `tipo == TipoDocumento.DECLARACAO`
- D-03: Verificação da Declaração: extrair CREA/RNP e especialidade do engenheiro declarante de seu `ResultadoAnalise`, verificar se especialidade é compatível com área do serviço da ART/Atestado
- D-04: Match especialidade-área requer GPT-4.1 — única chamada para comparar título/especialidade do engenheiro com escopo do serviço da ART (semântico, não exato)
- D-05: Se Declaração ausente quando obrigatória → exigência: "APRESENTAR DECLARACAO DE PROFISSIONAL HABILITADO NA AREA, DE ACORDO COM O par. 1, DO ART. 59 DA RESOLUCAO 1137 DO CONFEA"

**Declaração Cross-Reference (CDOC-04)**
- D-06: Cruzar entidades da Declaração com ART e Atestado: CREA do engenheiro declarante deve ser válido, número da ART referenciada na Declaração deve coincidir, nome do profissional deve coincidir
- D-07: Usar mesmos padrões da Phase 5 (`normalizar_crea_rnp` para exato, GPT para nomes fuzzy) — importar e reutilizar utilidades de matching

**Anuência (CDOC-03)**
- D-08: Detecção de subcontratação: comparar `empresa_executora` da ART com empresa do atestado — se empresas diferentes e uma é subcontratada, Anuência é obrigatória
- D-09: Se subcontratação detectada e sem Anuência em `pacote.complementares` → exigência
- D-10: Se Anuência presente → verificar se referencia as partes corretas (contratante, subcontratada, profissional)
- D-11: Nenhum par de teste tem subcontratação — código estrutural sem validação com dados reais ainda

**Anexo IV Checklist (COMP-01)**
- D-12: 6 categorias obrigatórias do Anexo IV (Res. 1.137/2023) verificadas no Atestado:
  1. Identificação do contratante (nome + CNPJ/CPF)
  2. Identificação do profissional (nome + CREA/RNP)
  3. Descrição do serviço/obra (escopo)
  4. Período de execução (datas início/término)
  5. Local da obra (endereço)
  6. Assinatura do contratante (assinatura visual presente)
- D-13: Cada categoria verificada contra campos de `ResultadoAnalise` — Python puro, sem GPT
- D-14: Categoria ausente → `NAO_CONFORME` com exigência específica identificando qual dado está faltando

**Res. 1.160/2025 Application (COMP-02)**
- D-15: Ler `Anexos_Resolucao 1160-2025.pdf` para extrair mudanças específicas da 1.160/2025 sobre a base 1.137/2023
- D-16: Implementação: aplicar regras 1.160 como overrides sobre a lógica de compliance base — código deve ser estruturado com regras base da 1.137 separadas das deltas da 1.160
- D-17: Foco em artigos que afetam requisitos de Declaração, dados do Anexo IV e critérios de aceitação do atestado

**Compliance Output Model**
- D-18: Pydantic model `ResultadoCompliance` seguindo padrões estabelecidos (BaseModel, Field, Optional)
- D-19: Campos: `verificacoes` (lista de resultados por verificação), `exigencias` (lista de strings formatadas), `declaracao_necessaria` (bool), `declaracao_encontrada` (bool), `anuencia_necessaria` (bool), `anuencia_encontrada` (bool), `anexo_iv_completo` (bool), `observacoes` (Optional[str])
- D-20: Cada verificação tem: `requisito` (ID como "CDOC-01"), `descricao`, `status` (CONFORME/NAO_CONFORME/NAO_APLICAVEL), `detalhes`

**GPT vs Lógica Local**
- D-21: Python local (sem GPT): trigger Declaração (flag bool), presença de campos Anexo IV, detecção de Anuência (comparação de empresas), campos exatos cross-reference (CREA, número ART)
- D-22: GPT-4.1 (semântico): matching especialidade-área do engenheiro, validação do conteúdo da Declaração em contexto, fuzzy name matching em cross-references
- D-23: Reutilizar `analysis.normalizar_crea_rnp()` e padrões de matching da Phase 5

### Claude's Discretion
- Design interno dos prompts para chamada GPT de matching especialidade-área
- Se fazer chamadas GPT em lote ou separadas para validação da Declaração
- Como estruturar verificação de Anuência quando dados de teste ficarem disponíveis
- Exata redação das exigências para cada não-conformidade (seguir padrão CREA maiúsculo com base legal)
- Nomenclatura do enum StatusCompliance (CONFORME/NAO_CONFORME/NAO_APLICAVEL ou similar)

### Deferred Ideas (OUT OF SCOPE)
Nenhum — discussão se manteve dentro do escopo da fase.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CDOC-01 | Pipeline verifica se Declaração é necessária (assinante não é engenheiro habilitado) | D-01: flag `engenheiro_habilitado` já disponível em `AssinanteInfo` do Phase 3 — verificação é Python puro |
| CDOC-02 | Declaração verificada: engenheiro declarante da área correta, CREA válido | D-03/D-04: `ResultadoAnalise` da Declaração fornece CREA e título profissional; GPT-4.1 verifica compatibilidade de área com escopo da ART |
| CDOC-03 | Anuência verificada em casos de subcontratação | D-08/D-09: detecção por comparação de empresa_executora entre ART e Atestado; Anuência em `pacote.complementares` |
| CDOC-04 | Dados da Declaração cruzados com ART e Atestado | D-06/D-07: CREA exato via normalizar_crea_rnp, número ART exato, nome fuzzy via GPT — padrões da Phase 5 reutilizados |
| COMP-01 | Conformidade com Anexo IV da Resolução 1.137/2023 (6 categorias de dados) | Anexo IV extraído do PDF: 6 seções com campos mínimos obrigatórios documentados nesta pesquisa |
| COMP-02 | Alterações da Resolução 1.160/2025 aplicadas | PDF analisado: o arquivo é de Res. 1.137/2023, não contém texto da 1.160/2025 — ver seção específica abaixo |
| COMP-03 | Art. 59 §1º (Declaração de profissional habilitado) enforced | D-05: exigência com texto exato no formato CREA quando Declaração ausente |

</phase_requirements>

---

## Summary

A Phase 6 implementa `compliance.py`, o módulo de verificação regulatória do pipeline. Recebe o pacote de documentos, os resultados de análise da Phase 3 e os resultados de cruzamento da Phase 5, e produz um `ResultadoCompliance` com o status de cada verificação regulatória.

A maior parte das verificações é Python puro: trigger de Declaração (leitura de flag booleano), checklist Anexo IV (presença de campos no `ResultadoAnalise`), detecção de subcontratação (comparação de nomes de empresa). Apenas o matching semântico de especialidade-área do engenheiro declarante usa GPT-4.1, em uma única chamada batch.

**Descoberta crítica sobre Res. 1.160/2025:** O arquivo `Anexos_Resolucao 1160-2025.pdf` contém os Anexos I a VI da Resolução 1.137/2023 (modelos de formulários ART, CAT, etc.). Não contém o texto articulado da Resolução 1.160/2025. A implementação da COMP-02 deve ser tratada como "aplicar regras da 1.137/2023 conforme o Anexo IV extraído" até que o texto específico da 1.160/2025 seja fornecido. Ver seção Open Questions.

**Primary recommendation:** Implementar compliance.py em duas camadas — camada local Python para verificações determinísticas (Anexo IV, trigger Declaração, detecção Anuência) e camada GPT para verificações semânticas (especialidade-área matching, cross-reference fuzzy names). Reutilizar `normalizar_crea_rnp` e padrões de `StatusCampo` da Phase 5.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | (via openai dep) | Modelos de dados estruturados (`ResultadoCompliance`, `VerificacaoItem`) | Padrão estabelecido em todas as phases anteriores |
| openai (Python SDK) | latest | GPT-4.1 para matching semântico especialidade-área | Única chamada GPT necessária na fase |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Nenhuma nova dependência | — | — | Todas as libs necessárias já estão no requirements.txt |

**Nenhuma nova instalação necessária.** Toda a Phase 6 usa dependências já instaladas.

---

## Architecture Patterns

### Fluxo de Módulo

```
compliance.py
├── verificar_declaracao()       # Python puro — trigger + busca + cross-ref exato
├── _verificar_especialidade_gpt()  # GPT-4.1 — comparação semântica única
├── verificar_anuencia()         # Python puro — detecção de subcontratação
├── verificar_anexo_iv()         # Python puro — checklist 6 categorias
└── verificar_compliance()       # API pública — orquestra tudo, retorna ResultadoCompliance
```

### Pattern 1: Modelo de Saída Compliance

```python
# Seguindo o mesmo padrão de ResultadoCruzamento em matching.py
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class StatusCompliance(str, Enum):
    CONFORME = "CONFORME"
    NAO_CONFORME = "NAO_CONFORME"
    NAO_APLICAVEL = "NAO_APLICAVEL"

class VerificacaoItem(BaseModel):
    requisito: str          # Ex: "CDOC-01"
    descricao: str          # Descrição legível
    status: StatusCompliance
    detalhes: Optional[str] = None

class ResultadoCompliance(BaseModel):
    verificacoes: list[VerificacaoItem] = Field(default_factory=list)
    exigencias: list[str] = Field(default_factory=list)
    declaracao_necessaria: bool = False
    declaracao_encontrada: bool = False
    anuencia_necessaria: bool = False
    anuencia_encontrada: bool = False
    anexo_iv_completo: bool = False
    observacoes: Optional[str] = None
```

### Pattern 2: Checagem Declaração (Python Puro)

```python
def verificar_declaracao(
    pacote: PacoteDocumentos,
    resultados_analise: dict[str, ResultadoAnalise],
    resultado_cruzamento: ResultadoCruzamento | None,
) -> tuple[list[VerificacaoItem], list[str]]:
    """
    Trigger: qualquer assinante do Atestado com engenheiro_habilitado == False.
    Busca: pacote.complementares com tipo == TipoDocumento.DECLARACAO.
    """
    atestado_analise = resultados_analise.get(TipoDocumento.ATESTADO.value)
    if atestado_analise is None:
        return [VerificacaoItem(
            requisito="CDOC-01",
            descricao="Verificação de Declaração",
            status=StatusCompliance.NAO_APLICAVEL,
            detalhes="Atestado não encontrado no pacote",
        )], []

    # D-01: Verificar assinantes não-engenheiros
    assinantes_nao_eng = [
        a for a in atestado_analise.visual.assinantes
        if not a.engenheiro_habilitado
    ]
    declaracao_necessaria = len(assinantes_nao_eng) > 0

    # D-02: Buscar Declaração nos complementares
    declaracao_doc = next(
        (d for d in pacote.complementares if d.tipo == TipoDocumento.DECLARACAO),
        None
    )
    # ... restante da lógica
```

### Pattern 3: Checklist Anexo IV (Python Puro)

A verificação do Anexo IV mapeia as 6 categorias regulatórias para campos de `ResultadoAnalise`:

```python
CATEGORIAS_ANEXO_IV = [
    {
        "id": "COMP-01-1",
        "descricao": "Identificação do contratante (nome + CNPJ/CPF)",
        "check": lambda r: r.contratante is not None and (
            r.contratante.cnpj is not None or r.contratante.cpf is not None
        ),
        "exigencia": "APRESENTAR IDENTIFICACAO COMPLETA DO CONTRATANTE (RAZAO SOCIAL E CNPJ/CPF) NO ATESTADO, CONFORME ITEM 1.2 DO ANEXO IV DA RESOLUCAO 1137 DO CONFEA",
    },
    {
        "id": "COMP-01-2",
        "descricao": "Identificação do profissional (nome + CREA/RNP)",
        "check": lambda r: r.profissional is not None and r.profissional.crea_rnp is not None,
        "exigencia": "APRESENTAR IDENTIFICACAO COMPLETA DO RESPONSAVEL TECNICO (NOME, TITULO PROFISSIONAL E RNP/CREA) NO ATESTADO, CONFORME ITEM 1.4 DO ANEXO IV DA RESOLUCAO 1137 DO CONFEA",
    },
    {
        "id": "COMP-01-3",
        "descricao": "Descrição do serviço/obra (escopo)",
        "check": lambda r: r.escopo is not None and len(r.escopo.strip()) > 10,
        "exigencia": "APRESENTAR DESCRICAO DETALHADA DOS SERVICOS REALIZADOS NO ATESTADO, CONFORME ITEM 1.5 DO ANEXO IV DA RESOLUCAO 1137 DO CONFEA",
    },
    {
        "id": "COMP-01-4",
        "descricao": "Período de execução (datas início/término)",
        "check": lambda r: r.datas.data_inicio is not None or r.datas.data_termino is not None,
        "exigencia": "APRESENTAR PERIODO DE REALIZACAO (DATA DE INICIO E CONCLUSAO) NO ATESTADO, CONFORME ITEM 1.1 DO ANEXO IV DA RESOLUCAO 1137 DO CONFEA",
    },
    {
        "id": "COMP-01-5",
        "descricao": "Local da obra (endereço)",
        "check": lambda r: r.endereco_obra is not None and (
            r.endereco_obra.cidade is not None or r.endereco_obra.logradouro is not None
        ),
        "exigencia": "APRESENTAR LOCAL DE REALIZACAO DA OBRA/SERVICO NO ATESTADO, CONFORME ITEM 1.1 DO ANEXO IV DA RESOLUCAO 1137 DO CONFEA",
    },
    {
        "id": "COMP-01-6",
        "descricao": "Assinatura do contratante (assinatura visual presente)",
        "check": lambda r: r.visual.tem_assinatura_visual,
        "exigencia": "APRESENTAR ASSINATURA DO REPRESENTANTE DO CONTRATANTE NO ATESTADO, CONFORME ITEM 1.6 DO ANEXO IV DA RESOLUCAO 1137 DO CONFEA",
    },
]
```

### Pattern 4: GPT Call para Especialidade-Área (Única Chamada)

```python
class ResultadoEspecialidadeGPT(BaseModel):
    """Resultado do GPT para matching especialidade-área."""
    compativel: bool
    confianca: float
    justificativa: str

def _verificar_especialidade_gpt(
    titulo_declarante: str,
    escopo_art: str,
) -> ResultadoEspecialidadeGPT:
    """
    Uma única chamada GPT-4.1 para verificar se o título profissional
    do engenheiro declarante é compatível com a área do serviço da ART.
    """
    response = client.responses.parse(
        model=config.OPENAI_MODEL,
        instructions=PROMPT_ESPECIALIDADE,
        input=[{"role": "user", "content": f"Título: {titulo_declarante}\nEscopo: {escopo_art}"}],
        text_format=ResultadoEspecialidadeGPT,
    )
    # Fallback se GPT não retornar resultado
    if response.output_parsed is None:
        return ResultadoEspecialidadeGPT(
            compativel=False,
            confianca=0.0,
            justificativa="GPT não retornou resultado",
        )
    return response.output_parsed
```

### Pattern 5: API Pública

```python
def verificar_compliance(
    pacote: PacoteDocumentos,
    resultados_analise: dict[str, ResultadoAnalise],
    resultado_cruzamento: ResultadoCruzamento | None,
) -> ResultadoCompliance:
    """
    Orquestra todas as verificações de compliance.
    Recebe exatamente os tipos que main.py já tem disponíveis após Phase 5.
    """
```

### Pattern 6: Wiring em main.py

```python
# Substituir placeholder nas linhas 136-140 de main.py:
from crea_cat_ai import compliance

# Phase 6: Documentos Complementares e Compliance
print()
print("--- Fase 5: Documentos Complementares e Compliance ---")
resultado_compliance = compliance.verificar_compliance(
    pacote=pacote,
    resultados_analise=resultados_analise,
    resultado_cruzamento=resultado_cruzamento,
)
print(f"  Declaração necessária: {'SIM' if resultado_compliance.declaracao_necessaria else 'NAO'}")
print(f"  Declaração encontrada: {'SIM' if resultado_compliance.declaracao_encontrada else 'NAO'}")
print(f"  Anuência necessária: {'SIM' if resultado_compliance.anuencia_necessaria else 'NAO'}")
print(f"  Anexo IV completo: {'SIM' if resultado_compliance.anexo_iv_completo else 'NAO'}")
if resultado_compliance.exigencias:
    for exig in resultado_compliance.exigencias:
        print(f"  EXIGENCIA: {exig}")
```

### Anti-Patterns to Avoid

- **Não duplicar `normalizar_crea_rnp`:** Importar de `analysis.py`, não re-implementar.
- **Não fazer GPT call para verificações determinísticas:** Presença de campo no `ResultadoAnalise` é Python puro. GPT só entra para matching semântico especialidade-área.
- **Não assumir que a Declaração está em `resultados_analise["Declaracao"]`:** `analisar_pacote()` usa `doc.tipo.value` como chave, mas pode haver múltiplos complementares do mesmo tipo. Buscar por `pacote.complementares` filtrado por `TipoDocumento.DECLARACAO`, depois acessar o resultado de análise correspondente pelo `caminho` do documento.
- **Não usar `ATESTADO` (maiúsculas) como chave em `resultados_analise`:** A chave é `TipoDocumento.ATESTADO.value` = `"Atestado"` (capitalizado). Ver Phase 5 patterns (STATE.md linha 73).

---

## Regulatório: Anexo IV da Res. 1.137/2023 — Dados Mínimos do Atestado

**Fonte:** Extraído diretamente do arquivo `Anexos_Resolucao 1160-2025.pdf`, página 18 (Resolução nº 1137/2023 - Anexo IV, "DADOS MÍNIMOS DO ATESTADO PARA REGISTRO NO CREA"). Confidence: HIGH.

### Seções do Anexo IV

**1.1 Dados da Obra/Serviço**
- Contrato/Convênio (número, se houver)
- Local de realização (rua, número, complemento, bairro, município, UF e CEP)
- Período de realização (data de início e de conclusão)
- Período executado e prazo contratual (no caso de serviço continuado parcialmente concluído)
- Parcelas executadas (no caso de obra/serviço não continuado parcialmente concluído)

**1.2 Dados do Contratante**
- Pessoa Jurídica: Razão Social + CNPJ
- OU Pessoa Física: Nome completo + CPF

**1.3 Dados da Pessoa Jurídica Contratada**
- Razão Social + CNPJ

**1.4 Dados do(s) Responsável(is) Técnico(s)**
- Nome completo
- Título profissional
- RNP
- Registro no Crea

**1.5 Descrição dos Serviços Realizados**
- Suficientemente detalhada para caracterizar as atividades e identificar profissionais
- Deve identificar os quantitativos correspondentes

**1.6 Identificação do Signatário**
- A) Representante do Contratante: assinatura + identificação (título, nome, cargo/função) + CPF
- B) Profissional Habilitado (opcional, quando houver): assinatura + identificação + CPF + RNP

**Notas Críticas do Anexo IV:**
- Nota 4: "Identificar o profissional habilitado que declarou as informações técnicas constantes do atestado." → Esta nota é a base do Art. 59 §1º: quando o signatário do atestado NÃO é profissional habilitado, é necessária Declaração de profissional habilitado.
- O atestado não deverá conter rasuras ou adulterações.
- O atestado emitido por PJ de direito público ou privado deve ser apresentado em papel timbrado ou com carimbo com CNPJ.
- O atestado que referenciar serviços subcontratados deve estar acompanhado de documentos hábeis que comprovem a efetiva contratação, bem como declaração do responsável técnico principal.

### Mapeamento 6 Categorias → `ResultadoAnalise` Fields

| Categoria COMP-01 | Campo Verificado | Field em ResultadoAnalise |
|-------------------|-----------------|--------------------------|
| 1 — Identificação do contratante | nome + CNPJ ou CPF | `contratante.nome` + `contratante.cnpj` / `contratante.cpf` |
| 2 — Identificação do profissional | nome + CREA/RNP | `profissional.nome` + `profissional.crea_rnp` |
| 3 — Descrição do serviço | escopo não vazio | `escopo` (len > 10 chars) |
| 4 — Período de execução | data início ou término | `datas.data_inicio` ou `datas.data_termino` |
| 5 — Local da obra | endereço mínimo | `endereco_obra.cidade` ou `endereco_obra.logradouro` |
| 6 — Assinatura do contratante | assinatura visual | `visual.tem_assinatura_visual` |

---

## Regulatório: Res. 1.160/2025 — Situação Real

**Descoberta importante (Confidence: HIGH):** O arquivo `Anexos_Resolucao 1160-2025.pdf` contém 20 páginas com os modelos de Anexos I (ART), II (CAT), III (Requerimento), IV (Dados Mínimos do Atestado), V (CAO) e VI (Requerimento CAO) da Resolução 1.137/2023 — não o texto articulado da Res. 1.160/2025.

O arquivo faz referência a "Resolução nº XXXX/20XX" em alguns modelos, indicando que são templates atualizados (potencialmente aplicáveis à 1.160), mas não contém artigos que alterem os requisitos da 1.137.

**Implicação para implementação (D-16):**
- A estrutura de Anexo IV verificada acima é de 1.137/2023 e é o baseline confirmado.
- Para COMP-02, a implementação deve criar um hook/override point para regras 1.160, mas popula-lo com comentário indicando que o texto específico da 1.160 não foi encontrado no arquivo fornecido.
- Código deve separar claramente `_verificacoes_1137()` de `_verificacoes_1160_overrides()` (mesmo que este último retorne lista vazia inicialmente).

```python
def _verificacoes_1137(atestado: ResultadoAnalise) -> list[VerificacaoItem]:
    """Regras base da Res. 1.137/2023 — Anexo IV."""
    # ... 6 categorias do Anexo IV

def _verificacoes_1160_overrides(atestado: ResultadoAnalise) -> list[VerificacaoItem]:
    """
    Alterações da Res. 1.160/2025 sobre a base 1.137.
    PENDENTE: texto articulado da 1.160/2025 não disponível no PDF fornecido.
    Retorna lista vazia até que o texto seja fornecido.
    """
    # TODO: implementar quando texto articulado da 1.160/2025 for fornecido
    return []
```

---

## Regulatório: Art. 59 §1º e Declaração

**Regra (base Res. 1.137/2023, Nota 4 do Anexo IV):** Quando o signatário do atestado NÃO é profissional habilitado (CREA/RNP/título de engenharia), é necessária Declaração de profissional habilitado na área confirmando a execução técnica.

**Exigência exata no formato CREA (D-05, D-07 — Confidence: HIGH, validada pelo analista CREA em CONTEXT.md):**
```
APRESENTAR DECLARACAO DE PROFISSIONAL HABILITADO NA AREA, DE ACORDO COM O par. 1, DO ART. 59 DA RESOLUCAO 1137 DO CONFEA
```

**Caso de teste Par 1:**
- Ruan (ADMINISTRADOR, `engenheiro_habilitado = False`) assina o atestado
- Declaração de Alexandre Bueno Neto (Engenheiro Eletricista) está em `pacote.complementares`
- Arquivo: `944678.2026__DECLARACAO__ENG_2_assinado__1_05022026162803.pdf`

---

## Regulatório: Anuência em Subcontratação

**Regra (Anexo III, seção 6.2 — Confidence: HIGH):** Em casos de subcontratação, o atestado deve estar acompanhado de "documento que apresente a anuência da contratante original ou documentos hábeis que comprovem a efetiva participação do profissional na execução da obra ou prestação do serviço".

**Exigência no formato CREA quando ausente:**
```
APRESENTAR ANUENCIA DA CONTRATANTE ORIGINAL OU DOCUMENTOS HABEIS QUE COMPROVEM A EFETIVA PARTICIPACAO DO PROFISSIONAL, CONFORME SEC. 6.2 DO ANEXO III DA RESOLUCAO 1137 DO CONFEA
```

**Detecção de subcontratação:** Comparar `art.empresa_executora.nome` com `atestado.empresa_executora.nome` ou `atestado.contratante.nome`. Se as empresas são distintas (usando `normalizar_crea_rnp` não serve para nomes; usar comparação case-insensitive + trim), há subcontratação potencial.

**Nota D-11:** Nenhum par de teste tem subcontratação confirmada. O código estrutural deve ser implementado mas não haverá teste de integração com dados reais nesta fase.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Normalização de CREA/RNP | Nova função de strip de dígitos | `analysis.normalizar_crea_rnp()` | Já implementado, coberto por testes |
| Comparação exata de identificadores | Lógica de match manual | `matching._status_exato()` (padrão interno) ou reimplementar localmente com a mesma lógica | Evita divergência de comportamento |
| Structured output do GPT | Parsing manual de JSON | `client.responses.parse(..., text_format=ModelPydantic)` | Padrão estabelecido em todas as phases |
| Fallback quando GPT retorna None | Try/except complexo | Checar `response.output_parsed is None` e retornar default | Padrão estabelecido em analysis.py e matching.py |
| Enum de status como str | Enum padrão | `class StatusCompliance(str, Enum)` | Permite serialização JSON direta — padrão de StatusCampo/TipoDocumento |

**Key insight:** Toda a lógica local desta fase é checagem de presença de campos em modelos Pydantic já construídos pelas phases anteriores. Não há processamento complexo — a complexidade foi tratada nas phases 2-5.

---

## Common Pitfalls

### Pitfall 1: Chave errada em `resultados_analise`

**What goes wrong:** Buscar `resultados_analise["ATESTADO"]` ao invés de `resultados_analise["Atestado"]`.
**Why it happens:** `TipoDocumento` é str Enum com valores capitalizados: `ATESTADO = "Atestado"`, `DECLARACAO = "Declaracao"`.
**How to avoid:** Sempre usar `TipoDocumento.ATESTADO.value` como chave, nunca string literal.
**Warning signs:** `KeyError` ou retorno `None` inesperado ao buscar resultados de análise.

### Pitfall 2: Assumir um único documento Declaração por chave

**What goes wrong:** `resultados_analise.get("Declaracao")` retorna apenas um resultado, mas podem existir múltiplas Declarações em `pacote.complementares`.
**Why it happens:** `analisar_pacote()` usa `doc.tipo.value` como chave — se houver dois documentos do tipo "Declaracao", o segundo sobrescreve o primeiro no dict.
**How to avoid:** Filtrar `pacote.complementares` por `TipoDocumento.DECLARACAO`, então buscar o resultado correspondente indexando por posição ou caminho. Alternativa: aceitar que o pipeline processa apenas a primeira Declaração encontrada (suficiente para o MVP de 2 pares).
**Warning signs:** Declaração presente mas não sendo encontrada.

### Pitfall 3: Falso positivo de subcontratação

**What goes wrong:** Comparação simplista de `empresa_executora` detecta subcontratação onde não existe porque os campos têm variações de formatação.
**Why it happens:** "TABOCA AGRO NEGÓCIOS LTDA" vs "Taboca Agro" são a mesma empresa mas uma comparação de string simples marcaria como divergente.
**How to avoid:** Para detecção de subcontratação, se as empresas divergem, não assumir automaticamente subcontratação — gerar verificação `NAO_CONFORME` com `detalhes` explicativos mas não exigência automática de Anuência sem confirmação semântica. Alternativa: usar o resultado de cruzamento da Phase 5 (campo `empresa_executora`) que já passou pelo GPT.
**Warning signs:** Anuência sendo exigida para Par 1 onde Ruan e Alexandre são da mesma empresa contratante.

### Pitfall 4: GPT call desnecessária para verificações booleanas

**What goes wrong:** Chamar GPT para verificar se um campo está presente (ex: "o escopo está preenchido?").
**Why it happens:** Tentação de fazer o GPT "validar qualidade" em vez de apenas checar presença.
**How to avoid:** Checagem Anexo IV é 100% presença de campo — Python puro. GPT só para especialidade-área (comparação semântica genuína).
**Warning signs:** Mais de uma chamada GPT em `compliance.py` além da chamada de especialidade-área.

### Pitfall 5: Confusão entre `ResultadoAnalise` do Atestado e da Declaração

**What goes wrong:** Usar o `profissional` do Atestado para verificar habilitação ao invés do `profissional` da Declaração.
**Why it happens:** O `profissional` em `ResultadoAnalise` do Atestado é o engenheiro que consta no corpo do atestado — não necessariamente o assinante. O assinante está em `visual.assinantes`.
**How to avoid:** Para trigger da Declaração, usar `atestado_analise.visual.assinantes`. Para verificar habilitação do declarante, usar `declaracao_analise.profissional`.
**Warning signs:** Declaração sendo exigida mesmo quando o engenheiro está listado em `profissional` do atestado.

---

## Code Examples

### Acesso ao flag `engenheiro_habilitado`

```python
# Source: crea_cat_ai/analysis.py — AssinanteInfo model
# Trigger CDOC-01
atestado = resultados_analise.get(TipoDocumento.ATESTADO.value)
assinantes_nao_eng = [
    a for a in (atestado.visual.assinantes if atestado else [])
    if not a.engenheiro_habilitado
]
declaracao_necessaria = len(assinantes_nao_eng) > 0
```

### Busca por tipo em complementares

```python
# Source: crea_cat_ai/ingestion.py — PacoteDocumentos.complementares
declaracao_doc = next(
    (d for d in pacote.complementares if d.tipo == TipoDocumento.DECLARACAO),
    None
)
anuencia_doc = next(
    (d for d in pacote.complementares if d.tipo == TipoDocumento.ANUENCIA),
    None
)
```

### Reutilização de normalizar_crea_rnp

```python
# Source: crea_cat_ai/analysis.py
from crea_cat_ai.analysis import normalizar_crea_rnp

# Cross-reference: CREA do declarante vs CREA do profissional do atestado
crea_declarante = normalizar_crea_rnp(
    declaracao_analise.profissional.crea_rnp if declaracao_analise.profissional else None
)
crea_atestado = normalizar_crea_rnp(
    atestado_analise.profissional.crea_rnp if atestado_analise.profissional else None
)
# Em Par 1: ambos devem ser o CREA de Alexandre
```

### Structured output GPT — padrão estabelecido

```python
# Source: crea_cat_ai/matching.py — _comparar_via_gpt() pattern
response = client.responses.parse(
    model=config.OPENAI_MODEL,
    instructions=PROMPT_ESPECIALIDADE,
    input=[{"role": "user", "content": bloco_input}],
    text_format=ResultadoEspecialidadeGPT,
)
if response.output_parsed is None:
    # Fallback — não deve bloquear o pipeline
    return ResultadoEspecialidadeGPT(
        compativel=False,
        confianca=0.0,
        justificativa="GPT nao retornou resultado — verificar manualmente",
    )
```

### Prompt sugerido para especialidade-área (Claude's Discretion)

```python
PROMPT_ESPECIALIDADE = """Você é um especialista em habilitações profissionais do CREA (Conselho Regional de Engenharia e Agronomia do Brasil).

Analise se o título profissional do engenheiro declarante é COMPATÍVEL com a área técnica do serviço descrito.

CRITÉRIOS DE COMPATIBILIDADE:
- Engenheiro Eletricista: habilitado para projetos elétricos, iluminação, instalações elétricas, subestações, sistemas de energia
- Engenheiro Civil: habilitado para obras civis, construção, estruturas, fundações, hidráulica
- Engenheiro Mecânico: habilitado para sistemas mecânicos, climatização, HVAC, caldeiras
- Engenheiro Agrônomo: habilitado para atividades agrícolas, agropecuárias, ambientais rurais
- Arquiteto: habilitado para projetos arquitetônicos, interiores, urbanismo

COMPATÍVEL = o serviço está claramente dentro da área de atuação do título profissional.
INCOMPATÍVEL = o serviço está claramente fora da área de atuação — ex: Engenheiro Civil declarando projeto elétrico.
INCERTO = há sobreposição de áreas ou informação insuficiente para determinar.

Retorne compativel=true somente se claramente compatível."""
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Verificação manual dos 15 campos do Anexo IV | Checagem automática de 6 categorias-chave via Python puro | Phase 6 | Reduz de 15 campos granulares para 6 categorias actionable |
| Verificação de habilitação do assinante manual | Flag `engenheiro_habilitado` computado automaticamente pelo GPT-4.1 no Phase 3 | Phase 3 | Trigger de Declaração é determinístico, sem nova chamada GPT |
| Stack overengineered (spaCy, LanguageTool) | GPT-4.1 Vision faz OCR, NER e análise visual | Pivot 2026-03-28 | Fase 6 herda entidades já extraídas — não precisa processar PDFs diretamente |

---

## Open Questions

1. **Texto articulado da Res. 1.160/2025 não encontrado**
   - What we know: O arquivo `Anexos_Resolucao 1160-2025.pdf` contém modelos de formulários da 1.137/2023, não o texto da 1.160/2025.
   - What's unclear: Quais artigos específicos a 1.160/2025 altera em relação à 1.137/2023 que afetam os requisitos de Declaração, Anexo IV e aceitação de atestados.
   - Recommendation: Implementar COMP-02 como "regras 1.137 aplicadas" com hook separado `_verificacoes_1160_overrides()` retornando lista vazia e comentário TODO. Marcar `status = CONFORME` com `detalhes = "Aplicada Res. 1.137/2023 — texto 1.160/2025 pendente de revisão"` para as verificações de base.

2. **Acesso ao `ResultadoAnalise` da Declaração**
   - What we know: `analisar_pacote()` cria o dict com chave `doc.tipo.value`. Para Declaração, a chave é `"Declaracao"`. Se há apenas uma Declaração no pacote, `resultados_analise.get("Declaracao")` funciona.
   - What's unclear: Se `analisar_pacote()` foi chamada com os complementares incluídos (ver `analysis.py` linha 325: `documentos.extend(pacote.complementares)`) — SIM, a função analisa todos os documentos do pacote. Resolvido: usar `resultados_analise.get(TipoDocumento.DECLARACAO.value)`.
   - Recommendation: Para MVP (1 Declaração por pacote), `resultados_analise.get("Declaracao")` é suficiente.

3. **Verificação de Anuência sem dados de teste**
   - What we know: D-11 confirma que nenhum par de teste tem subcontratação.
   - What's unclear: Como o CREA define "subcontratação" em termos de campos extraíveis — se é sempre pelo campo empresa_executora ou se há outros indicadores.
   - Recommendation: Implementar detecção baseada em `empresa_executora` vs `contratante` divergentes (após Phase 5 já detecção acontece). Se resultado de cruzamento da Phase 5 mostrar `empresa_executora` como `DIVERGENTE`, sinalizar verificação de Anuência. Marcar como `NAO_APLICAVEL` quando Phase 5 mostra `AUSENTE` para esse campo.

---

## Environment Availability

Step 2.6: SKIPPED (sem novas dependências externas — Phase 6 usa apenas bibliotecas já instaladas: openai, pydantic, e código do próprio projeto).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (pytest.ini presente) |
| Config file | `pytest.ini` — `addopts = -m "not integration"` |
| Quick run command | `pytest tests/test_compliance.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CDOC-01 | Declaração necessária quando assinante NÃO é engenheiro | unit | `pytest tests/test_compliance.py::TestDeclaracaoTrigger::test_assinante_nao_engenheiro_requer_declaracao -x` | Wave 0 |
| CDOC-01 | Declaração NÃO necessária quando assinante É engenheiro | unit | `pytest tests/test_compliance.py::TestDeclaracaoTrigger::test_assinante_engenheiro_nao_requer_declaracao -x` | Wave 0 |
| CDOC-02 | Declaração encontrada: engenheiro da área correta (mock GPT) | unit | `pytest tests/test_compliance.py::TestDeclaracaoVerificacao::test_declaracao_encontrada_engenheiro_area_correta -x` | Wave 0 |
| CDOC-02 | Declaração ausente quando obrigatória → exigência gerada | unit | `pytest tests/test_compliance.py::TestDeclaracaoVerificacao::test_declaracao_ausente_gera_exigencia -x` | Wave 0 |
| CDOC-03 | Anuência NAO_APLICAVEL quando sem subcontratação | unit | `pytest tests/test_compliance.py::TestAnuencia::test_sem_subcontratacao_nao_aplicavel -x` | Wave 0 |
| CDOC-04 | Cross-reference CREA declarante vs profissional atestado | unit | `pytest tests/test_compliance.py::TestCrossReference::test_crea_declarante_matches_profissional -x` | Wave 0 |
| COMP-01 | Atestado completo → todas 6 categorias CONFORME | unit | `pytest tests/test_compliance.py::TestAnexoIV::test_atestado_completo_todas_categorias_conforme -x` | Wave 0 |
| COMP-01 | Atestado sem escopo → categoria 3 NAO_CONFORME + exigência | unit | `pytest tests/test_compliance.py::TestAnexoIV::test_atestado_sem_escopo_gera_exigencia -x` | Wave 0 |
| COMP-01 | Atestado sem assinatura visual → categoria 6 NAO_CONFORME | unit | `pytest tests/test_compliance.py::TestAnexoIV::test_atestado_sem_assinatura_gera_exigencia -x` | Wave 0 |
| COMP-02 | Verificações 1.137 aplicadas, hook 1.160 vazio | unit | `pytest tests/test_compliance.py::TestRes1160::test_verificacoes_1137_aplicadas -x` | Wave 0 |
| COMP-03 | Exigência Art. 59 tem texto exato no formato CREA | unit | `pytest tests/test_compliance.py::TestDeclaracaoVerificacao::test_exigencia_formato_crea_correto -x` | Wave 0 |
| CDOC-01 + CDOC-02 | Integration Par 1: Ruan dispara Declaração, Alexandre encontrado | integration | `pytest tests/test_integration_phase6.py -m integration -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_compliance.py -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green antes do `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_compliance.py` — cobre CDOC-01 a CDOC-04, COMP-01 a COMP-03
- [ ] `tests/test_integration_phase6.py` — teste de integração do Par 1 (Ruan/Alexandre) com dados reais e API real

*(Conftest e fixtures existentes em `tests/conftest.py` devem ser reutilizadas — verificar se helpers `_make_resultado` de `test_matching.py` podem ser compartilhados para `ResultadoAnalise` fixtures.)*

---

## Sources

### Primary (HIGH confidence)
- `Anexos_Resolucao 1160-2025.pdf` (arquivo local, 20 páginas) — Anexo IV (página 18): Dados Mínimos do Atestado para Registro no CREA; Anexo III (páginas 16-17): Documentação obrigatória incluindo Anuência para subcontratação
- `crea_cat_ai/analysis.py` — Modelos `ResultadoAnalise`, `AssinanteInfo`, `normalizar_crea_rnp`
- `crea_cat_ai/matching.py` — Padrões `StatusCampo`, GPT batch call, fallback patterns
- `crea_cat_ai/ingestion.py` — `TipoDocumento` enum, `PacoteDocumentos`
- `.planning/phases/06-complementary-docs-compliance/06-CONTEXT.md` — Decisões D-01 a D-23

### Secondary (MEDIUM confidence)
- `main.py` linha 136-140 — Integration point para Phase 6
- `config.py` — `OPENAI_MODEL`, thresholds
- `.planning/STATE.md` — Decisões acumuladas (chave `"Atestado"` vs `"ATESTADO"`)
- `tests/test_matching.py` — Padrões de teste, helper `_make_resultado`

### Tertiary (LOW confidence)
- Texto específico da Resolução 1.160/2025 — NÃO ENCONTRADO no arquivo fornecido. Requer fornecimento do texto articulado para implementação completa de COMP-02.

---

## Project Constraints (from CLAUDE.md)

- `import pymupdf` — nunca `import fitz`
- `OPENAI_API_KEY` via variável de ambiente
- Modelo padrão: `gpt-4.1` via `config.OPENAI_MODEL`
- Responses API com structured output (JSON schema via Pydantic) — `client.responses.parse(..., text_format=Model)`
- Todas as mensagens de log e output em português (pt-BR)
- Paths usando `pathlib.Path`
- Testes de integração marcados com `@pytest.mark.integration`, excluídos do run padrão
- Sem Docker, sem deploy, Windows 11
- GPT-4.1 Vision como motor principal — não adicionar bibliotecas novas sem necessidade explícita

---

## Metadata

**Confidence breakdown:**
- Regulatório Anexo IV: HIGH — extraído diretamente do PDF oficial
- Regulatório Res. 1.160/2025: LOW — texto articulado não encontrado no arquivo fornecido
- Architecture patterns: HIGH — baseado em código existente das phases 3 e 5
- Integration points: HIGH — lido diretamente de main.py e analysis.py
- Test patterns: HIGH — baseado em estrutura de testes existente (pytest.ini, conftest.py, test_matching.py)

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (30 dias para stack estável; texto da 1.160/2025 é bloqueador para COMP-02 completo)
