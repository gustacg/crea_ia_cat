<!-- GSD:project-start source:PROJECT.md -->
## Project

**CREA CAT AI**

Pipeline Python local para análise automatizada de pedidos de Certidão de Acervo Técnico (CAT) do CREA-MA. Processa pacotes de documentos (ART + Atestado + documentos complementares como Declaração, Anuência, NF, Contrato, Relatório Fotográfico), cruza informações, detecta fraudes e gera parecer automático (ADERENTE / PENDENTE / SUSPEITO). Ferramenta de apoio ao analista humano — não substitui a decisão final do CREA.

**Core Value:** Cruzamento preciso entre Atestado e ART com detecção de inconsistências e fraudes, gerando parecer confiável que reduza o tempo de análise de 15 dias para minutos.

### Constraints

- **Tech Stack**: Python 3.13 local, sem servidores externos (exceto OpenAI API)
- **Motor IA**: OpenAI GPT-4.1 com Vision (chave existente do usuário) — faz 80% do trabalho: OCR, extração de entidades, classificação de documentos, comparação semântica, verificação ortográfica, análise visual
- **PDF → Imagem**: PyMuPDF para converter páginas em imagens pro GPT Vision e extrair texto nativo
- **Metadados PDF**: pikepdf para dados que o GPT não vê (data criação, software editor)
- **Assinatura Digital**: pyHanko para validação criptográfica ICP-Brasil (certificado, cadeia de confiança)
- **Ambiente**: Windows 11, sem Docker, sem deploy
- **Escala**: 2 pares de documentos de teste apenas
- **Regra de Ouro**: A IA é ferramenta de apoio — decisão final é do analista humano do CREA
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

### Filosofia: GPT-4.1 faz o trabalho pesado

A stack anterior era overengineered — 17 bibliotecas separadas (Tesseract, spaCy, LanguageTool, OpenCV, etc.) pra fazer o que uma chamada de API do GPT-4.1 Vision já faz nativamente. A stack do MVP usa GPT-4.1 como motor principal e adiciona bibliotecas SOMENTE para o que o GPT literalmente não consegue fazer.

### Core Stack (MVP)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| openai (Python SDK) | latest | GPT-4.1 API com Vision | Motor principal — OCR, NER, classificação, comparação semântica, spell check, análise visual de assinaturas e timbres. Uma chamada faz o que 8 bibliotecas faziam. |
| PyMuPDF (`pymupdf`) | 1.27.2.2 | PDF → imagens, extração de texto nativo | Converte páginas PDF em imagens base64 para o GPT Vision. Também extrai texto nativo (mais rápido/barato que Vision para PDFs com texto). Import: `import pymupdf` |
| pikepdf | 10.5.1 | Metadados PDF | Extrai data de criação, data de modificação, software criador, autor — sinais de fraude que o GPT não tem acesso. Powered by QPDF C++. |
| pyHanko | 0.34.1 | Assinatura digital ICP-Brasil | Única lib Python production-grade para validação de assinatura PDF (AdES/ETSI). Valida: cadeia de certificados, integridade, revogação (CRL). |
| Pillow | latest | Manipulação de imagens | Prepara imagens para Vision API, conversão de formato. |

### Dependências Transitivas (instaladas automaticamente)

| Package | Pulled by | Purpose |
|---------|-----------|---------|
| cryptography | pyHanko | Primitivas criptográficas, parsing X.509 |
| pyhanko-certvalidator | pyHanko | Validação de cadeia de certificados RFC 5280 |

### O que o GPT-4.1 Vision faz (substituindo bibliotecas separadas)

