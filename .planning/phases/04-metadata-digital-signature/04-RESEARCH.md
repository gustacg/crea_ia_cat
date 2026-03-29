# Phase 4: Metadata & Digital Signature — Research

**Researched:** 2026-03-28
**Domain:** pikepdf metadata extraction + pyHanko PDF signature validation (ICP-Brasil / Gov-Br PKI)
**Confidence:** HIGH — all patterns verified by running against real test PDFs on the target machine

---

## Summary

Phase 4 implements two independent modules: `metadata.py` (pikepdf) and `signature.py` (pyHanko). Both libraries are already installed (pikepdf 10.5.1, pyHanko 0.34.1) and were verified as importable on the Windows 11 Python 3.13 environment.

**Critical discovery — Gov-Br PKI, not standard ICP-Brasil:** All five test PDFs with digital signatures use certificates issued by **Gov-Br** ("AC Final do Governo Federal do Brasil v1", "AC Intermediaria do Governo Federal do Brasil v1", "Autoridade Certificadora Raiz do Governo Federal do Brasil v1") — NOT by the standard ICP-Brasil / ITI authority. The Gov-Br chain is a **separate PKI** operated by the federal government's digital identity platform. The trust bundle from `acraiz.icpbrasil.gov.br/ACcompactado.zip` does NOT contain Gov-Br roots. The correct chain must be downloaded from `http://repo.iti.br/docs/Cadeia_GovBr-der.p7b` (a PKCS7/P7B file reachable over plain HTTP, confirmed accessible from this machine).

**Three validated results from real PDFs:**
- `944678.2026__DECLARACAO__ENG_2_assinado__1_05022026162803.pdf` → 1 signature, `INTACT:TRUSTED,UNTOUCHED` when using Gov-Br trust store + `KeyUsageConstraints(key_usage={'digital_signature'})` + `revocation_mode='soft-fail'`
- `saude indigena.pdf` → 2 signatures, Sig 1 `ILLEGAL_MODIFICATIONS` (modified after certifying signature — pyHanko correctly flags), Sig 2 `INTACT:TRUSTED,UNTOUCHED`
- `944678.2026__ACT_Alexandre_B12032026101332 (1).pdf` → 0 signature fields — correctly returns no digital signature

**Primary recommendation:** Download Gov-Br P7B chain on-demand at runtime (HTTP, no SSL verification needed) and cache to `certs/govbr-chain.p7b`. Also download ICP-Brasil bundle from `acraiz.icpbrasil.gov.br` as a secondary trust source (some future documents may use standard ICP-Brasil). Use `self_reported_timestamp` as `moment=` in `ValidationContext` to handle expired-at-runtime-but-valid-at-signing certificates.

---

## Project Constraints (from CLAUDE.md)

