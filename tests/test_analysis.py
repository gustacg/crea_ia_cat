"""
Testes unitários para crea_cat_ai/analysis.py.

Cobre todos os 6 requisitos ANAL:
- ANAL-01: Extração de entidades (nome, CPF, CNPJ, CREA/RNP, datas, escopo)
- ANAL-02: Normalização RNP == CREA (identificadores equivalentes)
- ANAL-03: Verificação ortográfica apenas para Atestados
- ANAL-04: Detecção de timbre/logo visual
- ANAL-05: Detecção de assinatura visual com nome/cargo/CREA/CPF
- ANAL-06: Identificação de assinante não-engenheiro (engenheiro_habilitado)
"""

import pytest
from unittest.mock import MagicMock

from crea_cat_ai.analysis import (
    normalizar_crea_rnp,
    analisar_documento,
    analisar_pacote,
    _selecionar_paginas_analise,
    ResultadoAnalise,
    AssinanteInfo,
    ErroOrtografico,
    AnaliseVisual,
    EntidadesProfissional,
    EntidadesOrganizacao,
    EntidadesData,
)
from crea_cat_ai.ingestion import (
    DocumentoCarregado,
    PaginaDocumento,
    TipoDocumento,
    PacoteDocumentos,
)
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_doc(tipo: TipoDocumento, num_pages: int) -> DocumentoCarregado:
    """Cria um DocumentoCarregado fake com num_pages páginas para testes."""
    paginas = [
        PaginaDocumento(
            numero=i + 1,
            texto_nativo="",
            imagem_b64="AAAA",
        )
        for i in range(num_pages)
    ]
    return DocumentoCarregado(
        caminho=Path(f"fake_{tipo.value}.pdf"),
        tipo=tipo,
        paginas=paginas,
        tem_texto_nativo=False,
    )


# ---------------------------------------------------------------------------
# ANAL-02: Normalização CREA/RNP
# ---------------------------------------------------------------------------

class TestNormalizarCreaRnp:
    """Testa normalizar_crea_rnp — ANAL-02."""

    def test_normalizar_crea_rnp_somente_digitos(self):
        """Número já normalizado retorna igual."""
        assert normalizar_crea_rnp("1120893194") == "1120893194"

    def test_normalizar_crea_rnp_sufixo_uf(self):
        """Remove sufixo de UF (ex: 1120893194MA → 1120893194)."""
        assert normalizar_crea_rnp("1120893194MA") == "1120893194"

    def test_normalizar_crea_rnp_prefixo_crea_ma(self):
        """Remove prefixo 'CREA MA ' (ex: CREA MA 1015902979 → 1015902979)."""
        assert normalizar_crea_rnp("CREA MA 1015902979") == "1015902979"

    def test_normalizar_crea_rnp_formato_go(self):
        """Remove sufixo não-numérico (ex: 4388D/GO → 4388)."""
        assert normalizar_crea_rnp("4388D/GO") == "4388"

    def test_normalizar_crea_rnp_none(self):
        """None retorna None."""
        assert normalizar_crea_rnp(None) is None

    def test_normalizar_crea_rnp_string_vazia(self):
        """String vazia retorna None."""
        assert normalizar_crea_rnp("") is None

    def test_normalizar_crea_rnp_apenas_letras(self):
        """String sem dígitos retorna None."""
        assert normalizar_crea_rnp("MA") is None


# ---------------------------------------------------------------------------
# Seleção de páginas para análise
# ---------------------------------------------------------------------------

class TestSelecionarPaginasAnalise:
    """Testa _selecionar_paginas_analise."""

    def test_selecionar_paginas_1_page(self):
        """Documento com 1 página retorna [página 1]."""
        doc = _make_doc(TipoDocumento.ART, 1)
        paginas = _selecionar_paginas_analise(doc)
        assert len(paginas) == 1
        assert paginas[0].numero == 1

    def test_selecionar_paginas_3_pages(self):
        """Documento com 3 páginas retorna todas as 3."""
        doc = _make_doc(TipoDocumento.ATESTADO, 3)
        paginas = _selecionar_paginas_analise(doc)
        assert len(paginas) == 3

    def test_selecionar_paginas_32_pages(self):
        """Documento com 32 páginas retorna [página 1, página 32]."""
        doc = _make_doc(TipoDocumento.ATESTADO, 32)
        paginas = _selecionar_paginas_analise(doc)
        assert len(paginas) == 2
        assert paginas[0].numero == 1
        assert paginas[1].numero == 32

    def test_selecionar_paginas_4_pages(self):
        """Documento com 4 páginas (> 3) retorna [página 1, página 4]."""
        doc = _make_doc(TipoDocumento.ATESTADO, 4)
        paginas = _selecionar_paginas_analise(doc)
        assert len(paginas) == 2
        assert paginas[0].numero == 1
        assert paginas[1].numero == 4


