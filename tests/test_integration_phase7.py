"""Testes de integracao — Phase 7: Veredito, Exigencias e Relatorio."""
import pytest
from pathlib import Path
from crea_cat_ai.verdict import calcular_veredito, TipoVeredito
from crea_cat_ai.matching import ResultadoCruzamento, ComparacaoCampo, StatusCampo
from crea_cat_ai.compliance import ResultadoCompliance
from crea_cat_ai.metadata import MetadadosPDF
from crea_cat_ai.signature import ResultadoAssinatura


@pytest.mark.integration
class TestVerdictIntegration:

    def test_empresa_divergente_not_aderente(self):
        """Par 2 smoke test: empresa divergente must not produce ADERENTE (D-04)."""
        cruzamento = ResultadoCruzamento(
            comparacoes=[
                ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.MATCH, valor_art="111", valor_atestado="111"),
                ComparacaoCampo(campo="empresa_executora", status=StatusCampo.DIVERGENTE, valor_art="AR CLIMA SOLUCOES", valor_atestado="HIDRO-CLIMA Construcoes", detalhes="Nomes de empresa diferentes"),
            ],
            total_match=1, total_divergente=1, total_ausente=0,
        )
        compliance = ResultadoCompliance()
        veredito = calcular_veredito(cruzamento, compliance, {}, {})
        assert veredito.tipo != TipoVeredito.ADERENTE, f"Par 2 empresa divergente must not be ADERENTE, got {veredito.tipo.value} (score={veredito.score})"

    def test_all_match_aderente(self):
        """All fields matching should produce ADERENTE."""
        cruzamento = ResultadoCruzamento(
            comparacoes=[
                ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.MATCH),
                ComparacaoCampo(campo="cnpj_contratante", status=StatusCampo.MATCH),
                ComparacaoCampo(campo="crea_rnp", status=StatusCampo.MATCH),
                ComparacaoCampo(campo="nome_profissional", status=StatusCampo.MATCH),
                ComparacaoCampo(campo="empresa_executora", status=StatusCampo.MATCH),
                ComparacaoCampo(campo="escopo", status=StatusCampo.MATCH),
            ],
            total_match=6, total_divergente=0, total_ausente=0,
        )
        compliance = ResultadoCompliance()
        veredito = calcular_veredito(cruzamento, compliance, {}, {})
        assert veredito.tipo == TipoVeredito.ADERENTE

    def test_cpf_divergente_suspeito(self):
        """CPF divergente must produce SUSPEITO (D-02 knockout)."""
        cruzamento = ResultadoCruzamento(
            comparacoes=[
                ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.DIVERGENTE, valor_art="111", valor_atestado="222", detalhes="CPFs diferentes"),
                ComparacaoCampo(campo="empresa_executora", status=StatusCampo.MATCH),
            ],
            total_match=1, total_divergente=1, total_ausente=0,
        )
        compliance = ResultadoCompliance()
        veredito = calcular_veredito(cruzamento, compliance, {}, {})
        assert veredito.tipo == TipoVeredito.SUSPEITO

    def test_exigencias_generated_for_divergence(self):
        """Divergent fields generate UPPERCASE exigencias."""
        cruzamento = ResultadoCruzamento(
            comparacoes=[
                ComparacaoCampo(campo="empresa_executora", status=StatusCampo.DIVERGENTE, valor_art="A", valor_atestado="B", detalhes="diff"),
            ],
            total_match=0, total_divergente=1, total_ausente=0,
        )
        compliance = ResultadoCompliance(exigencias=["EXIGENCIA COMPLIANCE EXISTENTE"])
        veredito = calcular_veredito(cruzamento, compliance, {}, {})
        assert any("EMPRESA EXECUTORA" in e for e in veredito.exigencias)
        assert "EXIGENCIA COMPLIANCE EXISTENTE" in veredito.exigencias