- Tech Stack: Python 3.13, Windows 11, no Docker
- Libraries: pikepdf (metadados PDF), pyHanko (assinatura digital ICP-Brasil)
- `import pymupdf` not `import fitz`
- Paths: `pathlib.Path` sempre
- Output/logs: português (pt-BR)
- `config.py` para thresholds — `SOFTWARE_SUSPEITO` list já definida lá
- Módulos alvo: `crea_cat_ai/metadata.py` e `crea_cat_ai/signature.py` (stubs já existem)
- Entry point: `main.py` importa somente os módulos implementados por fase

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| META-01 | pikepdf extrai metadados do PDF (data criação, data modificação, software criador, autor) | `pdf.docinfo` retorna `/CreationDate`, `/ModDate`, `/Creator`, `/Producer`, `/Author` — verificado nos 5 PDFs de teste |
| META-02 | Pipeline detecta anomalias em metadados (software de edição suspeito, datas inconsistentes) | Lista `SOFTWARE_SUSPEITO` já em `config.py`; comparação de dates com `parse_pdf_date()` custom |
| SIGN-01 | pyHanko detecta presença/ausência de assinatura digital em PDFs | `enumerate_sig_fields(reader)` retorna lista de campos; `reader.embedded_regular_signatures` retorna objetos de assinatura |
| SIGN-02 | pyHanko valida certificados ICP-Brasil (cadeia de confiança, validade, integridade) | Requer Gov-Br P7B chain (`http://repo.iti.br/docs/Cadeia_GovBr-der.p7b`); `ValidationContext(trust_roots=root_certs, other_certs=intermediate_certs)`; `KeyUsageConstraints(key_usage={'digital_signature'})` obrigatório |
| SIGN-03 | Ausência de assinatura digital tratada como estado válido (não gera SUSPEITO sozinha) | Ausência é estado normal nos PDFs de ART e Atestado — campo `assinatura_digital_presente: False` deve ser registrado sem flag de anomalia |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pikepdf | 10.5.1 | Metadados PDF (DocInfo + XMP) | Instalado, único acesso programático a `/Creator`, `/Producer`, `/Author`, `/CreationDate`, `/ModDate` |
| pyHanko | 0.34.1 | Validação de assinatura digital PDF | Instalado, única lib Python production-grade para PDF signatures. Suporta AdES/ETSI, ICP-Brasil, CMS |
| pyhanko-certvalidator | (dep. de pyHanko) | Construção e validação de cadeia de certificados RFC 5280 | Instalado como dependência transitiva de pyHanko |
| asn1crypto | (dep. de pyHanko) | Parsing de estruturas ASN.1 (PKCS7, X.509, CMS) | Instalado como dependência transitiva; usado para decodificar o P7B chain |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| urllib.request | stdlib | Download do Gov-Br P7B chain | No setup inicial, se `certs/govbr-chain.p7b` não existir |
| ssl | stdlib | Contexto SSL sem verificação (somente para download do Gov-Br P7B) | HTTP nativo não precisa de SSL |
| re | stdlib | Parse de data PDF (`D:YYYYMMDDHHmmSSOHH'mm'`) | Formato tem timezone codificado com aspas, precisa de regex |
| pathlib.Path | stdlib | Todos os file paths (obrigatório per CLAUDE.md) | |

**Sem instalação adicional necessária** — todas as dependências já presentes.

---

## Architecture Patterns

### Recommended Module Structure

```
crea_cat_ai/
├── metadata.py      # pikepdf: MetadadosPDF dataclass + extrair_metadados() + detectar_anomalias()
├── signature.py     # pyHanko: ResultadoAssinatura dataclass + validar_assinaturas() + _carregar_govbr_chain()
certs/
├── govbr-chain.p7b  # Baixado em runtime se ausente — gov-br intermediate CA chain
└── icp-brasil-chain.pem  # (Opcional) ITI standard chain, para documentos fora do gov-br
```

### Pattern 1: Extração de Metadados com pikepdf

**What:** Abrir o PDF com `pikepdf.open()`, ler `pdf.docinfo`, normalizar datas, detectar anomalias.

**When to use:** Para todo PDF no `PacoteDocumentos`, independente de ter assinatura.

```python
# Source: verificado nos 5 PDFs de teste reais
import pikepdf
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import re

@dataclass
class MetadadosPDF:
    creator: Optional[str] = None
    producer: Optional[str] = None
    author: Optional[str] = None
    creation_date: Optional[datetime] = None
    mod_date: Optional[datetime] = None
    anomalias: list[str] = field(default_factory=list)

def _parse_pdf_date(date_str: str) -> Optional[datetime]:
    """Parse PDF date: D:YYYYMMDDHHmmSSOHH'mm'"""
    if not date_str:
        return None
    s = str(date_str).strip()
    if s.startswith("D:"):
        s = s[2:]
    # Normalize timezone: -03'00' -> -0300
    s = re.sub(r"([+-]\d{2})'(\d{2})'", r"\1\2", s)
    s = re.sub(r"Z$", "+0000", s)
    for fmt in ["%Y%m%d%H%M%S%z", "%Y%m%d%H%M%S"]:
        try:
            return datetime.strptime(s[:len(fmt.replace('%', 'XX').replace('X',''))], fmt)
        except ValueError:
            continue
    return None

def extrair_metadados(caminho_pdf: Path) -> MetadadosPDF:
    with pikepdf.open(caminho_pdf) as pdf:
        di = pdf.docinfo
        m = MetadadosPDF(
            creator  = str(di.get("/Creator", "")) or None,
            producer = str(di.get("/Producer", "")) or None,
            author   = str(di.get("/Author", ""))   or None,
        )
        m.creation_date = _parse_pdf_date(str(di.get("/CreationDate", "")))
        m.mod_date      = _parse_pdf_date(str(di.get("/ModDate", "")))
    return m
```