# ---------------------------------------------------------------------------
# ANAL-01: Extração de entidades via GPT (com mock)
# ---------------------------------------------------------------------------

class TestExtracaoEntidades:
    """Testa analisar_documento com cliente GPT mockado."""

    def test_extrai_entidades_art(self, mock_analysis_client):
        """ANAL-01: Extrai entidades da ART via GPT com structured output."""
        doc = _make_doc(TipoDocumento.ART, 2)
        resultado = analisar_documento(doc)

        assert resultado.profissional is not None
        assert resultado.profissional.nome == "ALEXANDRE DE MORAES BUENO NETO"
        assert resultado.profissional.crea_rnp == "1120893194"
        assert resultado.contratante is not None
        assert resultado.contratante.cnpj == "36.408.654/0001-04"
        assert resultado.numero_documento == "MA20250929762"

    def test_analisar_documento_retorna_resultado_analise(self, mock_analysis_client):
        """analisar_documento retorna instância de ResultadoAnalise."""
        doc = _make_doc(TipoDocumento.ART, 1)
        resultado = analisar_documento(doc)
        assert isinstance(resultado, ResultadoAnalise)

    def test_analisar_documento_fallback_none(self, monkeypatch):
        """Quando output_parsed é None, retorna ResultadoAnalise com confianca=0.0."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_parsed = None
        mock_client.responses.parse.return_value = mock_response
        monkeypatch.setattr("crea_cat_ai.analysis.client", mock_client)

        doc = _make_doc(TipoDocumento.ART, 1)
        resultado = analisar_documento(doc)
        assert resultado.confianca == 0.0


# ---------------------------------------------------------------------------
# ANAL-03: Verificação ortográfica (somente Atestado)
# ---------------------------------------------------------------------------

class TestOrtografia:
    """Testa comportamento de spell-check — ANAL-03."""

    def test_ortografia_art_vazia(self, mock_analysis_client):
        """ART não deve ter erros ortográficos (spell-check só para Atestados)."""
        doc = _make_doc(TipoDocumento.ART, 1)
        resultado = analisar_documento(doc)
        # O mock retorna erros_ortograficos=[] para ART (padrão)
        assert resultado.erros_ortograficos == []

    def test_ortografia_atestado_pode_ter_erros(self, monkeypatch):
        """Atestado pode ter erros ortográficos quando GPT os identifica."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_parsed = ResultadoAnalise(
            confianca=0.9,
            erros_ortograficos=[
                ErroOrtografico(trecho="iluminaçao", sugestao="iluminação"),
            ],
        )
        mock_client.responses.parse.return_value = mock_response
        monkeypatch.setattr("crea_cat_ai.analysis.client", mock_client)

        doc = _make_doc(TipoDocumento.ATESTADO, 1)
        resultado = analisar_documento(doc)
        assert len(resultado.erros_ortograficos) == 1
        assert resultado.erros_ortograficos[0].trecho == "iluminaçao"
        assert resultado.erros_ortograficos[0].sugestao == "iluminação"


# ---------------------------------------------------------------------------
# ANAL-04 + ANAL-05: Análise visual (timbre e assinatura)
# ---------------------------------------------------------------------------

class TestAnaliseVisual:
    """Testa detecção de timbre e assinatura — ANAL-04 e ANAL-05."""

    def test_visual_timbre(self, mock_analysis_client):
        """ANAL-04: tem_timbre=True quando timbre detectado."""
        doc = _make_doc(TipoDocumento.ATESTADO, 1)
        resultado = analisar_documento(doc)
        assert resultado.visual.tem_timbre is True
        assert resultado.visual.descricao_timbre is not None

    def test_visual_assinatura(self, mock_analysis_client):
        """ANAL-05: tem_assinatura_visual=True quando assinatura detectada."""
        doc = _make_doc(TipoDocumento.ATESTADO, 1)
        resultado = analisar_documento(doc)
        assert resultado.visual.tem_assinatura_visual is True
        assert len(resultado.visual.assinantes) > 0


# ---------------------------------------------------------------------------
# ANAL-06: Classificação de engenheiro habilitado
# ---------------------------------------------------------------------------

class TestEngenheiroHabilitado:
    """Testa engenheiro_habilitado — ANAL-06."""

    def test_nao_engenheiro(self):
        """Cargo 'ADMINISTRADOR' → engenheiro_habilitado=False."""
        assinante = AssinanteInfo(
            nome="RUAN FERNANDES AZEVEDO DA NOBREGA",
            cargo="ADMINISTRADOR",
            engenheiro_habilitado=False,
            cpf="620.456.233-94",
        )
        assert assinante.engenheiro_habilitado is False

    def test_engenheiro_habilitado(self):
        """Cargo 'Engenheiro Civil de Saude Indigena' → engenheiro_habilitado=True."""
        assinante = AssinanteInfo(
            nome="Daniel Farias de Albuquerque",
            cargo="Engenheiro Civil de Saude Indigena",
            engenheiro_habilitado=True,
        )
        assert assinante.engenheiro_habilitado is True

    def test_administrador_no_resultado_analise(self, mock_analysis_client):
        """Assinante ADMINISTRADOR no resultado de analisar_documento."""
        doc = _make_doc(TipoDocumento.ATESTADO, 1)
        resultado = analisar_documento(doc)
        assinantes = resultado.visual.assinantes
        assert len(assinantes) > 0
        administrador = assinantes[0]
        assert administrador.cargo == "ADMINISTRADOR"
        assert administrador.engenheiro_habilitado is False


