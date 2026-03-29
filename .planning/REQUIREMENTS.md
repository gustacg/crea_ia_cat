# Requirements: CREA CAT AI

**Defined:** 2026-03-28
**Revised:** 2026-03-28 — Stack simplificada (GPT-4.1 Vision como motor principal)
**Core Value:** Cruzamento preciso entre Atestado, ART e documentos complementares com detecção de inconsistências e fraudes, gerando parecer confiável no formato real do CREA.

## v1 Requirements

### Environment Setup

- [x] **SETUP-01**: Pipeline valida automaticamente todas as dependências antes de rodar (OpenAI API key, PyMuPDF, pikepdf, pyHanko, Pillow)
- [x] **SETUP-02**: `pip install -r requirements.txt` instala todas as dependências Python sem conflitos no Windows 11
- [x] **SETUP-03**: Thresholds e parâmetros do pipeline são configuráveis via arquivo config.py

### Document Ingestion & Classification

- [x] **INGS-01**: Pipeline aceita pacote de documentos como entrada (diretório com PDFs)
- [x] **INGS-02**: PyMuPDF converte cada página em imagem (para GPT Vision) e extrai texto nativo quando disponível
- [x] **INGS-03**: GPT-4.1 classifica automaticamente tipo de documento: ART, Atestado, Declaração, Anuência, NF, Contrato, Relatório Fotográfico
- [x] **INGS-04**: Pipeline aceita múltiplos documentos complementares opcionais por par

### Document Analysis & Entity Extraction

- [x] **ANAL-01**: GPT-4.1 Vision extrai entidades estruturadas: CPF, CNPJ, CREA, RNP, nomes, organizações, datas, endereços, escopo
- [x] **ANAL-02**: Pipeline trata RNP e CREA como identificadores equivalentes na comparação
- [x] **ANAL-03**: GPT-4.1 verifica ortografia do atestado (ignorando termos técnicos de engenharia)
- [x] **ANAL-04**: GPT-4.1 Vision detecta presença de timbre/logo da contratante no atestado
- [x] **ANAL-05**: GPT-4.1 Vision detecta assinatura visual e extrai nome, cargo, CREA/CPF do assinante
- [x] **ANAL-06**: Pipeline identifica quando assinante NÃO é engenheiro habilitado na área do serviço

### Metadata & Digital Signature

- [x] **META-01**: pikepdf extrai metadados do PDF (data criação, data modificação, software criador, autor)
- [x] **META-02**: Pipeline detecta anomalias em metadados (software de edição suspeito, datas inconsistentes)
- [x] **SIGN-01**: pyHanko detecta presença/ausência de assinatura digital em PDFs
- [x] **SIGN-02**: pyHanko valida certificados ICP-Brasil (cadeia de confiança, validade, integridade)
- [x] **SIGN-03**: Ausência de assinatura digital tratada como estado válido (não gera SUSPEITO sozinha)

### Cross-Document Matching

- [x] **XREF-01**: CPF, CNPJ, CREA/RNP comparados com match exato (após normalização RNP/CREA)
- [x] **XREF-02**: Nomes e empresas comparados com tolerância a variações via GPT-4.1
- [x] **XREF-03**: Endereço da obra comparado com tolerância a variações de formatação
- [x] **XREF-04**: Datas do atestado validadas como DENTRO do intervalo de datas da ART
- [x] **XREF-05**: Valores financeiros e número de contrato comparados quando presentes
- [x] **XREF-06**: Escopo/objeto do serviço comparado semanticamente via GPT-4.1
- [x] **XREF-07**: Empresa executora/contratada comparada entre documentos

### Complementary Documents & Compliance

- [x] **CDOC-01**: Pipeline verifica se Declaração é necessária (assinante não é engenheiro habilitado)
- [x] **CDOC-02**: Declaração verificada: engenheiro declarante da área correta, CREA válido
- [x] **CDOC-03**: Anuência verificada em casos de subcontratação
- [x] **CDOC-04**: Dados da Declaração cruzados com ART e Atestado
- [x] **COMP-01**: Conformidade com Anexo IV da Resolução 1.137/2023 (6 categorias de dados)
- [x] **COMP-02**: Alterações da Resolução 1.160/2025 aplicadas
- [x] **COMP-03**: Art. 59 §1º (Declaração de profissional habilitado) enforced