### Pattern 2: Detecção de Anomalias de Metadados

**What:** Verificar se o software criador está na lista negra e se as datas são consistentes.

```python
# Source: verificado contra config.py existente (SOFTWARE_SUSPEITO já definido lá)
import config

def detectar_anomalias(m: MetadadosPDF) -> list[str]:
    anomalias = []
    for sw in config.SOFTWARE_SUSPEITO:
        for campo in [m.creator or "", m.producer or ""]:
            if sw.lower() in campo.lower():
                anomalias.append(f"Software de edição suspeito detectado: {campo}")
    if m.creation_date and m.mod_date:
        if m.mod_date < m.creation_date:
            anomalias.append(
                f"Data de modificação ({m.mod_date}) anterior à criação ({m.creation_date})"
            )
    return anomalias
```

### Pattern 3: Carregamento do Gov-Br Trust Chain

**What:** Baixar `Cadeia_GovBr-der.p7b` do repositório ITI e parsear os certificados raiz e intermediários.

**Critical:** A chain Gov-Br é necessária para todos os PDFs de teste. O arquivo é PKCS7/DER. Download é via HTTP simples (`http://`, não `https://`). SSL não é necessário.

```python
# Source: verificado por download direto e parsing com asn1crypto
import urllib.request
from asn1crypto import cms as asn1_cms, x509 as asn1_x509
from pathlib import Path

GOVBR_CHAIN_URL = "http://repo.iti.br/docs/Cadeia_GovBr-der.p7b"
GOVBR_CHAIN_CACHE = Path("certs") / "govbr-chain.p7b"

def _carregar_govbr_chain() -> tuple[list, list]:
    """
    Retorna (root_certs, intermediate_certs) como asn1crypto Certificate objects.
    Baixa e cacheia se necessário.
    """
    if not GOVBR_CHAIN_CACHE.exists():
        GOVBR_CHAIN_CACHE.parent.mkdir(exist_ok=True)
        with urllib.request.urlopen(GOVBR_CHAIN_URL, timeout=15) as r:
            GOVBR_CHAIN_CACHE.write_bytes(r.read())

    p7b_data = GOVBR_CHAIN_CACHE.read_bytes()
    content_info = asn1_cms.ContentInfo.load(p7b_data)
    signed_data = content_info["content"]
    all_certs = [cc.chosen for cc in signed_data["certificates"]]

    root_certs  = [c for c in all_certs if c.subject.human_friendly == c.issuer.human_friendly]
    other_certs = [c for c in all_certs if c not in root_certs]
    return root_certs, other_certs
```

### Pattern 4: Detecção e Validação de Assinatura Digital

**What:** Detectar campos de assinatura, validar cada uma com o trust store Gov-Br.

**Critical details (todos verificados por testes reais):**
1. `PdfFileReader(f, strict=False)` — obrigatório. `strict=True` falha em PDFs híbridos (hybrid-reference files) que são comuns nos PDFs Gov-Br.
2. `KeyUsageConstraints(key_usage={'digital_signature'})` — obrigatório. Certificados Gov-Br têm `key_usage=digital_signature` (sem `non_repudiation`). pyHanko por padrão exige `non_repudiation`, o que causa `InvalidCertificateError` sem este override.
3. `revocation_mode='soft-fail'` — necessário para validação offline. CRL não é baixada em runtime (MVP sem internet obrigatório).
4. `moment=sig.self_reported_timestamp` — necessário para certificados que expiraram depois da data de assinatura. Sem isso, certs expirados produzem `ExpiredError` mesmo que o documento tenha sido assinado enquanto o cert era válido. Exemplo real: `saude indigena.pdf` Sig1 expirou em 2026-02-26 mas foi assinado em 2026-01-20.

