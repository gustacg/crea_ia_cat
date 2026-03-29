---
phase: 04-metadata-digital-signature
verified: 2026-03-28T18:00:00Z
status: passed
score: 6/6 must-haves verified
gaps: []
human_verification:
  - test: "Executar main.py com os PDFs de teste reais"
    expected: "Pipeline imprime Creator/Producer por documento, mostra DECLARACAO com assinatura SIM e 1 signatário, ACT/ART com NAO"
    why_human: "Requer PDFs em disco + download da Gov-Br chain (já cacheada); não pode ser executado sem os arquivos de dados"
  - test: "Executar pytest -m integration em tests/test_integration_phase4.py"
    expected: "8 testes passam: DECLARACAO valido=True confiavel=True, ACT presente=False, saude indigena 2 assinaturas"
    why_human: "Testes de integração dependem dos PDFs reais em 'Documentos que crea recebe/' — excluídos do pytest padrão por pytest.ini"
---

# Phase 4: Metadata & Digital Signature Verification Report

**Phase Goal:** Metadados PDF extraídos com flags de anomalia, assinatura digital ICP-Brasil validada criptograficamente
**Verified:** 2026-03-28T18:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                           | Status     | Evidence                                                                                              |
|----|-------------------------------------------------------------------------------------------------|------------|-------------------------------------------------------------------------------------------------------|
| 1  | pikepdf extrai creator, producer, author, creation_date, mod_date de qualquer PDF               | VERIFIED   | `extrair_metadados()` lê todos os 5 campos do `pdf.docinfo`; 3 testes unitários cobrem extração       |
| 2  | Software suspeito (Photoshop, GIMP, Paint.NET, Inkscape) detectado nos metadados                | VERIFIED   | `detectar_anomalias()` itera `config.SOFTWARE_SUSPEITO`; spot-check confirmou mensagem pt-BR correta  |
| 3  | Datas inconsistentes (mod_date < creation_date) sinalizadas como anomalia                       | VERIFIED   | `detectar_anomalias()` compara datas com normalização de tzinfo; spot-check confirmou               |
| 4  | pyHanko detecta presença ou ausência de assinatura digital em cada PDF                          | VERIFIED   | `validar_assinaturas()` usa `reader.embedded_regular_signatures`; 3 testes unitários cobrem           |
| 5  | Assinatura digital Gov-Br validada com cadeia de confiança (trust_roots do P7B)                 | VERIFIED   | `_carregar_govbr_chain()` baixa/cacheia P7B; Gov-Br chain já cacheada em `certs/govbr-chain.p7b`     |
| 6  | Ausência de assinatura digital registrada como presente=False sem anomalia (SIGN-03)             | VERIFIED   | `ResultadoAssinatura` sem campo `anomalias`; `test_ausencia_nao_e_anomalia` verifica via `dataclass_fields` |

**Score:** 6/6 truths verified

---

### Required Artifacts

| Artifact                              | Expected                                                        | Status     | Details                                                                                     |
|---------------------------------------|-----------------------------------------------------------------|------------|---------------------------------------------------------------------------------------------|
| `crea_cat_ai/metadata.py`             | MetadadosPDF dataclass + extrair_metadados() + detectar_anomalias() | VERIFIED  | 161 linhas; exports: MetadadosPDF, extrair_metadados, detectar_anomalias, processar_documento, _parse_pdf_date |
| `tests/test_metadata.py`              | Unit tests META-01 e META-02                                    | VERIFIED   | 297 linhas, 21 funções de teste; 21 passam em 0.81s                                         |
| `crea_cat_ai/signature.py`            | ResultadoAssinatura dataclass + validar_assinaturas() + _carregar_govbr_chain() | VERIFIED | 176 linhas; sem campo `anomalias`; strict=False, KeyUsageConstraints, self_reported_timestamp |
| `tests/test_signature.py`             | Unit tests SIGN-01, SIGN-02, SIGN-03                            | VERIFIED   | 384 linhas, 11 funções de teste; 11 passam em 0.81s                                         |
| `main.py`                             | Phase 4 integration: metadata + signature no pipeline           | VERIFIED   | Linha 8: `from crea_cat_ai import metadata, signature`; linhas 92 e 94: chamadas corretas   |
| `tests/test_integration_phase4.py`    | Integration tests para metadados e assinatura em PDFs reais     | VERIFIED   | 244 linhas; 8 testes todos com `@pytest.mark.integration`; estrutura de assertions correta  |

