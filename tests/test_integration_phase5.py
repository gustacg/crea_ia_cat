"""
Testes de integracao para Phase 5: Cruzamento de Documentos.
Requerem PDFs reais e chave OpenAI API.
Marcados com @pytest.mark.integration — excluidos do pytest padrao.
"""
import pytest
from pathlib import Path
from crea_cat_ai import ingestion, analysis, matching
from crea_cat_ai.matching import StatusCampo


@pytest.mark.integration
def test_cruzamento_par1(pdf_dir):
    """Par 1: ART + Atestado do Alexandre. Espera maioria MATCH."""
    pacote = ingestion.carregar_pacote(pdf_dir)
    assert pacote.art is not None, "ART nao encontrada"
    assert pacote.atestado is not None, "Atestado nao encontrado"

    resultados = analysis.analisar_pacote(pacote)
    art_analise = resultados.get("ART")
    atestado_analise = resultados.get("Atestado")
    assert art_analise is not None
    assert atestado_analise is not None

    resultado = matching.cruzar_documentos(art_analise, atestado_analise)
    assert resultado.total_match > 0, "Deve ter pelo menos 1 match"
    # Par 1 should have mostly matches
    assert resultado.total_match >= resultado.total_divergente


@pytest.mark.integration
def test_par2_empresa_divergente():
    """
    Par 2: ART diz 'AR CLIMA SOLUCOES', Atestado diz 'HIDRO-CLIMA Construcoes'.
    Empresa deve ser DIVERGENTE (D-11, XREF-07).
    """
    # Par 2 uses different PDFs — skip if not available
    par2_dir = Path("Documentos que crea recebe")  # adjust if Par 2 has own dir
    if not par2_dir.exists():
        pytest.skip("Diretorio Par 2 nao encontrado")

    # This test validates the critical D-11 requirement
    # When Par 2 documents are available, run full pipeline and check empresa field
    pacote = ingestion.carregar_pacote(par2_dir)
    if not pacote.art or not pacote.atestado:
        pytest.skip("Par 2: ART ou Atestado nao encontrado")

    resultados = analysis.analisar_pacote(pacote)
    art_analise = resultados.get("ART")
    atestado_analise = resultados.get("Atestado")
    if not art_analise or not atestado_analise:
        pytest.skip("Par 2: analise nao retornou dados")

    resultado = matching.cruzar_documentos(art_analise, atestado_analise)

    # Find empresa comparison — could be empresa_contratante or empresa_executora
    empresa_comps = [
        c for c in resultado.comparacoes
        if "empresa" in c.campo
    ]
    assert any(
        c.status == StatusCampo.DIVERGENTE for c in empresa_comps
    ), f"Par 2 deve ter empresa DIVERGENTE. Resultados empresa: {[(c.campo, c.status.value) for c in empresa_comps]}"


@pytest.mark.integration
def test_pipeline_main_com_matching(pdf_dir):
    """Roda main.main() e verifica que resultado_cruzamento esta no retorno."""
    from main import main as run_pipeline
    resultado = run_pipeline(pdf_dir)
    assert "resultado_cruzamento" in resultado, "main() deve retornar resultado_cruzamento"
    if resultado["resultado_cruzamento"] is not None:
        assert "total_match" in resultado["resultado_cruzamento"]
        assert "comparacoes" in resultado["resultado_cruzamento"]