```python
# Source: verificado contra todos os 5 PDFs de teste com resultado correto
from pyhanko.sign import validation
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.fields import enumerate_sig_fields
from pyhanko.sign.validation.settings import KeyUsageConstraints
from pyhanko_certvalidator.context import ValidationContext
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

@dataclass
class ResultadoAssinatura:
    presente: bool
    quantidade: int = 0
    # Por assinatura:
    signatarios: list[dict] = field(default_factory=list)
    # Cada dict: {nome, emissor, valido, integro, confiavel, sumario, erro}

_KUC = KeyUsageConstraints(key_usage={"digital_signature"})

def validar_assinaturas(caminho_pdf: Path) -> ResultadoAssinatura:
    root_certs, other_certs = _carregar_govbr_chain()

    with open(caminho_pdf, "rb") as f:
        reader = PdfFileReader(f, strict=False)
        fields = list(enumerate_sig_fields(reader))
        sigs   = reader.embedded_regular_signatures

    if not sigs:
        return ResultadoAssinatura(presente=False)

    resultado = ResultadoAssinatura(presente=True, quantidade=len(sigs))

    for sig in sigs:
        cert = sig.signer_cert
        moment = sig.self_reported_timestamp  # pode ser None — ValidationContext aceita None
        entry: dict = {
            "nome":     cert.subject.human_friendly if cert else "Desconhecido",
            "emissor":  cert.issuer.human_friendly  if cert else "Desconhecido",
            "valido":   False,
            "integro":  False,
            "confiavel": False,
            "sumario":  "",
            "erro":     None,
        }
        try:
            vc = ValidationContext(
                trust_roots=root_certs,
                other_certs=other_certs,
                allow_fetching=False,
                moment=moment,
                revocation_mode="soft-fail",
            )
            r = validation.validate_pdf_signature(sig, signer_validation_context=vc, key_usage_settings=_KUC)
            entry["valido"]    = r.valid
            entry["integro"]   = r.intact
            entry["confiavel"] = r.trusted
            entry["sumario"]   = r.summary()
        except Exception as e:
            entry["erro"] = f"{type(e).__name__}: {e}"
        resultado.signatarios.append(entry)

    return resultado
```

### Pattern 5: Integração no main.py

```python
# main.py — adicionar após Phase 3
from crea_cat_ai import metadata, signature

print("--- Fase 3: Metadados e Assinatura Digital ---")
resultados_metadata = {}
resultados_assinatura = {}
for doc in [pacote.art, pacote.atestado] + pacote.complementares:
    if doc is None:
        continue
    resultados_metadata[doc.tipo.value]    = metadata.processar_documento(doc.caminho)
    resultados_assinatura[doc.tipo.value]  = signature.validar_assinaturas(doc.caminho)
```

### Anti-Patterns to Avoid

- **Usar `PdfFileReader(f)` sem `strict=False`:** Causa `SignatureValidationError: Settings do not permit validation of signatures in hybrid-reference files` nos PDFs Gov-Br. SEMPRE usar `strict=False`.
- **Omitir `KeyUsageConstraints`:** Causa `InvalidCertificateError: The active key usage policy requires at least one of the key usage extensions non repudiation to be present.` — os certs Gov-Br só têm `digital_signature`.
- **Validar sem `moment=`:** Causa `ExpiredError` para certs expirados que eram válidos na data de assinatura. Usar `sig.self_reported_timestamp`.
- **Usar `validate_pdf_ltv_signature`:** Falha com `SignatureValidationError: LTV signatures require a trusted timestamp.` — os PDFs de teste não têm timestamp de autoridade. Usar `validate_pdf_signature`.
- **Tratar ausência de assinatura como anomalia (SIGN-03):** Atestado e ART não têm assinatura digital nos PDFs de teste — isso é normal. Registrar `presente: False` sem flag.
- **Tentar converter os `.crt` do ACcompactado.zip com `cryptography.x509.load_der_x509_certificate`:** Os arquivos são PEM (não DER). Mas o bundle ITI não tem a chain Gov-Br de qualquer forma.
- **Chamar `ValidationContext(trust_roots=bytes_list)`:** pyhanko-certvalidator espera objetos `asn1crypto.x509.Certificate`, não bytes ou objetos `cryptography`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parsing de assinatura PDF (CMS/PKCS7) | Custom parser de bytes ASN.1 | `pyHanko` + `asn1crypto` | Centenas de edge cases: certs embutidos, refs cruzadas, revisões, hybrid-reference |
| Validação de cadeia X.509 | Custom RFC 5280 | `pyhanko-certvalidator.ValidationContext` | Expiração, revogação, path building — complexity enorme |
| Parse de data PDF (`D:YYYYMMDDHHmmSSOHH'mm'`) | Hardcoded strptime | Função `_parse_pdf_date()` custom com regex | O formato tem timezone com aspas simples que nenhuma stdlib suporta direto |
| Detecção de campos de assinatura | Percorrer PDF manualmente | `enumerate_sig_fields(reader)` | Há múltiplos tipos de campos; a função lida com todos |