---

### Key Link Verification

| From                        | To                     | Via                                         | Status  | Details                                                                  |
|-----------------------------|------------------------|---------------------------------------------|---------|--------------------------------------------------------------------------|
| `crea_cat_ai/metadata.py`   | `config.py`            | `config.SOFTWARE_SUSPEITO`                  | WIRED   | Linha 122: `for sw in config.SOFTWARE_SUSPEITO` — acessa lista completa  |
| `crea_cat_ai/metadata.py`   | `pikepdf`              | `pikepdf.open()` -> `pdf.docinfo`           | WIRED   | Linha 84: `with pikepdf.open(caminho_pdf) as pdf:`                       |
| `crea_cat_ai/signature.py`  | `certs/govbr-chain.p7b`| `_carregar_govbr_chain()` baixa e cacheia   | WIRED   | Cache confirmada existente em disco; lógica download + fallback presente  |
| `crea_cat_ai/signature.py`  | `pyhanko`              | `validate_pdf_signature` com ValidationContext | WIRED | Linha 161: `validation.validate_pdf_signature(sig, signer_validation_context=vc, key_usage_settings=_KUC)` |
| `main.py`                   | `crea_cat_ai/metadata.py` | `metadata.processar_documento(doc.caminho)` | WIRED | Linha 92: chamada direta para todos docs do pacote                       |
| `main.py`                   | `crea_cat_ai/signature.py` | `signature.validar_assinaturas(doc.caminho)` | WIRED | Linha 94: chamada direta para todos docs do pacote                      |

---

### Data-Flow Trace (Level 4)

| Artifact                 | Data Variable        | Source                              | Produces Real Data | Status    |
|--------------------------|----------------------|-------------------------------------|--------------------|-----------|
| `crea_cat_ai/metadata.py` | `creator, producer, author, creation_date, mod_date` | `pikepdf.open()` -> `pdf.docinfo` | Sim — lê docinfo real do PDF | FLOWING  |
| `crea_cat_ai/metadata.py` | `anomalias`          | `detectar_anomalias(m)` com `config.SOFTWARE_SUSPEITO` | Sim — checa lista real e datas reais | FLOWING |
| `crea_cat_ai/signature.py` | `presente, quantidade, signatarios` | `reader.embedded_regular_signatures` + `validate_pdf_signature` | Sim — assinaturas reais do PDF | FLOWING |
| `main.py`                | `resultados_metadata` | `metadata.processar_documento(doc.caminho)` por documento | Sim — processa cada PDF real do pacote | FLOWING |
| `main.py`                | `resultados_assinatura` | `signature.validar_assinaturas(doc.caminho)` por documento | Sim — processa cada PDF real do pacote | FLOWING |

---

### Behavioral Spot-Checks

| Behavior                                                   | Command                                                          | Result                                                                | Status  |
|------------------------------------------------------------|------------------------------------------------------------------|-----------------------------------------------------------------------|---------|
| Photoshop detectado em `creator`                           | `detectar_anomalias(MetadadosPDF(creator="Adobe Photoshop CC 2024"))` | `['Software de edição suspeito detectado: Adobe Photoshop CC 2024']` | PASS    |
| mod_date < creation_date gera anomalia de data             | `detectar_anomalias(MetadadosPDF(creation_date=2025-03-01, mod_date=2025-01-01))` | `['Data de modificação (...) anterior à criação (...)']`     | PASS    |
| pikepdf acessível                                          | `import pikepdf; print(pikepdf.__version__)`                    | `10.5.1`                                                              | PASS    |
| GOVBR_CHAIN_URL correto e cache existente                  | `GOVBR_CHAIN_URL`; `GOVBR_CHAIN_CACHE.exists()`                 | URL correta; cache existente em `certs/govbr-chain.p7b`              | PASS    |
| Todos os 32 testes unitários passam                        | `pytest tests/test_metadata.py tests/test_signature.py -v`      | `32 passed, 4 deselected in 0.81s`                                   | PASS    |
| Todos os 63 testes da suite passam sem regressão           | `pytest tests/ -m "not integration" -q`                         | `63 passed, 16 deselected in 3.48s`                                  | PASS    |
| Imports de todos os módulos                                | `from main import main`                                         | `main import OK`                                                      | PASS    |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                                          | Status      | Evidence                                                                 |
|-------------|-------------|--------------------------------------------------------------------------------------|-------------|--------------------------------------------------------------------------|
| META-01     | 04-01, 04-03 | pikepdf extrai metadados do PDF (data criação, mod, software, autor)                | SATISFIED   | `extrair_metadados()` lê `/Creator`, `/Producer`, `/Author`, `/CreationDate`, `/ModDate`; 3 testes unitários passam |
| META-02     | 04-01, 04-03 | Pipeline detecta anomalias (software suspeito, datas inconsistentes)                 | SATISFIED   | `detectar_anomalias()` verifica `config.SOFTWARE_SUSPEITO` e datas; spot-checks confirmam respostas corretas |
| SIGN-01     | 04-02, 04-03 | pyHanko detecta presença/ausência de assinatura digital em PDFs                     | SATISFIED   | `validar_assinaturas()` verifica `embedded_regular_signatures`; retorna `presente=True/False` |
| SIGN-02     | 04-02, 04-03 | pyHanko valida certificados ICP-Brasil (cadeia, validade, integridade)               | SATISFIED   | `ValidationContext` com `trust_roots` da chain Gov-Br; `strict=False`; `KeyUsageConstraints(digital_signature)`; `moment=self_reported_timestamp` |
| SIGN-03     | 04-02, 04-03 | Ausência de assinatura tratada como estado válido (não gera SUSPEITO)                | SATISFIED   | `ResultadoAssinatura` sem campo `anomalias` (verificado via `dataclass_fields`); `presente=False` é retorno limpo |

