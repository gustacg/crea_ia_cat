# Roadmap: CREA CAT AI

## Overview

Pipeline Python que ingere pares de ART + Atestado + documentos complementares (Declaração, Anuência, NF, Contrato, Relatório Fotográfico), usa GPT-4.1 Vision como motor principal de análise, complementa com pikepdf (metadados) e pyHanko (assinatura digital ICP-Brasil), e produz um veredito ADERENTE/PENDENTE/SUSPEITO com score de confiança e exigências no formato real do CREA.

**Arquitetura simplificada:** GPT-4.1 faz 80% do trabalho (OCR, NER, classificação, comparação semântica, spell check, análise visual). Bibliotecas adicionais somente para o que o GPT não consegue fazer (metadados PDF, validação criptográfica de assinatura).

**Regras de negócio incorporadas:**
- RNP e CREA são identificadores equivalentes (mesmo número, formatos diferentes)
- Datas da ART definem um INTERVALO — datas do atestado devem estar DENTRO desse range
- Declaração é obrigatória quando assinante do atestado não é engenheiro habilitado na área (Art. 59 §1º, Res. 1.137/2023)
- Exigências geradas no formato real do CREA: declarativas em maiúsculas com base legal

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Environment Setup** — Instalar dependências (openai, pymupdf, pikepdf, pyHanko), criar config.py, setup_check.py, e estrutura do projeto (completed 2026-03-28)
- [ ] **Phase 2: Document Ingestion & Classification** — Aceitar pacotes de documentos, converter PDFs em imagens via PyMuPDF, classificar tipo (ART/Atestado/Declaração/etc) via GPT-4.1
- [ ] **Phase 3: Document Analysis & Entity Extraction** — GPT-4.1 Vision analisa cada documento: OCR, extrai entidades (CPF, CNPJ, CREA/RNP, nomes, datas, endereços, escopo), verifica ortografia, detecta timbre e assinatura visual
- [x] **Phase 4: Metadata & Digital Signature** — pikepdf extrai metadados PDF (anomalias), pyHanko valida assinatura digital ICP-Brasil (completed 2026-03-29)
- [x] **Phase 5: Cross-Document Matching** — GPT-4.1 cruza campos entre Atestado e ART: identifiers exatos, nomes fuzzy, endereços, datas (intervalo), valores, escopo semântico (completed 2026-03-29)
- [x] **Phase 6: Complementary Docs & Compliance** — Verifica Declaração (Art. 59 §1º), Anuência (subcontratação), Anexo IV checklist, Res. 1.160/2025 (completed 2026-03-29)
- [ ] **Phase 7: Verdict, Exigências & Report** — Score de confiança, veredito ADERENTE/PENDENTE/SUSPEITO, exigências no formato CREA, relatórios JSON + Markdown, teste end-to-end nos 2 pares reais

## Phase Details

### Phase 1: Environment Setup
**Goal**: Todas as dependências instaladas e validadas, estrutura do projeto criada, configurações prontas
**Depends on**: Nothing (first phase)
**Requirements**: SETUP-01, SETUP-02, SETUP-03
**Success Criteria** (what must be TRUE):
  1. `python setup_check.py` reporta todas as dependências OK: OpenAI API key, PyMuPDF, pikepdf, pyHanko, Pillow
  2. `pip install -r requirements.txt` instala sem conflitos no Windows 11 Python 3.13
  3. Thresholds do pipeline configuráveis via `config.py` sem tocar no código
  4. Estrutura de pacote `crea_cat_ai/` criada com módulos placeholder
**Plans:** 1/1 plans complete

Plans:
- [x] 01-01-PLAN.md — Project structure, dependencies, config, setup_check

### Phase 2: Document Ingestion & Classification
**Goal**: Pipeline aceita um pacote de documentos, converte cada PDF em imagens e texto, e classifica cada documento por tipo usando GPT-4.1
**Depends on**: Phase 1
**Requirements**: INGS-01, INGS-02, INGS-03, INGS-04
**Success Criteria** (what must be TRUE):
  1. Pipeline aceita diretório com PDFs e carrega todos os arquivos
  2. PyMuPDF converte cada página em imagem (para Vision) e extrai texto nativo quando disponível
  3. GPT-4.1 classifica cada documento como ART, Atestado, Declaração, Anuência, NF, Contrato, ou Relatório Fotográfico
  4. Classificação correta nos 2 pares de teste reais (5 documentos total)
**Plans:** 2 plans

Plans:
- [x] 02-01-PLAN.md — Tests + ingestion.py implementation (PDF loading, GPT classification, grouping)
- [ ] 02-02-PLAN.md — Wire main.py + live GPT-4.1 classification verification

### Phase 3: Document Analysis & Entity Extraction
**Goal**: Cada documento tem um set completo de entidades extraídas (CPF, CNPJ, CREA/RNP tratados como equivalentes, nomes, organizações, datas, endereços, escopo do serviço) + verificação ortográfica + detecção visual de timbre e assinatura
**Depends on**: Phase 2
**Requirements**: ANAL-01, ANAL-02, ANAL-03, ANAL-04, ANAL-05, ANAL-06
**Success Criteria** (what must be TRUE):
  1. GPT-4.1 Vision extrai entidades estruturadas de cada documento em formato JSON
  2. CREA e RNP são reconhecidos como identificadores equivalentes
  3. GPT-4.1 verifica ortografia do atestado e reporta erros (ignorando termos técnicos)
  4. GPT-4.1 Vision detecta presença de timbre/logo e assinatura visual com nome/CREA/CPF
  5. Assinante classificado como engenheiro habilitado ou não (cargo detectado)
**Plans:** 2 plans