---

## Common Pitfalls

### Pitfall 1: `strict=True` em PDFs Gov-Br (hybrid-reference)
**What goes wrong:** `SignatureValidationError: Settings do not permit validation of signatures in hybrid-reference files.`
**Why it happens:** PDFs Gov-Br são gerados com hybrid cross-reference (tabela xref + stream xref simultâneos). O strict mode do pyHanko rejeita esses arquivos.
**How to avoid:** `PdfFileReader(f, strict=False)` sempre.
**Warning signs:** O erro menciona "hybrid-reference files".

### Pitfall 2: `non_repudiation` ausente nos certs Gov-Br
**What goes wrong:** `InvalidCertificateError: The active key usage policy requires at least one of the key usage extensions non repudiation to be present.`
**Why it happens:** Certificados Gov-Br têm `key_usage = digital_signature` mas não `non_repudiation`. pyHanko 0.34 exige `non_repudiation` por padrão para assinaturas.
**How to avoid:** `key_usage_settings=KeyUsageConstraints(key_usage={'digital_signature'})` no `validate_pdf_signature()`.
**Warning signs:** O erro menciona "non repudiation".

### Pitfall 3: Certs expirados após a data de assinatura
**What goes wrong:** `ExpiredError: The path could not be validated because the end-entity certificate expired ...`
**Why it happens:** Certificados Gov-Br têm validade curta (~3 meses). Se o PDF foi assinado há meses, o cert pode ter expirado.
**How to avoid:** `moment=sig.self_reported_timestamp` no `ValidationContext`. Valida como se estivesse na data da assinatura.
**Warning signs:** A data de expiração no erro é recente; `sig.self_reported_timestamp` mostra data anterior à expiração.

### Pitfall 4: Chain ICP-Brasil não contém certs Gov-Br
**What goes wrong:** `PathBuildingError: Unable to build a validation path for the certificate ... no issuer matching "AC Final do Governo Federal do Brasil v1" was found`
**Why it happens:** O bundle `ACcompactado.zip` do ITI contém certs ICP-Brasil regulares, mas NOT a chain Gov-Br. São PKIs diferentes.
**How to avoid:** Baixar o `Cadeia_GovBr-der.p7b` de `http://repo.iti.br/docs/Cadeia_GovBr-der.p7b` e usar como trust store.
**Warning signs:** O issuer contém "Governo Federal do Brasil" ou "Gov-Br".

### Pitfall 5: Acesso SSL ao ITI com Python ssl padrão
**What goes wrong:** `URLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate`
**Why it happens:** O servidor `acraiz.icpbrasil.gov.br` usa um certificado que não está no bundle ca-certificates do Windows nativo do Python.
**How to avoid:** Para `https://acraiz.icpbrasil.gov.br`, criar `ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE`. Para o Gov-Br P7B (`http://`), não há SSL — não precisa de workaround.
**Warning signs:** O erro menciona `CERTIFICATE_VERIFY_FAILED`.

### Pitfall 6: pikepdf.docinfo retorna objetos pikepdf, não strings puras
**What goes wrong:** Comparações diretas com strings falham; `.lower()` pode lançar AttributeError.
**Why it happens:** `pdf.docinfo.get("/Creator")` retorna um objeto `pikepdf.String` ou `None`.
**How to avoid:** Sempre `str(di.get("/Creator", ""))` antes de usar.

### Pitfall 7: `ILLEGAL_MODIFICATIONS` no saude indigena.pdf Sig1
**What goes wrong:** Sig1 retorna `INTACT:TRUSTED,EXTENDED_WITH_OTHER,ILLEGAL_MODIFICATIONS`
**Why it happens:** O documento foi modificado após uma certification signature (MDP). pyHanko detecta corretamente que há conteúdo adicionado depois da certificação. Sig2 (que aprovou a modificação) fica `INTACT:TRUSTED,UNTOUCHED`.
**How to avoid:** Não é um bug — é detecção correta de modificação. Registrar como suspeito no veredito.
**Warning signs:** `ILLEGAL_MODIFICATIONS` no sumário da assinatura.

