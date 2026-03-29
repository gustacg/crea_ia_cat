# 🏗️ CREA CAT AI — Documento de Contexto Master (MVP)

> **Última atualização:** 28/03/2026
> **Status:** MVP — Validação de pureza e eficácia via Claude Code
> **Regra de ouro:** A solução NÃO substitui o analista humano. É ferramenta de apoio. A decisão final é do CREA.
> **Escopo MVP:** Pipeline Python local, sem frontend, sem deploy, sem banco. 2 usuários de teste (ART + Atestado cada).

---

## 1. O QUE É A CAT

A **Certidão de Acervo Técnico** é o "currículo oficial" do profissional de engenharia, emitido pelo CREA. Comprova, com fé pública, todas as obras e serviços executados com base nas ARTs registradas.

**Sem a CAT, o profissional não consegue:**
- Participar de licitações públicas
- Comprovar experiência para contratos
- Demonstrar capacidade técnica

---

## 2. FLUXO ATUAL (Manual)

```
1. Profissional preenche requerimento e anexa documentos
2. Paga a taxa de serviço
3. Analista faz análise MANUAL de todos os documentos
4. Verifica compatibilidade com a ART
5. Emite CAT ou gera exigência
```

**Prazo médio:** até 15 dias. Com exigências, o prazo reinicia.

---

## 3. PROBLEMAS IDENTIFICADOS

| Problema | Descrição |
|---|---|
| **Demora** | Prazo médio de até 15 dias. Com exigências reinicia. Profissional pode perder licitações. |
| **Sobrecarga da equipe** | Volume alto de solicitações. Cada processo exige leitura atenta de múltiplas páginas. |
| **Risco de fraude** | Documentos podem ser adulterados: datas alteradas, valores inflados, assinaturas editadas. Difícil detectar manualmente. |
| **Inconsistências evitáveis** | Muitos processos retornam por erros simples: data divergente, nome diferente, campo obrigatório faltando. |

---

## 4. OS DOIS PRODUTOS

### 4.1 — Produto A: IA Interna do CREA (Sistema Completo)

**Onde vive (futuro):** Dentro do sistema interno do CREA, integrado ao **SITAC**.
**Onde vive (MVP):** Script Python rodando no Claude Code com documentos de teste.

**Funcionalidades do MVP:**

| # | Funcionalidade | No MVP? | Detalhe |
|---|---|---|---|
| 1 | **Extração de texto (OCR)** | ✅ SIM | Extrair texto de PDFs e imagens dos documentos de teste |
| 2 | **Extração de metadados** | ✅ SIM | Analisar metadados do PDF para detectar edição/criação suspeita |
| 3 | **Detecção de manipulação digital** | ✅ SIM | ELA + metadados para identificar adulteração |
| 4 | **Verificação de assinatura digital** | ✅ SIM | Validar certificados ICP-Brasil, integridade pós-assinatura |
| 5 | **Detecção de assinatura visual fraudulenta** | ✅ SIM | Detectar cópia/colagem de assinatura |
| 6 | **Verificação de assinatura qualificada** | ✅ SIM | Assinante habilitado + CREA/CPF abaixo do nome |
| 7 | **Cruzamento Atestado × ART** | ✅ SIM | Nome, CPF, CNPJ, endereço, objeto, empresa, datas |
| 8 | **Verificação de CNPJ** | ⚠️ PARCIAL | Apenas verifica se CNPJ do atestado bate com o da ART. **NÃO consulta Receita Federal** |
| 9 | **Verificação ortográfica** | ✅ SIM | Erros de português, formatação inconsistente |
| 10 | **Verificação de timbre** | ✅ SIM | Atestado deve ter timbre da contratante |
| 11 | **Classificação de documentos** | ✅ SIM | Identificar tipo: atestado, contrato, NF, ART |
| 12 | **Conformidade com Anexo IV (Res. 1.137/2023)** | ✅ SIM | Checklist regulatório automático |
| 13 | **Parecer automático** | ✅ SIM | Veredito: ADERENTE / PENDENTE / SUSPEITO |
| 14 | **Scoring de risco** | ❌ NÃO | Requer histórico de múltiplas solicitações |
| 15 | **Dashboard de gestão** | ❌ NÃO | Sem frontend no MVP |
| 16 | **Integração com SITAC** | ❌ NÃO | MVP roda isolado com arquivos locais |
| 17 | **Aprendizado contínuo** | ❌ NÃO | Requer volume de dados e feedback |

