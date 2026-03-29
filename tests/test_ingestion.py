"""
Testes unitários para o módulo crea_cat_ai/ingestion.py.

Todos os testes que chamam a API do OpenAI usam mocks.
Testes de integração (API real) são marcados com @pytest.mark.integration.
"""

import base64
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from crea_cat_ai.ingestion import (
    TipoDocumento,
    PaginaDocumento,
    DocumentoCarregado,
    PacoteDocumentos,
    ResultadoClassificacao,
    carregar_pdf,
    classificar_documento,
    carregar_pacote,
    _agrupar_documentos,
)


# ---------------------------------------------------------------------------
# Testes de estrutura de dados
# ---------------------------------------------------------------------------

def test_tipo_documento_enum():
    """Verifica que todos os 8 membros do enum TipoDocumento existem e têm os valores corretos."""
    assert TipoDocumento.ART.value == "ART"
    assert TipoDocumento.ATESTADO.value == "Atestado"
    assert TipoDocumento.DECLARACAO.value == "Declaracao"
    assert TipoDocumento.ANUENCIA.value == "Anuencia"
    assert TipoDocumento.NF.value == "NF"
    assert TipoDocumento.CONTRATO.value == "Contrato"
    assert TipoDocumento.RELATORIO_FOTOGRAFICO.value == "RelatorioFotografico"
    assert TipoDocumento.DESCONHECIDO.value == "Desconhecido"
    # Garante que há exatamente 8 membros
    assert len(TipoDocumento) == 8


# ---------------------------------------------------------------------------
# Testes de carregamento de PDF (requerem arquivo real — pulam se ausente)
# ---------------------------------------------------------------------------

def test_carrega_pdf_retorna_paginas(pdf_art_path):
    """carregar_pdf deve retornar lista de PaginaDocumento com pelo menos 1 página."""
    paginas = carregar_pdf(pdf_art_path)

    assert isinstance(paginas, list)
    assert len(paginas) >= 1

    for pagina in paginas:
        assert isinstance(pagina, PaginaDocumento)
        assert pagina.numero >= 1
        assert isinstance(pagina.texto_nativo, str)
        assert isinstance(pagina.imagem_b64, str)
        assert len(pagina.imagem_b64) > 0
        # Verifica que imagem_b64 é decodificável como base64
        decoded = base64.b64decode(pagina.imagem_b64)
        assert len(decoded) > 0


def test_texto_nativo_extraido(pdf_art_path):
    """A primeira página do PDF de ART deve conter 'ART' ou 'Anotação'."""
    paginas = carregar_pdf(pdf_art_path)
    assert len(paginas) >= 1
    texto_p0 = paginas[0].texto_nativo
    assert "ART" in texto_p0 or "Anotação" in texto_p0 or "Anotacao" in texto_p0


def test_imagem_b64_valida(pdf_art_path):
    """A imagem base64 da primeira página deve ser um PNG válido (verifica header)."""
    paginas = carregar_pdf(pdf_art_path)
    assert len(paginas) >= 1
    decoded = base64.b64decode(paginas[0].imagem_b64)
    # PNG magic bytes: \x89PNG
    assert decoded[:4] == b'\x89PNG', f"Header inesperado: {decoded[:8]!r}"


# ---------------------------------------------------------------------------
# Testes de classificação (com mock do cliente OpenAI)
# ---------------------------------------------------------------------------

def test_classificacao_mockada(mock_openai_client, pdf_art_path):
    """
    classificar_documento deve retornar ResultadoClassificacao válido
    com tipo, confianca e justificativa — usando cliente mockado.
    """
    paginas = carregar_pdf(pdf_art_path)
    doc = DocumentoCarregado(
        caminho=pdf_art_path,
        tipo=TipoDocumento.DESCONHECIDO,
        paginas=paginas,
        tem_texto_nativo=any(len(p.texto_nativo.strip()) > 100 for p in paginas),
    )

    resultado = classificar_documento(doc)

    assert isinstance(resultado, ResultadoClassificacao)
    # tipo deve ser uma string que corresponde a um valor do enum
    assert resultado.tipo in [t.value for t in TipoDocumento]
    # confianca deve ser float entre 0 e 1
    assert isinstance(resultado.confianca, float)
    assert 0.0 <= resultado.confianca <= 1.0
    # justificativa deve ser string não-vazia
    assert isinstance(resultado.justificativa, str)
    assert len(resultado.justificativa) > 0