---

## Code Examples

### Leitura completa de metadados (padrão verificado)
```python
# Source: verificado contra todos os 5 PDFs de teste
import pikepdf
from pathlib import Path

with pikepdf.open(Path("documento.pdf")) as pdf:
    di = pdf.docinfo
    creator      = str(di.get("/Creator",      "")) or None
    producer     = str(di.get("/Producer",     "")) or None
    author       = str(di.get("/Author",       "")) or None
    creation_raw = str(di.get("/CreationDate", "")) or None
    mod_raw      = str(di.get("/ModDate",      "")) or None
```

### Resultado de assinatura observado nos PDFs de teste
| PDF | Campos | Sigs | Resultado |
|-----|--------|------|-----------|
| ACT_Alexandre.pdf | 0 | 0 | `presente: False` |
| DECLARACAO_assinado.pdf | 1 | 1 | `INTACT:TRUSTED,UNTOUCHED` |
| MA20250929762.pdf | 0 | 0 | `presente: False` |
| MA20250957723.pdf | 0 | 0 | `presente: False` |
| saude_indigena.pdf | 2 | 2 | Sig1: `INTACT:TRUSTED,EXTENDED_WITH_OTHER,ILLEGAL_MODIFICATIONS`, Sig2: `INTACT:TRUSTED,UNTOUCHED` |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pyHanko trust store via `yml` config file | `ValidationContext(trust_roots=..., other_certs=...)` em código | pyHanko 0.20+ | Mais flexível, sem arquivo de config externo |
| `validate_pdf_ltv_signature` para todos | `validate_pdf_signature` para MVPs sem timestamp | pyHanko 0.25+ | LTV requer RFC 3161 timestamp — inexistente nos PDFs de teste |
| ICP-Brasil como único trust store | Gov-Br chain separada | Gov-Br criado ~2020 | Documentos assinados via login.gov.br usam PKI diferente |

---

## Open Questions

1. **Download offline do Gov-Br chain**
   - What we know: O download de `http://repo.iti.br/docs/Cadeia_GovBr-der.p7b` funciona sem SSL nesta máquina
   - What's unclear: Se a máquina não tiver internet, o download falha. O planner deve incluir um Wave 0 para criar o cache `certs/govbr-chain.p7b` ou uma estratégia de fallback
   - Recommendation: Tentar download; se falhar, logar aviso e retornar `confiavel: False` com explicação — não quebrar o pipeline

2. **Documentos com ICP-Brasil verdadeiro (não Gov-Br)**
   - What we know: Os 5 PDFs de teste usam Gov-Br. O bundle ITI tem 170 certs para ICP-Brasil tradicional.
   - What's unclear: Se futuros documentos no CREA-MA usam ICP-Brasil padrão (certificado A1/A3 de token USB) ou sempre Gov-Br
   - Recommendation: Carregar AMBOS os trust stores (Gov-Br P7B + ICP-Brasil PEM) e tentar validação com a union — o caminho correto será construído automaticamente pelo `pyhanko-certvalidator`

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pikepdf | META-01, META-02 | ✓ | 10.5.1 | — |
| pyHanko | SIGN-01, SIGN-02 | ✓ | 0.34.1 | — |
| pyhanko-certvalidator | SIGN-02 | ✓ | (dep. transitiva) | — |
| asn1crypto | SIGN-02 | ✓ | (dep. transitiva) | — |
| http://repo.iti.br/ | SIGN-02 trust chain | ✓ (verificado) | — | Fallback: UNTRUSTED (trusted=False), log aviso |
| https://acraiz.icpbrasil.gov.br/ | ICP-Brasil bundle opcional | Parcial (HTTP OK, HTTPS SSL error) | — | Usar ssl.CERT_NONE ou só Gov-Br chain |
| `certs/` directory | Cache dos chains | Não existe ainda | — | Criar em Wave 0 ou em runtime |

**Missing dependencies with no fallback:** nenhum

