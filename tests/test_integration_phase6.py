"""
Testes de integracao para Phase 6 — Compliance module com PDFs reais.
Requerem PDFs reais e chave OpenAI API.
Marcados com @pytest.mark.integration — excluidos do pytest padrao.
"""

import pytest
from pathlib import Path
from tests.conftest import PDF_DIR


@pytest.mark.integration
class TestPar1ComplianceIntegration:
    """Par 1: Ruan (Administrador) assina atestado -> exige Declaracao -> Declaracao do Alexandre presente."""

    def test_par1_declaracao_necessaria(self):
        """Ruan (Administrador, engenheiro_habilitado=False) dispara exigencia de Declaracao."""
        # Import aqui para evitar criacao do cliente OpenAI no nivel do modulo
        from crea_cat_ai import ingestion, analysis, matching, compliance
        from crea_cat_ai.ingestion import TipoDocumento

        # Verificar se diretorio de PDFs de teste existe
        if not PDF_DIR.exists():
            pytest.skip(f"Diretorio de PDFs nao encontrado: {PDF_DIR}")

        # Fase 1: Ingestao e Classificacao
        pacote = ingestion.carregar_pacote(PDF_DIR)
        assert pacote.art is not None, "ART nao encontrada nos documentos de teste"
        assert pacote.atestado is not None, "Atestado nao encontrado nos documentos de teste"

        # Fase 2: Analise e Extracao de Entidades
        resultados_analise = analysis.analisar_pacote(pacote)

        art_analise = resultados_analise.get(TipoDocumento.ART.value)
        atestado_analise = resultados_analise.get(TipoDocumento.ATESTADO.value)
        assert art_analise is not None, "Analise da ART nao encontrada"
        assert atestado_analise is not None, "Analise do Atestado nao encontrada"

        # Fase 3: Cruzamento de Documentos
        resultado_cruzamento = matching.cruzar_documentos(art_analise, atestado_analise)

        # Fase 4: Compliance
        resultado = compliance.verificar_compliance(
            pacote=pacote,
            resultados_analise=resultados_analise,
            resultado_cruzamento=resultado_cruzamento,
        )

        # Par 1: Ruan e Administrador -> Declaracao deve ser exigida
        assert resultado.declaracao_necessaria is True, (
            "Ruan (Administrador) deve disparar exigencia de Declaracao (Art. 59 §1°)"
        )

        # Par 1: Declaracao do Alexandre deve estar nos complementares
        declaracao_found = any(
            d.tipo == TipoDocumento.DECLARACAO for d in pacote.complementares
        )
        if declaracao_found:
            assert resultado.declaracao_encontrada is True, (
                "Declaracao do Alexandre deve ser encontrada nos complementares"
            )

        # Compliance deve ter ao menos uma verificacao
        assert len(resultado.verificacoes) > 0, "Deve ter ao menos uma verificacao de compliance"

    def test_par1_pipeline_retorna_resultado_compliance(self):
        """Roda main.main() e verifica que resultado_compliance esta no retorno."""
        if not PDF_DIR.exists():
            pytest.skip(f"Diretorio de PDFs nao encontrado: {PDF_DIR}")

        from main import main as run_pipeline
        resultado = run_pipeline(PDF_DIR)

        assert "resultado_compliance" in resultado, (
            "main() deve retornar resultado_compliance no dict de retorno"
        )
        compliance_dict = resultado["resultado_compliance"]
        assert "declaracao_necessaria" in compliance_dict
        assert "declaracao_encontrada" in compliance_dict
        assert "anuencia_necessaria" in compliance_dict
        assert "anuencia_encontrada" in compliance_dict
        assert "anexo_iv_completo" in compliance_dict
        assert "verificacoes" in compliance_dict
        assert "exigencias" in compliance_dict