### 4.2 — Produto B: Ferramenta Pré-Envio para Engenheiros (Simplificada)

**Status no MVP:** ❌ NÃO incluída. Será desenvolvida após validação do Produto A.

---

## 5. ESCOPO DO MVP

### 5.1 — O que o MVP faz

```
ENTRADA:
  → 2 pares de documentos de teste (ART + Atestado de cada usuário)
  → Arquivos PDF ou imagem

PROCESSAMENTO (pipeline Python no Claude Code):
  → Extrai texto via OCR
  → Extrai e analisa metadados do arquivo
  → Detecta manipulação digital (ELA)
  → Verifica assinatura (digital e visual)
  → Cruza dados do atestado com dados da ART
  → Verifica ortografia e formatação
  → Verifica presença de timbre
  → Classifica o documento
  → Aplica regras do Anexo IV (Res. 1.137/2023 + 1.160/2025)

SAÍDA:
  → Relatório em JSON/Markdown com:
    → Veredito: ADERENTE / PENDENTE / SUSPEITO
    → Lista de itens verificados com status (OK / DIVERGENTE / AUSENTE / SUSPEITO)
    → Exigências geradas (se aplicável)
    → Confiança do parecer
```

### 5.2 — O que o MVP NÃO faz

```
❌ Frontend (nenhuma interface web)
❌ Deploy / infraestrutura / Docker
❌ Banco de dados (tudo em memória / arquivos)
❌ Dashboard de gestão
❌ Feedback loop / aprendizado contínuo
❌ Integração com SITAC
❌ Consulta de CNPJ na Receita Federal
❌ Scoring de risco (sem histórico)
❌ Produto B (ferramenta do engenheiro)
❌ Fila de tarefas / processamento assíncrono
```

### 5.3 — Dados de teste

```
Usuário 1:
  → ART: [documento a ser fornecido]
  → Atestado: [documento a ser fornecido]

Usuário 2:
  → ART: [documento a ser fornecido]
  → Atestado: [documento a ser fornecido]
```

---

## 6. MARCO REGULATÓRIO

| Resolução | Status | Observação |
|---|---|---|
| **Resolução 1.137/2023 do CONFEA** | Base regulatória | Define regras de emissão de CAT, incluindo Anexo IV |
| **Resolução 1.160/2025 do CONFEA** | Alteração vigente a partir de março/2026 | Altera disposições da 1.137 |

> ⚠️ **AÇÃO NECESSÁRIA:** Obter e analisar o texto completo do Anexo IV da Resolução 1.137/2023 e todas as alterações introduzidas pela Resolução 1.160/2025.

### 6.1 — Exigências padrão do CREA (extraídas do briefing)

```
1. O atestado DEVE apresentar timbre da contratante e ser assinado por ela
2. Empresa executora no atestado deve bater com empresa na ART
3. Objeto da obra no atestado deve bater com objeto da ART
4. Endereço da obra deve ser consistente entre atestado e ART
5. Se atestado menciona serviço de área específica (ex: eletricista),
   deve haver vínculo do profissional com o contratante OU
   declaração de profissional habilitado da área
6. Referência: § 1º, Art. 59 da Resolução 1137 do CONFEA
```

### 6.2 — Checklist de cruzamento Atestado × ART

