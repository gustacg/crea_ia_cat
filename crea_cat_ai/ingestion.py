"""
CREA CAT AI - Ingestão e Classificação de Documentos

Responsável por:
- Aceitar pacote de documentos (diretório com PDFs)
- Converter páginas PDF em imagens via PyMuPDF (para GPT Vision)
- Extrair texto nativo quando disponível
- Classificar tipo de documento via GPT-4.1 (Responses API com structured output)
- Agrupar documentos em pacote estruturado (ART + Atestado + complementares)
"""

import pymupdf  # NUNCA usar import fitz — per CLAUDE.md
import base64
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from openai import OpenAI
from pydantic import BaseModel

import config


# ---------------------------------------------------------------------------
# Tipos de documento reconhecidos pelo pipeline
# ---------------------------------------------------------------------------

class TipoDocumento(str, Enum):
    ART = "ART"
    ATESTADO = "Atestado"
    DECLARACAO = "Declaracao"
    ANUENCIA = "Anuencia"
    NF = "NF"
    CONTRATO = "Contrato"
    RELATORIO_FOTOGRAFICO = "RelatorioFotografico"
    DESCONHECIDO = "Desconhecido"


# ---------------------------------------------------------------------------
# Estruturas de dados
# ---------------------------------------------------------------------------

@dataclass
class PaginaDocumento:
    """Representa uma página carregada de um PDF."""
    numero: int          # 1-indexed
    texto_nativo: str    # page.get_text() — string vazia se documento escaneado
    imagem_b64: str      # imagem PNG codificada em base64


@dataclass
class DocumentoCarregado:
    """Representa um PDF completamente carregado e classificado."""
    caminho: Path
    tipo: TipoDocumento
    paginas: list[PaginaDocumento]
    tem_texto_nativo: bool  # True se alguma página tem > 100 chars de texto


@dataclass
class PacoteDocumentos:
    """Agrupamento estruturado de documentos de um pedido de CAT."""
    art: DocumentoCarregado | None
    atestado: DocumentoCarregado | None
    complementares: list[DocumentoCarregado] = field(default_factory=list)
    nao_classificados: list[DocumentoCarregado] = field(default_factory=list)


class ResultadoClassificacao(BaseModel):
    """Schema para structured output do GPT-4.1 na classificação de documentos."""
    tipo: str          # Um dos valores de TipoDocumento
    confianca: float   # 0.0 a 1.0
    justificativa: str # Breve justificativa em pt-BR


# ---------------------------------------------------------------------------
# Cliente OpenAI (módulo-level — reutilizado entre chamadas)
# ---------------------------------------------------------------------------

client = OpenAI(api_key=config.OPENAI_API_KEY)


# ---------------------------------------------------------------------------
# Prompt de classificação
# ---------------------------------------------------------------------------

_TIPOS_VALIDOS = [t.value for t in TipoDocumento]

PROMPT_CLASSIFICACAO = """Você é um assistente especialista em documentos de engenharia do CREA (Conselho Regional de Engenharia e Agronomia).
Classifique este documento em uma das categorias abaixo:

- ART: Anotação de Responsabilidade Técnica emitida pelo CREA. Contém número da ART, profissional responsável, obra/serviço, valor, datas de início e término.
- Atestado: Atestado de Capacidade Técnica emitido por empresa contratante. Certifica que o profissional executou determinado serviço.
- Declaracao: Declaração de profissional habilitado ou Declaração Fiscal. Frequentemente usada quando o assinante do atestado não é engenheiro habilitado (Art. 59 §1º).
- Anuencia: Anuência de empresa ou profissional para subcontratação de serviços de engenharia.
- NF: Nota Fiscal de serviços prestados relacionada ao projeto ou obra.
- Contrato: Contrato de prestação de serviços de engenharia entre partes.
- RelatorioFotografico: Relatório fotográfico de obra ou serviço executado.
- Desconhecido: Tipo não identificado ou que não se enquadra nas categorias acima.

Analise o conteúdo textual e visual do documento e retorne a classificação com justificativa em português.
Tipos válidos: {tipos}""".format(tipos=", ".join(_TIPOS_VALIDOS))


# ---------------------------------------------------------------------------
# Funções principais
# ---------------------------------------------------------------------------

def carregar_pdf(caminho: Path) -> list[PaginaDocumento]:
    """
    Carrega um PDF, extrai texto nativo de cada página e converte para imagem PNG base64.

    Args:
        caminho: Caminho para o arquivo PDF.

    Returns:
        Lista de PaginaDocumento (1-indexed), limitada a config.MAX_PAGES_PER_PDF páginas.
    """
    scale = config.IMAGE_DPI / 72  # config.IMAGE_DPI = 200 → escala 200/72 ≈ 2.78x
    mat = pymupdf.Matrix(scale, scale)
    paginas: list[PaginaDocumento] = []

    with pymupdf.open(str(caminho)) as doc:
        total_paginas = min(len(doc), config.MAX_PAGES_PER_PDF)
        for i in range(total_paginas):
            page = doc[i]

            # Extração de texto nativo (rápido, sem chamada de API)
            texto = page.get_text()

            # Conversão da página em imagem PNG para o GPT Vision
            pix = page.get_pixmap(matrix=mat)
            png_bytes = pix.tobytes("png")
            b64 = base64.b64encode(png_bytes).decode("utf-8")

            paginas.append(PaginaDocumento(
                numero=i + 1,
                texto_nativo=texto,
                imagem_b64=b64,
            ))

    return paginas