| Tarefa | Antes (overengineered) | Agora (GPT-4.1) |
|--------|----------------------|------------------|
| OCR de documentos escaneados | Tesseract 5 + pytesseract + pdf2image + Poppler | GPT-4.1 Vision lê a imagem diretamente |
| Extração de entidades (nome, CPF, CNPJ, CREA) | spaCy pt_core_news_lg + regex patterns | GPT-4.1 extrai com prompt estruturado |
| Classificação de tipo de documento | Heurísticas custom | GPT-4.1 classifica com contexto |
| Comparação semântica de escopos | Chamada GPT-4o separada | Já incluso na análise principal |
| Verificação ortográfica | LanguageTool + Java JRE | GPT-4.1 verifica nativamente |
| Detecção de timbre/logo | OpenCV template matching | GPT-4.1 Vision vê e descreve |
| Presença de assinatura visual | OpenCV + Pillow | GPT-4.1 Vision detecta e descreve |
| ELA (Error Level Analysis) | OpenCV + Pillow JPEG re-save | Deferido para V1 — overkill pro MVP |

### Assinaturas — Dois Tipos Distintos

**Assinatura Digital (ICP-Brasil):** Certificado criptográfico embutido no PDF. pyHanko valida matematicamente — cadeia de confiança, integridade do documento, status de revogação. Resultado binário: válida ou inválida. Confiável.

**Assinatura Visual (imagem no documento):** GPT-4.1 Vision verifica: presença de assinatura, nome/CREA/CPF abaixo, aparência geral. NÃO faz análise forense pixel a pixel. Suficiente pro MVP. Detecção de cópia/colagem com OpenCV fica para V1.

### ICP-Brasil Setup

- Download root CA bundle: `https://acraiz.icpbrasil.gov.br/`
- Configure pyHanko com `trust: /path/to/icp-brasil-chain.pem`
- CRL é o mecanismo primário de revogação (OCSP só no nível sub-CA)
- MVP aceita CRL staleness até 24 horas (offline validation)

### Deferido para V1

| Feature | Biblioteca | Razão |
|---------|-----------|-------|
| ELA (Error Level Analysis) | OpenCV + Pillow | Overkill para 2 docs de teste, alto false-positive rate |
| Detecção de cópia/colagem de assinatura | OpenCV | Requer base de comparação cruzada |
| NER com modelo treinado | spaCy / BERTimbau | GPT-4.1 já extrai entidades com qualidade superior |
| Spell check offline | LanguageTool | Elimina dependência Java; GPT-4.1 verifica nativamente |

### requirements.txt (MVP)

```
openai
pymupdf>=1.27.0
pikepdf>=10.0
pyHanko>=0.34
Pillow
```
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

- Sempre usar `import pymupdf` (não `import fitz`)
- OpenAI API key via variável de ambiente `OPENAI_API_KEY`
- Modelo padrão: `gpt-4.1` para tarefas principais
- Responses API com structured output (JSON schema) para extração de dados
- Todas as mensagens de log e output em português (pt-BR)
- Paths usando `pathlib.Path` (compatibilidade Windows)
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

### Pipeline Flow

```
Documentos (PDFs)
  → PyMuPDF (páginas → imagens + texto nativo)
  → GPT-4.1 Vision (classificação, OCR, entidades, análise visual)
  → pikepdf (metadados PDF)
  → pyHanko (assinatura digital ICP-Brasil)
  → GPT-4.1 (cruzamento, compliance, veredito)
  → Relatório JSON + Markdown
```

### Módulos

```
crea_cat_ai/
├── __init__.py
├── ingestion.py      # Aceitar PDFs, converter páginas em imagens
├── analysis.py       # GPT-4.1 Vision — classificar, extrair, analisar por documento
├── metadata.py       # pikepdf — metadados PDF
├── signature.py      # pyHanko — assinatura digital ICP-Brasil
├── matching.py       # GPT-4.1 — cruzamento Atestado vs ART
├── compliance.py     # GPT-4.1 — Anexo IV, Art. 59 §1º, Res. 1.160/2025
├── verdict.py        # Scoring, veredito, exigências
└── report.py         # JSON + Markdown output
config.py             # Thresholds e configurações
setup_check.py        # Validação de dependências
main.py               # Entry point
```
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
