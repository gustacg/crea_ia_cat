"""
CREA CAT AI - Validação de Assinatura Digital ICP-Brasil/Gov-Br via pyHanko

Responsável por:
- Detectar presença/ausência de assinatura digital no PDF (SIGN-01)
- Validar cadeia de certificados Gov-Br/ICP-Brasil (SIGN-02)
- Tratar ausência de assinatura como estado válido — não gera anomalia (SIGN-03)

Notas importantes:
- PDFs Gov-Br são hybrid-reference: PdfFileReader(strict=False) obrigatório
- Certificados Gov-Br têm apenas key_usage=digital_signature (sem non_repudiation)
  → KeyUsageConstraints(key_usage={'digital_signature'}) obrigatório
- Certificados podem ter expirado após a data de assinatura
  → moment=sig.self_reported_timestamp obrigatório para validação offline
- Chain Gov-Br disponível em http://repo.iti.br/docs/Cadeia_GovBr-der.p7b (HTTP simples)
"""

import urllib.request
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from asn1crypto import cms as asn1_cms
from pyhanko.sign import validation
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.fields import enumerate_sig_fields
from pyhanko.sign.validation.settings import KeyUsageConstraints
from pyhanko_certvalidator.context import ValidationContext

import config


# === Constantes ===

GOVBR_CHAIN_URL = "http://repo.iti.br/docs/Cadeia_GovBr-der.p7b"
GOVBR_CHAIN_CACHE = config.PROJECT_ROOT / "certs" / "govbr-chain.p7b"

# KeyUsageConstraints pré-criado — Gov-Br tem digital_signature mas não non_repudiation
_KUC = KeyUsageConstraints(key_usage={"digital_signature"})


# === Dataclass de resultado ===

@dataclass
class ResultadoAssinatura:
    """
    Resultado da análise de assinaturas digitais de um PDF.

    Nota SIGN-03: A ausência de assinatura (presente=False) é um estado válido.
    Não há campo 'anomalias' neste dataclass — ausência não é suspeito.
    """
    presente: bool
    quantidade: int = 0
    signatarios: list[dict] = field(default_factory=list)
    # Cada dict em signatarios: {nome, emissor, valido, integro, confiavel, sumario, erro}


# === Funções auxiliares ===

def _carregar_govbr_chain() -> tuple[list, list]:
    """
    Carrega e retorna a cadeia de certificados Gov-Br como objetos asn1crypto.

    Baixa o arquivo P7B do repositório ITI e cacheia em certs/govbr-chain.p7b.
    Na primeira chamada (ou se o cache não existir), faz download via HTTP.

    Returns:
        Tupla (root_certs, other_certs) como listas de asn1crypto Certificate.
        Em caso de falha no download, retorna ([], []) — pipeline continua com
        confiavel=False nos resultados.
    """
    if not GOVBR_CHAIN_CACHE.exists():
        GOVBR_CHAIN_CACHE.parent.mkdir(parents=True, exist_ok=True)
        try:
            print(f"Baixando cadeia Gov-Br de {GOVBR_CHAIN_URL} ...")
            with urllib.request.urlopen(GOVBR_CHAIN_URL, timeout=15) as r:
                GOVBR_CHAIN_CACHE.write_bytes(r.read())
            print(f"Chain Gov-Br salva em {GOVBR_CHAIN_CACHE}")
        except Exception as e:
            print(f"AVISO: Falha ao baixar chain Gov-Br: {e}")
            print("Validação de certificados será marcada como não confiável (confiavel=False).")
            return [], []

    try:
        p7b_data = GOVBR_CHAIN_CACHE.read_bytes()
        content_info = asn1_cms.ContentInfo.load(p7b_data)
        signed_data = content_info["content"]
        all_certs = [cc.chosen for cc in signed_data["certificates"]]

        # Raízes: subject == issuer (self-signed)
        root_certs = [c for c in all_certs
                      if c.subject.human_friendly == c.issuer.human_friendly]
        other_certs = [c for c in all_certs if c not in root_certs]

        return root_certs, other_certs
    except Exception as e:
        print(f"AVISO: Falha ao parsear chain Gov-Br: {e}")
        return [], []


# === Função principal ===

def validar_assinaturas(caminho_pdf: Path) -> ResultadoAssinatura:
    """
    Detecta e valida assinaturas digitais em um PDF.

    Args:
        caminho_pdf: Caminho para o arquivo PDF.

    Returns:
        ResultadoAssinatura com:
        - presente=False se não houver assinaturas (estado válido, SIGN-03)
        - presente=True com lista de signatários validados se houver assinaturas

    Parâmetros críticos de validação (baseados em pitfalls descobertos na pesquisa):
    - strict=False: necessário para PDFs Gov-Br hybrid-reference (Pitfall 1)
    - KeyUsageConstraints(digital_signature): Gov-Br não tem non_repudiation (Pitfall 2)
    - moment=self_reported_timestamp: valida certs expirados na data de assinatura (Pitfall 3)
    - revocation_mode='soft-fail': permite validação offline sem CRL (MVP)
    """
    root_certs, other_certs = _carregar_govbr_chain()

    # CRÍTICO: manter o arquivo aberto durante toda a validação.
    # validate_pdf_signature() faz seek no arquivo ao ler os dados da assinatura.
    # Fechar o arquivo antes de validar causa "seek of closed file".
    with open(caminho_pdf, "rb") as f:
        # CRÍTICO: strict=False para PDFs hybrid-reference Gov-Br (Pitfall 1)
        reader = PdfFileReader(f, strict=False)
        sigs = reader.embedded_regular_signatures

        if not sigs:
            # SIGN-03: Ausência é estado válido — retorna presente=False sem anomalia
            return ResultadoAssinatura(presente=False)

        resultado = ResultadoAssinatura(presente=True, quantidade=len(sigs))

        for sig in sigs:
            cert = sig.signer_cert
            # CRÍTICO: moment=self_reported_timestamp para certs expirados (Pitfall 3)
            moment = sig.self_reported_timestamp

            entry: dict = {
                "nome": cert.subject.human_friendly if cert else "Desconhecido",
                "emissor": cert.issuer.human_friendly if cert else "Desconhecido",
                "valido": False,
                "integro": False,
                "confiavel": False,
                "sumario": "",
                "erro": None,
            }

            try:
                vc = ValidationContext(
                    trust_roots=root_certs,
                    other_certs=other_certs,
                    allow_fetching=False,
                    moment=moment,
                    revocation_mode="soft-fail",
                )
                # CRÍTICO: key_usage_settings com digital_signature (Pitfall 2)
                r = validation.validate_pdf_signature(
                    sig,
                    signer_validation_context=vc,
                    key_usage_settings=_KUC,
                )
                entry["valido"] = r.valid
                entry["integro"] = r.intact
                entry["confiavel"] = r.trusted
                entry["sumario"] = r.summary()
            except Exception as e:
                entry["erro"] = f"{type(e).__name__}: {e}"

            resultado.signatarios.append(entry)

    return resultado