Plans:
- [x] 03-01-PLAN.md — Tests + Pydantic models + analysis.py implementation (entity extraction, visual analysis, spell check, CREA/RNP normalization)
- [x] 03-02-PLAN.md — Wire main.py + live GPT-4.1 entity extraction verification

### Phase 4: Metadata & Digital Signature
**Goal**: Metadados PDF extraídos com flags de anomalia, assinatura digital ICP-Brasil validada criptograficamente
**Depends on**: Phase 2
**Requirements**: META-01, META-02, SIGN-01, SIGN-02, SIGN-03
**Success Criteria** (what must be TRUE):
  1. pikepdf extrai metadados (data criação, modificação, software, autor) de todos os documentos
  2. Anomalias detectadas: software de edição suspeito, datas inconsistentes
  3. pyHanko detecta presença/ausência de assinatura digital em cada PDF
  4. Quando presente, valida cadeia de certificados ICP-Brasil com CA bundle local
  5. Ausência de assinatura digital registrada como estado válido (não gera SUSPEITO sozinha)
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md — Tests + metadata.py (pikepdf extraction, anomaly detection)
- [x] 04-02-PLAN.md — Tests + signature.py (pyHanko validation, Gov-Br chain)
- [x] 04-03-PLAN.md — Wire main.py + integration tests on real PDFs

### Phase 5: Cross-Document Matching
**Goal**: Todos os campos sobrepostos entre Atestado e ART comparados — identifiers exatos, nomes/endereços fuzzy, escopo semântico, datas por intervalo — cada campo com status MATCH/DIVERGENTE/AUSENTE
**Depends on**: Phase 3, Phase 4
**Requirements**: XREF-01, XREF-02, XREF-03, XREF-04, XREF-05, XREF-06, XREF-07
**Success Criteria** (what must be TRUE):
  1. CPF, CNPJ, CREA/RNP comparados com match exato (após normalização)
  2. Nomes e empresas comparados com tolerância a variações (GPT-4.1 faz fuzzy matching semântico)
  3. Divergência conhecida no Par 2 ("AR CLIMA SOLUÇÕES" vs "HIDRO-CLIMA Construções") detectada
  4. Datas do atestado validadas como DENTRO do intervalo da ART
  5. Escopo do serviço comparado semanticamente via GPT-4.1
  6. Valores financeiros e número de contrato comparados quando presentes
**Plans:** 2/2 plans complete

Plans:
- [x] 05-01-PLAN.md — Tests + matching.py implementation (exact match, date interval, GPT batch fuzzy/semantic)
- [x] 05-02-PLAN.md — Wire main.py + integration tests on real PDFs

### Phase 6: Complementary Docs & Compliance
**Goal**: Declaração verificada quando necessária (Art. 59 §1º), Anuência verificada em subcontratação, Anexo IV completo, Res. 1.160/2025 aplicada
**Depends on**: Phase 3, Phase 5
**Requirements**: CDOC-01, CDOC-02, CDOC-03, CDOC-04, COMP-01, COMP-02, COMP-03
**Success Criteria** (what must be TRUE):
  1. Quando assinante não é engenheiro (detectado na Phase 3), Declaração marcada como OBRIGATÓRIA
  2. Declaração presente verificada: engenheiro declarante é da área, CREA válido
  3. Par 1 (Ruan Administrador) corretamente dispara exigência de Declaração; Declaração do Alexandre é encontrada e verificada
  4. Anexo IV checklist verificado: 6 categorias de dados obrigatórios
  5. Res. 1.160/2025 aplicada sobre base Res. 1.137/2023
**Plans**: 2 plans

Plans:
- [x] 06-01-PLAN.md — Tests + compliance.py implementation (Declaracao, Anuencia, Anexo IV, Res 1.160 hook)
- [x] 06-02-PLAN.md — Wire main.py + integration tests + human verification

### Phase 7: Verdict, Exigências & Report
**Goal**: Score de confiança calculado, veredito ADERENTE/PENDENTE/SUSPEITO gerado, exigências no formato CREA, relatórios JSON+Markdown escritos, pipeline validado end-to-end nos 2 pares reais
**Depends on**: Phase 6
**Requirements**: VERD-01, VERD-02, VERD-03, VERD-04, VERD-05, VERD-06
**Success Criteria** (what must be TRUE):
  1. Cada campo analisado tem status OK/DIVERGENTE/AUSENTE/SUSPEITO
  2. Score de confiança 0.0–1.0 com peso: CPF mismatch > erro ortográfico
  3. Veredito: ADERENTE (>=0.80), PENDENTE (0.50–0.79), SUSPEITO (<0.50)
  4. Par 2 (empresa divergente) produz PENDENTE ou SUSPEITO, nunca ADERENTE
  5. Exigências em formato CREA maiúsculo com base legal
  6. Relatórios JSON + Markdown em output/ para cada par
  7. Pipeline end-to-end roda nos 2 pares reais sem exceções
**Plans:** 3 plans

Plans:
- [ ] 07-01-PLAN.md — Tests + verdict.py (scoring, knock-outs, item consolidation, exigencias)
- [ ] 07-02-PLAN.md — Tests + report.py (JSON + Markdown report generation)
- [ ] 07-03-PLAN.md — Wire main.py + integration tests + end-to-end verification

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Environment Setup | 1/1 | Complete   | 2026-03-28 |
| 2. Document Ingestion & Classification | 0/2 | Planning complete | - |
| 3. Document Analysis & Entity Extraction | 0/2 | Planning complete | - |
| 4. Metadata & Digital Signature | 3/3 | Complete   | 2026-03-29 |
| 5. Cross-Document Matching | 2/2 | Complete   | 2026-03-29 |
| 6. Complementary Docs & Compliance | 2/2 | Complete   | 2026-03-29 |
| 7. Verdict, Exigencias & Report | 0/3 | Planning complete | - |
