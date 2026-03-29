"""
Fixtures de teste para o pipeline CREA CAT AI.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock


# Diretório raiz do projeto (um nível acima do diretório tests/)
PROJECT_ROOT = Path(__file__).parent.parent
PDF_DIR = PROJECT_ROOT / "Documentos que crea recebe"


@pytest.fixture
def pdf_dir():
    """Retorna o diretório com os PDFs de teste. Pula se não existir."""
    if not PDF_DIR.exists():
        pytest.skip(f"Diretório de PDFs não encontrado: {PDF_DIR}")
    return PDF_DIR


@pytest.fixture
def pdf_art_path():
    """Retorna o caminho do PDF de ART de teste. Pula se não existir."""
    caminho = PDF_DIR / "MA20250929762.aZzbC (1).pdf"
    if not caminho.exists():
        pytest.skip(f"PDF de ART não encontrado: {caminho}")
    return caminho


@pytest.fixture
def pdf_atestado_path():
    """Retorna o caminho do PDF de Atestado de teste. Pula se não existir."""
    caminho = PDF_DIR / "944678.2026__ACT_Alexandre_B12032026101332 (1).pdf"
    if not caminho.exists():
        pytest.skip(f"PDF de Atestado não encontrado: {caminho}")
    return caminho


@pytest.fixture
def mock_openai_client(monkeypatch):
    """
    Substitui o cliente OpenAI em crea_cat_ai.ingestion por um MagicMock.
    O mock retorna uma classificação de ART com confiança 0.95 por padrão.
    """
    from crea_cat_ai.ingestion import ResultadoClassificacao

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.output_parsed = ResultadoClassificacao(
        tipo="ART",
        confianca=0.95,
        justificativa="Documento ART",
    )
    mock_client.responses.parse.return_value = mock_response

    monkeypatch.setattr("crea_cat_ai.ingestion.client", mock_client)
    return mock_client


@pytest.fixture
def all_test_pdfs():
    """Retorna dicionário mapeando tipo esperado para nome de arquivo."""
    return {
        "ART": [
            "MA20250929762.aZzbC (1).pdf",
            "MA20250957723.ac6Y3.pdf",
        ],
        "Atestado": [
            "944678.2026__ACT_Alexandre_B12032026101332 (1).pdf",
            "saude indigena.pdf",
        ],
        "Declaracao": [
            "944678.2026__DECLARACAO__ENG_2_assinado__1_05022026162803.pdf",
        ],
    }


@pytest.fixture
def mock_analysis_client(monkeypatch):
    """
    Substitui o cliente OpenAI em crea_cat_ai.analysis por um MagicMock.
    O mock retorna um ResultadoAnalise completo por padrao.
    """
    from crea_cat_ai.analysis import (
        ResultadoAnalise, EntidadesProfissional, EntidadesOrganizacao,
        EntidadesData, AnaliseVisual, AssinanteInfo,
    )

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.output_parsed = ResultadoAnalise(
        numero_documento="MA20250929762",
        profissional=EntidadesProfissional(
            nome="ALEXANDRE DE MORAES BUENO NETO",
            titulo="ENGENHEIRO ELETRICISTA",
            crea_rnp="1120893194",
            cpf=None,
            registro="1120893194MA",
        ),
        contratante=EntidadesOrganizacao(
            nome="TABOCA AGRO NEGOCIOS LTDA",
            cnpj="36.408.654/0001-04",
        ),
        endereco_obra=None,
        datas=EntidadesData(data_inicio="12/05/2025", data_termino="24/06/2025"),
        escopo="Elaboracao de projeto de sistema de iluminacao",
        contrato_numero="0352015",
        visual=AnaliseVisual(
            tem_timbre=True,
            descricao_timbre="Timbre da empresa",
            tem_assinatura_visual=True,
            assinantes=[AssinanteInfo(
                nome="RUAN FERNANDES AZEVEDO DA NOBREGA",
                cargo="ADMINISTRADOR",
                engenheiro_habilitado=False,
                cpf="620.456.233-94",
            )],
        ),
        erros_ortograficos=[],
        confianca=0.95,
    )
    mock_client.responses.parse.return_value = mock_response
    monkeypatch.setattr("crea_cat_ai.analysis.client", mock_client)
    return mock_client


@pytest.fixture
def mock_matching_client(monkeypatch):
    """
    Substitui o cliente OpenAI em crea_cat_ai.matching por um MagicMock.
    O mock retorna um ResultadoGPTCruzamento com todos os campos como MATCH.
    """
    from crea_cat_ai.matching import ComparacaoGPT, ResultadoGPTCruzamento, StatusCampo

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.output_parsed = ResultadoGPTCruzamento(
        comparacoes=[
            ComparacaoGPT(campo="nome_profissional", status=StatusCampo.MATCH, confianca=0.95, detalhes="Mesmo profissional"),
            ComparacaoGPT(campo="empresa_contratante", status=StatusCampo.MATCH, confianca=0.90, detalhes="Mesma empresa contratante"),
            ComparacaoGPT(campo="empresa_executora", status=StatusCampo.MATCH, confianca=0.90, detalhes="Mesma empresa executora"),
            ComparacaoGPT(campo="endereco_obra", status=StatusCampo.MATCH, confianca=0.85, detalhes="Mesmo endereco"),
            ComparacaoGPT(campo="escopo", status=StatusCampo.MATCH, confianca=0.80, detalhes="Escopos compativeis"),
            ComparacaoGPT(campo="valor_contrato", status=StatusCampo.MATCH, confianca=1.0, detalhes="Mesmo valor"),
            ComparacaoGPT(campo="contrato_numero", status=StatusCampo.MATCH, confianca=1.0, detalhes="Mesmo numero de contrato"),
        ]
    )
    mock_client.responses.parse.return_value = mock_response
    monkeypatch.setattr("crea_cat_ai.matching.client", mock_client)
    return mock_client


@pytest.fixture
def mock_matching_client_divergente(monkeypatch):
    """
    Variante do mock_matching_client onde empresa_executora retorna DIVERGENTE.
    Usada para testar deteccao do caso Par 2: AR CLIMA vs HIDRO-CLIMA (D-11).
    """
    from crea_cat_ai.matching import ComparacaoGPT, ResultadoGPTCruzamento, StatusCampo

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.output_parsed = ResultadoGPTCruzamento(
        comparacoes=[
            ComparacaoGPT(campo="nome_profissional", status=StatusCampo.MATCH, confianca=0.95, detalhes="Mesmo profissional"),
            ComparacaoGPT(campo="empresa_contratante", status=StatusCampo.MATCH, confianca=0.90, detalhes="Mesma empresa contratante"),
            ComparacaoGPT(campo="empresa_executora", status=StatusCampo.DIVERGENTE, confianca=0.05, detalhes="AR CLIMA SOLUCOES e HIDRO-CLIMA Construcoes sao empresas distintas"),
            ComparacaoGPT(campo="endereco_obra", status=StatusCampo.MATCH, confianca=0.85, detalhes="Mesmo endereco"),
            ComparacaoGPT(campo="escopo", status=StatusCampo.MATCH, confianca=0.80, detalhes="Escopos compativeis"),
            ComparacaoGPT(campo="valor_contrato", status=StatusCampo.MATCH, confianca=1.0, detalhes="Mesmo valor"),
            ComparacaoGPT(campo="contrato_numero", status=StatusCampo.MATCH, confianca=1.0, detalhes="Mesmo numero de contrato"),
        ]
    )
    mock_client.responses.parse.return_value = mock_response
    monkeypatch.setattr("crea_cat_ai.matching.client", mock_client)
    return mock_client


@pytest.fixture
def mock_matching_client_none(monkeypatch):
    """
    Variante do mock_matching_client onde output_parsed=None.
    Testa o fallback quando o GPT nao retorna resultado estruturado.
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.output_parsed = None
    mock_client.responses.parse.return_value = mock_response
    monkeypatch.setattr("crea_cat_ai.matching.client", mock_client)
    return mock_client