| Campo | Atestado | ART | Regra |
|---|---|---|---|
| Nome do profissional | ✓ | ✓ | Devem ser idênticos |
| CPF | ✓ | ✓ | Devem ser idênticos |
| Nº CREA | ✓ | ✓ | Devem ser idênticos |
| CNPJ da contratante | ✓ | ✓ | Devem bater entre si (sem consulta externa) |
| Empresa executora | ✓ | ✓ | Se atestado informa, ART deve informar a mesma |
| Objeto/escopo do serviço | ✓ | ✓ | Devem ser compatíveis (comparação semântica via LLM) |
| Endereço da obra | ✓ | ✓ | Devem ser compatíveis (fuzzy match) |
| Datas (início/fim) | ✓ | ✓ | Devem ser compatíveis |
| Valores | ✓ | ✓ | Se informados, verificar coerência |

### 6.3 — Verificação de assinatura

```
Regra principal:
  → Atestado deve ter assinatura + (CREA ou CPF) abaixo do nome

Regra de habilitação:
  → O assinante deve ser engenheiro com habilitação para os serviços do atestado
  → Se NÃO for habilitado:
    → Deve existir documento anexo: "Declaração de Comprovação"
    → Essa declaração deve conter assinatura de engenheiro habilitado

Verificação anti-fraude:
  → Detectar se assinatura é imagem copiada/colada
  → Verificar se mesma assinatura aparece em múltiplos documentos (pixel-match)
  → Validar certificado digital se assinatura for digital (ICP-Brasil)
  → Verificar integridade: documento não alterado após assinatura digital
```

---

## 7. FUNCIONALIDADES DIFERENCIAIS (Para slide — visão futura)

| # | Diferencial | No MVP? |
|---|---|---|
| 1 | **Detecção de manipulação digital** | ✅ SIM |
| 2 | **Conformidade com Anexo IV** | ✅ SIM |
| 3 | **Dashboard de gestão** | ❌ Futuro |
| 4 | **Integração com SITAC** | ❌ Futuro |
| 5 | **Aprendizado contínuo** | ❌ Futuro |

---

## 8. TECH STACK (MVP — Claude Code)

### 8.1 — Processamento de documentos

| Componente | Tecnologia | Justificativa |
|---|---|---|
| **OCR** | Tesseract 5 (pytesseract) | Funciona local, sem API externa |
| **PDF parsing** | PyMuPDF (fitz) + pdfplumber | Extração de texto nativo + layout-aware |
| **Metadados PDF** | pikepdf + python-exiftool | Análise de metadados (criação, edição, software) |
| **Processamento de imagem** | OpenCV + Pillow | Pré-processamento OCR + ELA + detecção visual |

### 8.2 — IA / NLP

| Componente | Tecnologia | Justificativa |
|---|---|---|
| **LLM** | Claude API (Anthropic) | Análise semântica, comparação de escopos, parecer, extração |
| **NER** | spaCy (pt_core_news_lg) | Extração de nomes, CPF, CNPJ, endereços, datas |
| **Verificação ortográfica** | LanguageTool (local ou API) | Verificação gramatical pt-BR |

### 8.3 — Verificação de assinatura

| Componente | Tecnologia | Justificativa |
|---|---|---|
| **Assinatura digital ICP-Brasil** | pyHanko + pyOpenSSL | Validação de certificado + integridade |
| **Detecção de assinatura visual** | OpenCV (template matching + ELA) | Detecta cópia/colagem |

### 8.4 — Estrutura do projeto (Claude Code)