# ---------------------------------------------------------------------------
# Testes de agrupamento de documentos
# ---------------------------------------------------------------------------

def _criar_doc_mock(tipo: TipoDocumento, nome: str = "doc.pdf") -> DocumentoCarregado:
    """Cria um DocumentoCarregado mock para testes de agrupamento."""
    pagina = PaginaDocumento(numero=1, texto_nativo="texto teste", imagem_b64="dGVzdGU=")
    return DocumentoCarregado(
        caminho=Path(nome),
        tipo=tipo,
        paginas=[pagina],
        tem_texto_nativo=True,
    )


def test_agrupa_documentos():
    """
    _agrupar_documentos deve separar corretamente:
    - 1 ART (primeiro encontrado)
    - 1 Atestado (primeiro encontrado)
    - complementares (Declaracao, Anuencia, NF, Contrato, RelatorioFotografico)
    - nao_classificados (Desconhecido)
    Quando há 2 ARTs, o segundo vai para nao_classificados.
    """
    docs = [
        _criar_doc_mock(TipoDocumento.ART, "art1.pdf"),
        _criar_doc_mock(TipoDocumento.ATESTADO, "atestado.pdf"),
        _criar_doc_mock(TipoDocumento.DECLARACAO, "declaracao.pdf"),
        _criar_doc_mock(TipoDocumento.ART, "art2.pdf"),           # segundo ART
        _criar_doc_mock(TipoDocumento.DESCONHECIDO, "outro.pdf"),
    ]

    pacote = _agrupar_documentos(docs)

    assert isinstance(pacote, PacoteDocumentos)
    # Primeiro ART encontrado
    assert pacote.art is not None
    assert pacote.art.tipo == TipoDocumento.ART
    assert pacote.art.caminho == Path("art1.pdf")
    # Atestado
    assert pacote.atestado is not None
    assert pacote.atestado.tipo == TipoDocumento.ATESTADO
    # Complementares: apenas Declaracao
    assert len(pacote.complementares) == 1
    assert pacote.complementares[0].tipo == TipoDocumento.DECLARACAO
    # Nao classificados: DESCONHECIDO apenas (o segundo ART não vai pra cá pelo agrupador)
    assert len(pacote.nao_classificados) == 1
    assert pacote.nao_classificados[0].tipo == TipoDocumento.DESCONHECIDO


# ---------------------------------------------------------------------------
# Testes de carregamento de diretório
# ---------------------------------------------------------------------------

def test_carrega_diretorio_vazio(tmp_path):
    """carregar_pacote com diretório vazio deve lançar ValueError com 'Nenhum PDF'."""
    with pytest.raises(ValueError, match="Nenhum PDF"):
        carregar_pacote(tmp_path)


# ---------------------------------------------------------------------------
# Teste de integração com API real (requer OPENAI_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_classificacao_docs_reais(pdf_dir):
    """Testa classificação real dos 5 documentos de teste via GPT-4.1 API.

    Requer OPENAI_API_KEY no ambiente. Roda com: pytest -m integration
    """
    import os
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY não configurada")

    pacote = carregar_pacote(pdf_dir)

    # Must find at least 1 ART and 1 Atestado
    assert pacote.art is not None, "Nenhuma ART encontrada no pacote"
    assert pacote.atestado is not None, "Nenhum Atestado encontrado no pacote"
    assert pacote.art.tipo == TipoDocumento.ART
    assert pacote.atestado.tipo == TipoDocumento.ATESTADO

    # Should have at least 1 complementary doc (Declaracao)
    tipos_complementares = [d.tipo for d in pacote.complementares]
    assert TipoDocumento.DECLARACAO in tipos_complementares, "Declaração não encontrada nos complementares"

    # No documents should be unclassified
    assert len(pacote.nao_classificados) == 0, f"Documentos não classificados: {[d.caminho.name for d in pacote.nao_classificados]}"