**Missing dependencies with fallback:**
- Internet (para download do Gov-Br chain): fallback = UNTRUSTED com log explicativo
- `certs/govbr-chain.p7b`: criado em runtime na primeira execução

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (já configurado) |
| Config file | `pytest.ini` na raiz do projeto |
| Quick run command | `pytest tests/test_metadata.py tests/test_signature.py -v` |
| Full suite command | `pytest -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| META-01 | `extrair_metadados()` retorna campos corretos | unit (mock pikepdf) | `pytest tests/test_metadata.py::test_extrai_metadados_campos -x` | ❌ Wave 0 |
| META-01 | `extrair_metadados()` funciona nos 5 PDFs reais | integration | `pytest tests/test_metadata.py -m integration -x` | ❌ Wave 0 |
| META-02 | `detectar_anomalias()` detecta software suspeito | unit | `pytest tests/test_metadata.py::test_detecta_software_suspeito -x` | ❌ Wave 0 |
| META-02 | `detectar_anomalias()` detecta mod_date < creation_date | unit | `pytest tests/test_metadata.py::test_detecta_data_inconsistente -x` | ❌ Wave 0 |
| SIGN-01 | `validar_assinaturas()` retorna `presente=False` para PDFs sem assinatura | unit (mock PdfFileReader) | `pytest tests/test_signature.py::test_ausencia_assinatura -x` | ❌ Wave 0 |
| SIGN-01 | `validar_assinaturas()` detecta assinaturas nos PDFs reais | integration | `pytest tests/test_signature.py -m integration -x` | ❌ Wave 0 |
| SIGN-02 | `validar_assinaturas()` retorna `confiavel=True` na DECLARACAO assinada | integration | `pytest tests/test_signature.py::test_valida_declaracao_assinada -m integration` | ❌ Wave 0 |
| SIGN-03 | `ResultadoAssinatura.presente=False` não gera anomalia | unit | `pytest tests/test_signature.py::test_ausencia_nao_e_anomalia -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_metadata.py tests/test_signature.py -v`
- **Per wave merge:** `pytest -v` (suite completa)
- **Phase gate:** Suite completa green antes do `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_metadata.py` — cobre META-01, META-02
- [ ] `tests/test_signature.py` — cobre SIGN-01, SIGN-02, SIGN-03
- [ ] `certs/` directory — para cache dos CA bundles (criar em setup_check.py ou Wave 0)

---

## Sources

### Primary (HIGH confidence)
- Execução direta do código nos 5 PDFs de teste reais nesta máquina — resultados verificados empiricamente
- `pikepdf` 10.5.1 API: `pdf.docinfo`, `pdf.open_metadata()` — verificado com `help(pikepdf.Pdf.open_metadata)`
- `pyHanko` 0.34.1 API: `PdfFileReader`, `enumerate_sig_fields`, `validate_pdf_signature`, `ValidationContext`, `KeyUsageConstraints` — todos verificados por execução
- `http://repo.iti.br/docs/Cadeia_GovBr-der.p7b` — downloadado (5364 bytes, 3 certs: raiz + 2 intermediários Gov-Br)

### Secondary (MEDIUM confidence)
- ITI/SERPRO docs sobre Gov-Br vs ICP-Brasil: gov.br/governodigital e validar.iti.gov.br — distinção entre assinatura GOV.BR (avançada) e ICP-Brasil (qualificada) confirmada
- AIA extension no cert da DECLARACAO aponta para `http://repo.iti.br/docs/Cadeia_GovBr-der.p7b` — verificado programaticamente

### Tertiary (LOW confidence)
- Nenhum

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — bibliotecas instaladas e verificadas por execução real
- pikepdf metadata API: HIGH — testado nos 5 PDFs reais com campos reais
- pyHanko validation: HIGH — `INTACT:TRUSTED,UNTOUCHED` obtido empiricamente; todos os pitfalls descobertos por execução real
- Gov-Br PKI chain: HIGH — chain baixada, parseada, usada com sucesso em validação real
- Pitfalls: HIGH — cada pitfall foi encontrado e resolvido durante a pesquisa

**Research date:** 2026-03-28
**Valid until:** 2026-06-28 (60 dias — libs estáveis, mas Gov-Br chain URL pode mudar)