```
crea-cat-ai/
├── main.py                     # Entry point — processa um par ART+Atestado
├── config.py                   # Constantes, thresholds, regras
├── models/
│   └── schemas.py              # Dataclasses / Pydantic models para todas as variáveis
├── extractors/
│   ├── ocr.py                  # OCR (Tesseract)
│   ├── pdf_parser.py           # Extração de texto nativo de PDFs
│   ├── metadata.py             # Extração de metadados do arquivo
│   └── ner.py                  # Named Entity Recognition (spaCy)
├── analyzers/
│   ├── crossref.py             # Cruzamento Atestado × ART
│   ├── signature.py            # Verificação de assinatura (digital + visual)
│   ├── manipulation.py         # Detecção de manipulação (ELA + metadados)
│   ├── spelling.py             # Verificação ortográfica
│   ├── compliance.py           # Conformidade Anexo IV (Res. 1.137 + 1.160)
│   └── classifier.py           # Classificação de tipo de documento
├── reporters/
│   ├── verdict.py              # Gera veredito final (ADERENTE/PENDENTE/SUSPEITO)
│   └── report.py               # Gera relatório estruturado (JSON + Markdown)
├── utils/
│   ├── image.py                # Helpers de processamento de imagem
│   └── text.py                 # Helpers de texto (normalização, fuzzy match)
├── tests/
│   ├── user1/
│   │   ├── art.pdf
│   │   └── atestado.pdf
│   └── user2/
│       ├── art.pdf
│       └── atestado.pdf
└── output/
    ├── user1_report.json
    ├── user1_report.md
    ├── user2_report.json
    └── user2_report.md
```

---

## 9. VARIÁVEIS DO SISTEMA

### 9.1 — Dados de entrada

```
documento_atestado: PDF | Imagem       # Atestado de capacidade técnica
documento_art: PDF                     # ART de referência
```

### 9.2 — Dados extraídos do Atestado

```
atestado.nome_profissional: string
atestado.cpf: string
atestado.crea: string
atestado.cnpj_contratante: string
atestado.razao_social_contratante: string
atestado.empresa_executora: string | null
atestado.objeto_servico: string
atestado.endereco_obra: string
atestado.data_inicio: date | null
atestado.data_fim: date | null
atestado.valor: decimal | null
atestado.tem_timbre: boolean
atestado.assinatura.presente: boolean
atestado.assinatura.nome_assinante: string
atestado.assinatura.crea_assinante: string | null
atestado.assinatura.cpf_assinante: string | null
atestado.assinatura.tipo: "digital_icp" | "digital_outro" | "visual" | "ausente"
atestado.assinatura.certificado_valido: boolean | null
atestado.assinatura.documento_integro: boolean | null
atestado.assinatura.suspeita_copia: boolean
```

### 9.3 — Dados extraídos da ART

```
art.numero: string
art.nome_profissional: string
art.cpf: string
art.crea: string
art.empresa_executora: string | null
art.objeto_servico: string
art.endereco_obra: string
art.data_inicio: date
art.data_fim: date
art.valor: decimal | null
art.tipo_servico: string[]
```

### 9.4 — Metadados do documento

```
metadata.software_criacao: string
metadata.data_criacao: datetime
metadata.data_modificacao: datetime
metadata.autor: string | null
metadata.num_revisoes: int | null
metadata.producer: string
metadata.is_scanned: boolean
metadata.resolucao_dpi: int | null
metadata.ela_score: float | null
```

### 9.5 — Resultado da análise

```
analise.id: uuid
analise.data: datetime
analise.veredito: "ADERENTE" | "PENDENTE" | "SUSPEITO"
analise.confianca: float                # 0.0 a 1.0
analise.itens_verificados: VerificacaoItem[]
analise.observacoes: string[]
analise.exigencias: Exigencia[]
analise.conformidade_anexo_iv: ConformidadeItem[]
```

### 9.6 — Item de verificação

```
VerificacaoItem {
  categoria: string                     # "cruzamento_dados" | "assinatura" | "metadados" | "texto" | "conformidade"
  item: string                         # Ex: "Nome do profissional"
  status: "OK" | "DIVERGENTE" | "AUSENTE" | "SUSPEITO" | "OBSERVACAO"
  valor_atestado: string | null
  valor_art: string | null
  detalhe: string
  severidade: "BLOQUEANTE" | "ALERTA" | "INFO"
}
```

### 9.7 — Exigência gerada

```
Exigencia {
  codigo: string                        # Ex: "EXG-001"
  descricao: string
  fundamentacao: string                 # Referência à resolução CONFEA
  tipo: "CORREÇÃO" | "DOCUMENTO_ADICIONAL" | "ESCLARECIMENTO"
}
```

---

## 10. PIPELINE MVP (Fluxo de processamento)