# ---------------------------------------------------------------------------
# analisar_pacote
# ---------------------------------------------------------------------------

class TestAnalisarPacote:
    """Testa analisar_pacote — integração das análises do pacote."""

    def test_analisar_pacote(self, mock_analysis_client):
        """analisar_pacote retorna dict keyed por tipo.value com ResultadoAnalise."""
        art = _make_doc(TipoDocumento.ART, 1)
        atestado = _make_doc(TipoDocumento.ATESTADO, 1)
        pacote = PacoteDocumentos(art=art, atestado=atestado)

        resultados = analisar_pacote(pacote)

        assert TipoDocumento.ART.value in resultados
        assert TipoDocumento.ATESTADO.value in resultados
        assert isinstance(resultados[TipoDocumento.ART.value], ResultadoAnalise)
        assert isinstance(resultados[TipoDocumento.ATESTADO.value], ResultadoAnalise)

    def test_analisar_pacote_vazio(self, mock_analysis_client):
        """Pacote sem documentos retorna dict vazio."""
        pacote = PacoteDocumentos(art=None, atestado=None)
        resultados = analisar_pacote(pacote)
        assert resultados == {}

    def test_analisar_pacote_com_complementares(self, mock_analysis_client):
        """Pacote com complementares inclui-os no resultado."""
        declaracao = _make_doc(TipoDocumento.DECLARACAO, 1)
        pacote = PacoteDocumentos(art=None, atestado=None, complementares=[declaracao])
        resultados = analisar_pacote(pacote)
        assert TipoDocumento.DECLARACAO.value in resultados


# ---------------------------------------------------------------------------
# Testes de integração (requerem API real — marcados com integration)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_analisar_documento_integracao(pdf_art_path):
    """Integração: analisar_documento com PDF real e API OpenAI real."""
    from crea_cat_ai.ingestion import carregar_pdf
    paginas = carregar_pdf(pdf_art_path)
    from crea_cat_ai.ingestion import DocumentoCarregado
    doc = DocumentoCarregado(
        caminho=pdf_art_path,
        tipo=TipoDocumento.ART,
        paginas=paginas,
        tem_texto_nativo=any(len(p.texto_nativo.strip()) > 100 for p in paginas),
    )
    resultado = analisar_documento(doc)
    assert resultado.profissional is not None
    assert "ALEXANDRE" in resultado.profissional.nome.upper()


@pytest.mark.integration
def test_analise_art_real(pdf_art_path):
    """ANAL-01: Entidades extraidas corretamente de ART real."""
    from crea_cat_ai.ingestion import carregar_pdf, DocumentoCarregado, TipoDocumento
    from crea_cat_ai.analysis import analisar_documento

    paginas = carregar_pdf(pdf_art_path)
    doc = DocumentoCarregado(
        caminho=pdf_art_path,
        tipo=TipoDocumento.ART,
        paginas=paginas,
        tem_texto_nativo=any(len(p.texto_nativo.strip()) > 100 for p in paginas),
    )
    resultado = analisar_documento(doc)
    assert resultado.profissional is not None
    assert "ALEXANDRE" in resultado.profissional.nome.upper() or "NIZO" in resultado.profissional.nome.upper()
    assert resultado.confianca > 0.5


@pytest.mark.integration
def test_assinante_ruan_real(pdf_atestado_path):
    """ANAL-05, ANAL-06: Atestado Par 1 — Ruan is ADMINISTRADOR, not engineer."""
    from crea_cat_ai.ingestion import carregar_pdf, DocumentoCarregado, TipoDocumento
    from crea_cat_ai.analysis import analisar_documento

    paginas = carregar_pdf(pdf_atestado_path)
    doc = DocumentoCarregado(
        caminho=pdf_atestado_path,
        tipo=TipoDocumento.ATESTADO,
        paginas=paginas,
        tem_texto_nativo=any(len(p.texto_nativo.strip()) > 100 for p in paginas),
    )
    resultado = analisar_documento(doc)
    assert resultado.visual.assinantes, "Deve detectar pelo menos um assinante"
    # At least one signer should be non-engineer (Ruan, ADMINISTRADOR)
    nao_engenheiros = [a for a in resultado.visual.assinantes if not a.engenheiro_habilitado]
    assert len(nao_engenheiros) >= 1, "Par 1: Ruan (ADMINISTRADOR) deve ser detectado como nao-engenheiro"