Nenhum requisito órfão: todos os 5 IDs declarados nos PLANs estão cobertos e mapeados em REQUIREMENTS.md com status "Complete".

---

### Anti-Patterns Found

| File     | Line | Pattern              | Severity | Impact                                                                 |
|----------|------|----------------------|----------|------------------------------------------------------------------------|
| `main.py` | 114 | `# Phases 5-7: placeholders` | Info | Comentário informativo para fases futuras; não afeta funcionalidade da Phase 4 |

As ocorrências de `return None` em `metadata.py` (linhas 41, 50, 69) são retornos legítimos da função `_parse_pdf_date` para entradas vazias ou inválidas — não são stubs. As ocorrências de `return [], []` em `signature.py` (linhas 82, 98) são fallbacks explícitos para falha de download/parse do P7B — documentados em pt-BR e sem impacto crítico (pipeline continua com `confiavel=False`).

---

### Human Verification Required

#### 1. Pipeline completo com PDFs reais

**Test:** Executar `python main.py` no diretório do projeto com os PDFs de teste em `Documentos que crea recebe/`
**Expected:** Pipeline imprime seção "Fase 3: Metadados e Assinatura Digital" com uma linha por documento; DECLARACAO mostra `Assinatura digital: SIM` com 1 signatário; ART e ACT mostram `Assinatura digital: NAO`; nenhum PDF de teste deve exibir linha `ANOMALIA` (software suspeito)
**Why human:** Requer execução do pipeline completo com os PDFs reais em disco; não testável programaticamente sem os arquivos de dados

#### 2. Testes de integração com PDFs reais

**Test:** Executar `python -m pytest tests/test_integration_phase4.py -m integration -v --timeout=60`
**Expected:** 8 testes passam: `test_sig_declaracao_assinada` confirma `valido=True, confiavel=True`; `test_sig_saude_indigena_duas_assinaturas` confirma `quantidade=2`; `test_meta_sem_software_suspeito` confirma lista limpa
**Why human:** Requer PDFs reais em disco; excluídos do pytest padrão via pytest.ini; foram executados durante o desenvolvimento (SUMMARY relata 8/8 passando com 0 skipped)

---

### Gaps Summary

Nenhum gap encontrado. Todos os 6 must-haves foram verificados e confirmados no código real:

- `crea_cat_ai/metadata.py` e `crea_cat_ai/signature.py` são implementações completas (não stubs)
- 32 testes unitários passam; 63 testes da suite completa passam sem regressão
- Todos os 5 requisitos (META-01, META-02, SIGN-01, SIGN-02, SIGN-03) têm evidência de implementação
- Pipeline em `main.py` chama `metadata.processar_documento()` e `signature.validar_assinaturas()` para todos os documentos do pacote e inclui resultados no dict de retorno
- Gov-Br chain cacheada confirma que a integração criptográfica já foi exercida

---

_Verified: 2026-03-28T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