```
ENTRADA
  └─ Par de arquivos: ART (PDF) + Atestado (PDF/imagem)
       │
       ▼
FASE 1: INGESTÃO
  ├─ Detectar tipo de arquivo (PDF nativo vs escaneado vs imagem)
  ├─ Extrair metadados do arquivo
  └─ Armazenar em memória
       │
       ▼
FASE 2: EXTRAÇÃO
  ├─ Se PDF nativo → pdfplumber/PyMuPDF
  ├─ Se escaneado/imagem → Tesseract OCR
  ├─ NER com spaCy → nomes, CPF, CNPJ, datas, endereços, valores
  └─ Claude API → extração semântica do objeto do serviço
       │
       ▼
FASE 3: VERIFICAÇÕES
  │
  ├─── [A] METADADOS & MANIPULAÇÃO
  │     ├─ Data criação vs data modificação
  │     ├─ Software de edição suspeito
  │     └─ ELA (Error Level Analysis)
  │
  ├─── [B] ASSINATURA
  │     ├─ Presença de assinatura
  │     ├─ Se digital → validar ICP-Brasil + integridade (pyHanko)
  │     ├─ Se visual → detectar cópia/colagem (OpenCV)
  │     ├─ CREA/CPF abaixo do nome
  │     └─ Habilitação do assinante (se possível verificar nos docs)
  │
  ├─── [C] CRUZAMENTO ATESTADO × ART
  │     ├─ Match exato: nome, CPF, CREA, CNPJ
  │     ├─ Match semântico: objeto do serviço (Claude API)
  │     ├─ Match fuzzy: endereço da obra
  │     └─ Verificar: empresa executora, datas, valores
  │
  └─── [D] TEXTO & CONFORMIDADE
        ├─ Ortografia (LanguageTool)
        ├─ Timbre presente
        └─ Checklist Anexo IV (Res. 1.137 + 1.160)
       │
       ▼
FASE 4: PARECER
  ├─ Agregar todos os resultados
  ├─ Aplicar regras de negócio
  ├─ Gerar veredito: ADERENTE / PENDENTE / SUSPEITO
  ├─ Gerar exigências (se PENDENTE)
  ├─ Calcular confiança
  └─ Gerar relatório (JSON + Markdown)
       │
       ▼
SAÍDA
  ├─ output/userN_report.json    # Dados estruturados
  └─ output/userN_report.md      # Relatório legível
```

---

## 11. BARREIRAS E RISCOS (MVP)

| # | Barreira | Mitigação |
|---|---|---|
| 1 | **OCR impreciso em documentos escaneados** | Pré-processamento com OpenCV (binarização, deskew) + verificação manual |
| 2 | **Variação de formatos de atestado** | Claude API para extração semântica flexível |
| 3 | **Tesseract com acurácia inferior ao Vision/Textract** | Aceitável para MVP. Se insuficiente, testar com Claude Vision direto |
| 4 | **Assinaturas digitais com certificados expirados** | Verificar validade na data da assinatura |
| 5 | **Comparação semântica de escopo** | Claude API para análise de compatibilidade |
| 6 | **Detecção de assinatura copiada** | ELA + template matching. Flag, não bloqueia |
| 7 | **Apenas 2 documentos de teste** | Suficiente para validar pipeline. Escalar depois |
| 8 | **Sem rede no Claude Code** | Instalar dependências antes. Claude API via SDK já disponível |

---

## 12. TÓPICOS DO SLIDE (Apresentação Figma)

### Bloco 1 — Slides Conceituais