def classificar_documento(doc: DocumentoCarregado) -> ResultadoClassificacao:
    """
    Classifica o tipo de documento via GPT-4.1 Vision usando a Responses API.

    Usa apenas a primeira página — suficiente para identificar o tipo de documento.
    Em caso de recusa do modelo, retorna TipoDocumento.DESCONHECIDO.

    Args:
        doc: Documento já carregado com páginas.

    Returns:
        ResultadoClassificacao com tipo, confiança e justificativa.
    """
    pagina = doc.paginas[0]

    # Texto da primeira página (com fallback para documentos escaneados)
    texto = pagina.texto_nativo.strip()
    conteudo_texto = (
        texto[:2000]
        if texto
        else "(sem texto nativo — documento escaneado)"
    )

    response = client.responses.parse(
        model=config.OPENAI_MODEL,
        instructions=PROMPT_CLASSIFICACAO,
        input=[{
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": f"Texto extraído (primeiros 2000 chars):\n{conteudo_texto}"
                },
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{pagina.imagem_b64}",
                    "detail": "low"  # Suficiente para identificação do tipo; economiza tokens
                }
            ]
        }],
        text_format=ResultadoClassificacao,
    )

    # Trata recusa do modelo (output_parsed = None em caso de safety filter)
    if response.output_parsed is None:
        return ResultadoClassificacao(
            tipo="Desconhecido",
            confianca=0.0,
            justificativa="Modelo recusou classificação",
        )

    return response.output_parsed


def _agrupar_documentos(documentos: list[DocumentoCarregado]) -> PacoteDocumentos:
    """
    Agrupa documentos classificados em um pacote estruturado.

    Regras de agrupamento:
    - art: primeiro documento com tipo ART
    - atestado: primeiro documento com tipo Atestado
    - complementares: Declaracao, Anuencia, NF, Contrato, RelatorioFotografico
    - nao_classificados: Desconhecido

    Args:
        documentos: Lista de documentos já classificados.

    Returns:
        PacoteDocumentos com documentos agrupados por categoria.
    """
    _tipos_complementares = (
        TipoDocumento.DECLARACAO,
        TipoDocumento.ANUENCIA,
        TipoDocumento.NF,
        TipoDocumento.CONTRATO,
        TipoDocumento.RELATORIO_FOTOGRAFICO,
    )

    art = next((d for d in documentos if d.tipo == TipoDocumento.ART), None)
    atestado = next((d for d in documentos if d.tipo == TipoDocumento.ATESTADO), None)
    complementares = [d for d in documentos if d.tipo in _tipos_complementares]
    nao_classificados = [d for d in documentos if d.tipo == TipoDocumento.DESCONHECIDO]

    return PacoteDocumentos(
        art=art,
        atestado=atestado,
        complementares=complementares,
        nao_classificados=nao_classificados,
    )


def carregar_pacote(diretorio: Path) -> PacoteDocumentos:
    """
    Carrega todos os PDFs de um diretório, converte páginas e classifica cada documento.

    Este é o ponto de entrada do pipeline para a Phase 2.
    Os documentos são classificados via GPT-4.1 e agrupados em PacoteDocumentos.

    Args:
        diretorio: Diretório contendo os arquivos PDF do pedido de CAT.

    Returns:
        PacoteDocumentos com documentos agrupados por tipo.

    Raises:
        ValueError: Se o diretório não contiver nenhum arquivo PDF.
    """
    pdfs = sorted(diretorio.glob("*.pdf"))
    if not pdfs:
        raise ValueError(f"Nenhum PDF encontrado em: {diretorio}")

    documentos: list[DocumentoCarregado] = []

    for caminho in pdfs:
        print(f"  Carregando: {caminho.name}")
        paginas = carregar_pdf(caminho)

        tem_nativo = any(len(p.texto_nativo.strip()) > 100 for p in paginas)

        doc = DocumentoCarregado(
            caminho=caminho,
            tipo=TipoDocumento.DESCONHECIDO,
            paginas=paginas,
            tem_texto_nativo=tem_nativo,
        )

        resultado = classificar_documento(doc)

        # Tenta mapear o tipo retornado para o enum; usa DESCONHECIDO como fallback
        try:
            doc.tipo = TipoDocumento(resultado.tipo)
        except ValueError:
            doc.tipo = TipoDocumento.DESCONHECIDO

        documentos.append(doc)
        print(f"    Tipo: {doc.tipo.value} (confiança: {resultado.confianca:.0%})")

    return _agrupar_documentos(documentos)