### Verdict & Report

- [ ] **VERD-01**: Veredito ADERENTE/PENDENTE/SUSPEITO com score de confiança (0.0 a 1.0)
- [ ] **VERD-02**: Lista de itens verificados com status (OK/DIVERGENTE/AUSENTE/SUSPEITO)
- [ ] **VERD-03**: Exigências automáticas no formato real do CREA (maiúsculas, base legal)
- [ ] **VERD-04**: Relatório estruturado em JSON
- [ ] **VERD-05**: Relatório legível em Markdown
- [ ] **VERD-06**: Pipeline processa os 2 pares reais de teste e gera relatórios em output/

## v2 Requirements (Deferido)

- **VISA-01**: ELA (Error Level Analysis) para detectar manipulação em imagens
- **VISA-02**: Detecção de cópia/colagem de assinatura visual via OpenCV
- **VISA-03**: Análise de metadados EXIF de fotos em relatórios fotográficos
- **FRON-01**: Dashboard web do analista
- **FRON-02**: Integração com SITAC
- **INTL-01**: Scoring de risco do profissional baseado em histórico

## Out of Scope

| Feature | Reason |
|---------|--------|
| ELA / análise forense de imagem | Overkill para 2 docs — V1 |
| OpenCV / detecção visual de cópia | Requer base de comparação — V1 |
| Tesseract / OCR local | GPT-4.1 Vision faz OCR melhor |
| spaCy / NER local | GPT-4.1 extrai entidades nativamente |
| LanguageTool / spell check local | GPT-4.1 verifica ortografia |
| Frontend/interface web | MVP é CLI/script |
| Deploy/Docker | Roda local no Windows |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SETUP-01 | Phase 1 | Complete |
| SETUP-02 | Phase 1 | Complete |
| SETUP-03 | Phase 1 | Complete |
| INGS-01 | Phase 2 | Complete |
| INGS-02 | Phase 2 | Complete |
| INGS-03 | Phase 2 | Complete |
| INGS-04 | Phase 2 | Complete |
| ANAL-01 | Phase 3 | Complete |
| ANAL-02 | Phase 3 | Complete |
| ANAL-03 | Phase 3 | Complete |
| ANAL-04 | Phase 3 | Complete |
| ANAL-05 | Phase 3 | Complete |
| ANAL-06 | Phase 3 | Complete |
| META-01 | Phase 4 | Complete |
| META-02 | Phase 4 | Complete |
| SIGN-01 | Phase 4 | Complete |
| SIGN-02 | Phase 4 | Complete |
| SIGN-03 | Phase 4 | Complete |
| XREF-01 | Phase 5 | Complete |
| XREF-02 | Phase 5 | Complete |
| XREF-03 | Phase 5 | Complete |
| XREF-04 | Phase 5 | Complete |
| XREF-05 | Phase 5 | Complete |
| XREF-06 | Phase 5 | Complete |
| XREF-07 | Phase 5 | Complete |
| CDOC-01 | Phase 6 | Complete |
| CDOC-02 | Phase 6 | Complete |
| CDOC-03 | Phase 6 | Complete |
| CDOC-04 | Phase 6 | Complete |
| COMP-01 | Phase 6 | Complete |
| COMP-02 | Phase 6 | Complete |
| COMP-03 | Phase 6 | Complete |
| VERD-01 | Phase 7 | Pending |
| VERD-02 | Phase 7 | Pending |
| VERD-03 | Phase 7 | Pending |
| VERD-04 | Phase 7 | Pending |
| VERD-05 | Phase 7 | Pending |
| VERD-06 | Phase 7 | Pending |

**Coverage:** 38 v1 requirements, 38 mapped, 0 unmapped

---
*Last revised: 2026-03-28 — Stack simplificada, 7 phases*