```
Slide 01: Capa
  → "IA para Análise de CAT — CREA [Estado]"
  → Subtítulo: "Mais velocidade, segurança e consistência na emissão de Certidões"

Slide 02: O que é a CAT
  → Definição + importância
  → "Sem a CAT: sem licitações, sem contratos, sem capacidade técnica"

Slide 03: Fluxo Atual de Emissão
  → 5 passos com destaque: análise MANUAL

Slide 04: Desafio — Por que isso é um problema?
  → 4 cards: Demora, Sobrecarga, Fraude, Inconsistências

Slide 05: Visão da Solução
  → "IA como ferramenta de apoio ao analista"
  → Fluxo: Upload → IA processa → Relatório → Decisão humana
  → Rodapé: "A solução NÃO substitui o analista humano"

Slide 06: O que a IA verifica (visão macro)
  → Módulos: OCR, Metadados, Assinatura, Cruzamento, Conformidade

Slide 07: Funcionalidades diferenciais
  → Detecção de manipulação digital
  → Conformidade Anexo IV
  → Integração com SITAC (visão futura)
  → Aprendizado contínuo (visão futura)

Slide 08: Cruzamento Atestado × ART (Detalhado)
  → Tabela de campos + regras
  → Exemplo visual de divergência

Slide 09: Verificação de Assinatura (Detalhado)
  → Fluxo: tipo → validação → habilitação → declaração
  → Exemplos visuais

Slide 10: Exemplo de Exigência Gerada
  → Formato real do CREA
  → Como a IA gera automaticamente

Slide 11: Tech Stack (resumo visual)
  → Tecnologias sugeridas
  → Opções cloud vs on-premise

Slide 12: Marco Regulatório
  → Resolução 1.137/2023 + 1.160/2025
  → Conformidade com Anexo IV

Slide 13: Roadmap
  → MVP (agora): Pipeline Python, 2 usuários teste
  → V1: Frontend + integração SITAC + CNPJ
  → V2: Dashboard + scoring + aprendizado contínuo

Slide 14: Resumo / CTA
  → Benefícios consolidados
  → Próximos passos
```

### Bloco 2 — Mockups (Prints do site do CREA com rota fictícia da IA)

```
Mockup 01: Tela de login do CREA (existente)
  → Print real

Mockup 02: Tela de solicitação de CAT (existente)
  → Print real + destaque upload

Mockup 03: Upload de documentos (mockup IA)
  → Drag & drop + "Analisando..."

Mockup 04: Resultado da análise — Visão geral
  → Veredito com cor + itens verificados (✅ ❌ ⚠️)

Mockup 05: Resultado — Comparativo Atestado vs ART
  → Lado a lado com match/divergência

Mockup 06: Detecção de metadados suspeitos
  → Timeline de edição + flags

Mockup 07: Relatório do analista
  → Parecer + pontos de atenção + botões de ação

Mockup 08: Ferramenta do engenheiro (Produto B — visão futura)
  → Upload + checklist em tempo real
```

---

## 13. ROADMAP

```
┌─────────────────────────────────────────────────────────────┐
│  MVP (AGORA)                                                │
│  → Pipeline Python no Claude Code                           │
│  → 2 pares de documentos de teste                           │
│  → Validar pureza e eficácia da IA                          │
│  → Sem frontend, sem deploy, sem banco                      │
│  → Relatório em JSON + Markdown                             │
│  → Apresentação em slides (Figma)                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  V1 (FUTURO)                                                │
│  → Frontend (Next.js) — dashboard do analista               │
│  → Integração com SITAC                                     │
│  → Consulta CNPJ na Receita Federal                         │
│  → Deploy (Docker, cloud ou on-premise)                     │
│  → Banco de dados (PostgreSQL)                              │
│  → Fila de tarefas (Celery + Redis)                         │
│  → Produto B (ferramenta do engenheiro)                     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  V2 (FUTURO)                                                │
│  → Dashboard de gestão (volume, tempo, taxa de exigências)  │
│  → Scoring de risco do profissional                         │
│  → Aprendizado contínuo (feedback loop)                     │
│  → ML avançado para classificação de documentos             │
│  → API pública para outros CREAs                            │
└─────────────────────────────────────────────────────────────┘
```

---

*Este documento é a referência central do projeto. Toda decisão de implementação deve ser validada contra este contexto.*
*Marco regulatório: Resolução 1.137/2023 do CONFEA (com alterações da 1.160/2025, a partir de março/2026).*
