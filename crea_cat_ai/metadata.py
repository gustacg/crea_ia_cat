"""
CREA CAT AI - Extração de Metadados PDF via pikepdf

Responsável por:
- Extrair metadados do PDF (creator, producer, author, data criação, data modificação)
- Detectar anomalias: software de edição suspeito, datas inconsistentes
- Sinalizar documentos editados em software de imagem (Photoshop, GIMP, etc.)
"""

import pikepdf
import re
import config
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class MetadadosPDF:
    """Metadados extraídos de um arquivo PDF."""
    creator: Optional[str] = None
    producer: Optional[str] = None
    author: Optional[str] = None
    creation_date: Optional[datetime] = None
    mod_date: Optional[datetime] = None
    anomalias: list[str] = field(default_factory=list)


def _parse_pdf_date(date_str: str) -> Optional[datetime]:
    """
    Parseia data no formato PDF: D:YYYYMMDDHHmmSSOHH'mm'

    Exemplos:
        "D:20250115143000-03'00'"  → datetime(2025, 1, 15, 14, 30, 0, tzinfo=...)
        "D:20250115143000"          → datetime(2025, 1, 15, 14, 30, 0) naive
        "D:20250115143000Z"         → datetime(2025, 1, 15, 14, 30, 0, tzinfo=UTC)
        ""                          → None
    """
    if not date_str:
        return None

    s = str(date_str).strip()

    # Remover prefixo "D:"
    if s.startswith("D:"):
        s = s[2:]

    if not s:
        return None

    # Normalizar fuso horário: -03'00' → -0300, +05'30' → +0530
    s = re.sub(r"([+-]\d{2})'(\d{2})'", r"\1\2", s)
    # Normalizar UTC: Z → +0000
    s = re.sub(r"Z$", "+0000", s)

    # Tentar com fuso horário (YYYYMMDDHHmmSS±HHMM)
    try:
        return datetime.strptime(s, "%Y%m%d%H%M%S%z")
    except ValueError:
        pass

    # Tentar sem fuso horário (YYYYMMDDHHmmSS → 14 chars)
    try:
        return datetime.strptime(s[:14], "%Y%m%d%H%M%S")
    except ValueError:
        pass

    return None


def extrair_metadados(caminho_pdf: Path) -> MetadadosPDF:
    """
    Extrai metadados do PDF usando pikepdf.

    Lê: /Creator, /Producer, /Author, /CreationDate, /ModDate do docinfo.

    Args:
        caminho_pdf: Caminho para o arquivo PDF.

    Returns:
        MetadadosPDF com os campos extraídos. Campos ausentes ficam None.
    """
    with pikepdf.open(caminho_pdf) as pdf:
        di = pdf.docinfo

        # pikepdf retorna objetos pikepdf.String — sempre converter com str()
        creator_raw = str(di.get("/Creator", ""))
        producer_raw = str(di.get("/Producer", ""))
        author_raw = str(di.get("/Author", ""))
        creation_raw = str(di.get("/CreationDate", ""))
        mod_raw = str(di.get("/ModDate", ""))

        m = MetadadosPDF(
            creator=creator_raw or None,
            producer=producer_raw or None,
            author=author_raw or None,
            creation_date=_parse_pdf_date(creation_raw),
            mod_date=_parse_pdf_date(mod_raw),
        )

    return m


def detectar_anomalias(m: MetadadosPDF) -> list[str]:
    """
    Detecta anomalias nos metadados do PDF.

    Verifica:
    - Software de edição suspeito (Photoshop, GIMP, Paint.NET, Inkscape)
    - Data de modificação anterior à data de criação

    Args:
        m: MetadadosPDF com os dados extraídos.

    Returns:
        Lista de strings descrevendo as anomalias encontradas.
    """
    anomalias: list[str] = []

    # Verificar software suspeito no creator e producer
    for sw in config.SOFTWARE_SUSPEITO:
        for campo in [m.creator or "", m.producer or ""]:
            if sw.lower() in campo.lower():
                anomalias.append(f"Software de edição suspeito detectado: {campo}")
                break  # evitar duplicata para o mesmo campo

    # Verificar inconsistência de datas
    if m.creation_date and m.mod_date:
        # Comparação segura: ambas devem ser naive ou ambas com tzinfo
        cd = m.creation_date
        md = m.mod_date
        # Normalizar para comparação: remover tzinfo se apenas uma tem
        if (cd.tzinfo is None) != (md.tzinfo is None):
            cd = cd.replace(tzinfo=None) if cd.tzinfo else cd
            md = md.replace(tzinfo=None) if md.tzinfo else md
        if md < cd:
            anomalias.append(
                f"Data de modificação ({m.mod_date}) anterior à criação ({m.creation_date})"
            )

    return anomalias


def processar_documento(caminho_pdf: Path) -> MetadadosPDF:
    """
    Ponto de entrada público para processamento de metadados.

    Combina extrair_metadados() e detectar_anomalias(), retornando
    MetadadosPDF com campo anomalias populado.

    Args:
        caminho_pdf: Caminho para o arquivo PDF.

    Returns:
        MetadadosPDF com metadados extraídos e anomalias detectadas.
    """
    m = extrair_metadados(caminho_pdf)
    m.anomalias = detectar_anomalias(m)
    return m
