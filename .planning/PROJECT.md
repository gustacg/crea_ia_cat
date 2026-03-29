# CREA CAT AI

## What This Is

Pipeline Python local para análise automatizada de pedidos de Certidão de Acervo Técnico (CAT) do CREA-MA. Processa pacotes de documentos (ART + Atestado + documentos complementares como Declaração, Anuência, NF, Contrato, Relatório Fotográfico), cruza informações, detecta fraudes e gera parecer automático (ADERENTE / PENDENTE / SUSPEITO). Ferramenta de apoio ao analista humano — não substitui a decisão final do CREA.

## Core Value

Cruzamento preciso entre Atestado e ART com detecção de inconsistências e fraudes, gerando parecer confiável que reduza o tempo de análise de 15 dias para minutos.

## Requirements

### Validated

- [x] Validação de dependências e setup automatizado — Validated in Phase 1
- [x] Ingestão de documentos e classificação por tipo via GPT-4.1 — Validated in Phase 2
- [x] Análise de documento e extração de entidades via GPT-4.1 Vision — Validated in Phase 3 (human UAT pending for live GPT accuracy)
- [x] Extração de metadados PDF e validação de assinatura digital ICP-Brasil — Validated in Phase 4
- [x] Cruzamento de campos entre Atestado e ART (exato, fuzzy, semântico, intervalo de datas) — Validated in Phase 5

### Active
- [x] Verificação de documentos complementares (Declaração Art. 59 §1º, Anuência) e compliance Anexo IV — Validated in Phase 6 (human UAT pending for live API tests)
- [ ] Veredito ADERENTE/PENDENTE/SUSPEITO com exigências no formato CREA e relatórios (Phase 7)

### Out of Scope

- Frontend/interface web — MVP é apenas CLI/script
- Deploy/infraestrutura/Docker — roda local no Windows
- Banco de dados — tudo em memória/arquivos
- ELA / análise forense de imagem — overkill para 2 docs de teste, V1
- OpenCV / detecção de cópia de assinatura visual — V1
- Tesseract / spaCy / LanguageTool — substituídos por GPT-4.1
- Consulta de CNPJ na Receita Federal — apenas verifica se bate entre docs
- Integração com SITAC — MVP roda isolado

## Context

**Domínio:** A CAT (Certidão de Acervo Técnico) é o "currículo oficial" do engenheiro no CREA. Sem ela, o profissional não pode participar de licitações, comprovar experiência ou demonstrar capacidade técnica. A análise atual é 100% manual, leva até 15 dias, e é suscetível a fraudes documentais.

**Marco regulatório:**
- Resolução 1.137/2023 do CONFEA — base regulatória
- Resolução 1.160/2025 do CONFEA — alterações vigentes a partir de março/2026
- Anexo IV (Res. 1.137/2023) — dados mínimos do atestado

**Documentos de teste reais (CREA-MA):**

Par 1 — Alexandre (Engenheiro Eletricista):
- ART: MA20250929762 — Projeto 50 pontos de iluminação, R$5.000
- Atestado: Emitido por TABOCA AGRO NEGÓCIOS LTDA, assinado por Ruan (Administrador, NÃO engenheiro)
- Declaração: Alexandre declara que JF EMPREENDIMENTOS executou serviços
- Nota: Assinante é Administrador → EXIGE Declaração (Art. 59 §1º)

Par 2 — Nizo (Engenheiro Civil):
- ART: MA20250957723 — Construção civil, Aldeia indígena, Arame-MA, R$818.582
- Atestado: 32 páginas, DSEI-MA, empresa HIDRO-CLIMA
- Nota: ART diz "AR CLIMA SOLUÇÕES" mas atestado diz "HIDRO-CLIMA" → DIVERGÊNCIA

**Regras de negócio:**
- RNP e CREA são identificadores equivalentes
- Datas da ART definem INTERVALO — atestado deve estar DENTRO
- Declaração obrigatória quando assinante NÃO é engenheiro habilitado na área
- Anuência necessária em subcontratação
- Exigências no formato CREA: maiúsculas declarativas com base legal

## Constraints

- **Tech Stack**: Python 3.13 local, GPT-4.1 Vision como motor principal
- **LLM**: OpenAI GPT-4.1 (chave existente do usuário) — OCR, NER, classificação, comparação semântica, spell check, análise visual
- **PDF**: PyMuPDF para converter páginas em imagens e extrair texto nativo
- **Metadados**: pikepdf para dados que o GPT não vê
- **Assinatura Digital**: pyHanko para ICP-Brasil (validação criptográfica)
- **Ambiente**: Windows 11, sem Docker, sem deploy
- **Escala**: 2 pares de documentos de teste apenas
- **Regra de Ouro**: A IA é ferramenta de apoio — decisão final é do analista humano do CREA

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| GPT-4.1 Vision como motor principal | Faz OCR, NER, classificação, spell check, análise visual numa chamada. Substitui 8 bibliotecas separadas. | Accepted |
| Stack simplificada (5 deps em vez de 17) | Overengineering removido. Só adiciona lib quando GPT não consegue fazer. | Accepted |
| OpenAI em vez de Claude API | Usuário já possui chave OpenAI, não tem chave Anthropic | Accepted |
| Assinatura digital via pyHanko | Validação criptográfica que GPT não faz — precisa de lib dedicada | Accepted |
| ELA/OpenCV deferido para V1 | Overkill para 2 documentos de teste, alto false-positive | Deferred |
| Tesseract/spaCy/LanguageTool removidos | GPT-4.1 faz tudo isso com qualidade superior | Replaced |

## Evolution

This document evolves at phase transitions and milestone boundaries.

---
*Last updated: 2026-03-29 — Phase 6 complete: compliance.py (Declaração/Anuência verification, Anexo IV checklist, Res. 1.160/2025 hook)*
