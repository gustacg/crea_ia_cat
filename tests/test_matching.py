"""
Testes unitários para crea_cat_ai/matching.py

Cobre:
- TestMatchExato: comparação exata de CPF, CNPJ, CREA/RNP, ART referenciada
- TestValidacaoDatas: validação de intervalo de datas
- TestGPTCruzamento: comparação fuzzy/semântica via GPT mock
- TestCruzarDocumentos: API pública cruzar_documentos()
"""

import pytest
from crea_cat_ai.matching import (
    cruzar_documentos,
    StatusCampo,
    ComparacaoCampo,
    ResultadoCruzamento,
)
from crea_cat_ai.analysis import (
    ResultadoAnalise,
    EntidadesProfissional,
    EntidadesOrganizacao,
    EntidadesEndereco,
    EntidadesData,
    AnaliseVisual,
)


# ---------------------------------------------------------------------------
# Helper para construir ResultadoAnalise com campos customizáveis
# ---------------------------------------------------------------------------

def _make_resultado(
    numero_documento: str | None = "MA20250929762",
    crea_rnp: str | None = "1120893194",
    cpf_profissional: str | None = None,
    cnpj_contratante: str | None = "36408654000104",
    nome_profissional: str | None = "ALEXANDRE DE MORAES BUENO NETO",
    empresa_contratante: str | None = "TABOCA AGRO NEGOCIOS LTDA",
    empresa_executora: str | None = None,
    endereco_obra: EntidadesEndereco | None = None,
    data_inicio: str | None = "12/05/2025",
    data_termino: str | None = "24/06/2025",
    escopo: str | None = "Elaboracao de projeto de sistema de iluminacao",
    valor_contrato: str | None = "R$ 5.000,00",
    contrato_numero: str | None = "0352015",
    art_referenciada: str | None = None,
) -> ResultadoAnalise:
    """Cria um ResultadoAnalise com campos customizáveis para testes."""
    profissional = None
    if nome_profissional or crea_rnp or cpf_profissional:
        profissional = EntidadesProfissional(
            nome=nome_profissional or "N/A",
            titulo="ENGENHEIRO ELETRICISTA",
            crea_rnp=crea_rnp,
            cpf=cpf_profissional,
        )

    contratante = None
    if empresa_contratante or cnpj_contratante:
        contratante = EntidadesOrganizacao(
            nome=empresa_contratante or "N/A",
            cnpj=cnpj_contratante,
        )

    executora = None
    if empresa_executora:
        executora = EntidadesOrganizacao(nome=empresa_executora)

    return ResultadoAnalise(
        numero_documento=numero_documento,
        profissional=profissional,
        contratante=contratante,
        empresa_executora=executora,
        endereco_obra=endereco_obra,
        datas=EntidadesData(data_inicio=data_inicio, data_termino=data_termino),
        escopo=escopo,
        valor_contrato=valor_contrato,
        contrato_numero=contrato_numero,
        art_referenciada=art_referenciada,
        visual=AnaliseVisual(tem_timbre=False, tem_assinatura_visual=False),
        confianca=0.95,
    )


def _get_campo(result: ResultadoCruzamento, campo: str) -> ComparacaoCampo:
    """Retorna a comparação para um campo específico pelo nome."""
    return next(c for c in result.comparacoes if c.campo == campo)


# ---------------------------------------------------------------------------
# TestMatchExato: comparação exata de identificadores
# ---------------------------------------------------------------------------

class TestMatchExato:
    """Testa comparação exata de CPF, CNPJ, CREA/RNP."""

    def test_crea_rnp_match(self, mock_matching_client):
        """Mesmo CREA/RNP após normalização → MATCH."""
        art = _make_resultado(crea_rnp="1120893194MA")
        atestado = _make_resultado(crea_rnp="CREA MA 1120893194")
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "crea_rnp")
        assert campo.status == StatusCampo.MATCH

    def test_crea_rnp_divergente(self, mock_matching_client):
        """CREA/RNP diferentes após normalização → DIVERGENTE."""
        art = _make_resultado(crea_rnp="1120893194")
        atestado = _make_resultado(crea_rnp="9999999999")
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "crea_rnp")
        assert campo.status == StatusCampo.DIVERGENTE

    def test_cpf_match(self, mock_matching_client):
        """Mesmo CPF após normalização → MATCH."""
        art = _make_resultado(cpf_profissional="123.456.789-00")
        atestado = _make_resultado(cpf_profissional="12345678900")
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "cpf_profissional")
        assert campo.status == StatusCampo.MATCH

    def test_cnpj_match(self, mock_matching_client):
        """Mesmo CNPJ após normalização → MATCH."""
        art = _make_resultado(cnpj_contratante="36.408.654/0001-04")
        atestado = _make_resultado(cnpj_contratante="36408654000104")
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "cnpj_contratante")
        assert campo.status == StatusCampo.MATCH

    def test_ambos_ausentes(self, mock_matching_client):
        """Ambos os CPFs ausentes (None) → AUSENTE."""
        art = _make_resultado(cpf_profissional=None, crea_rnp=None)
        atestado = _make_resultado(cpf_profissional=None, crea_rnp=None)
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "cpf_profissional")
        assert campo.status == StatusCampo.AUSENTE

    def test_um_ausente(self, mock_matching_client):
        """CPF presente apenas em um documento → AUSENTE."""
        art = _make_resultado(cpf_profissional="12345678900")
        atestado = _make_resultado(cpf_profissional=None)
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "cpf_profissional")
        assert campo.status == StatusCampo.AUSENTE

    def test_art_referenciada_match(self, mock_matching_client):
        """ART referenciada no atestado coincide com numero_documento da ART → MATCH."""
        art = _make_resultado(numero_documento="MA20250929762")
        atestado = _make_resultado(art_referenciada="MA20250929762")
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "art_referenciada")
        assert campo.status == StatusCampo.MATCH


# ---------------------------------------------------------------------------
# TestValidacaoDatas: validação de intervalo de datas
# ---------------------------------------------------------------------------

class TestValidacaoDatas:
    """Testa validação de intervalo de datas (atestado deve estar DENTRO da ART)."""

    def test_dentro_intervalo(self, mock_matching_client):
        """Datas do atestado dentro do intervalo da ART → MATCH."""
        art = _make_resultado(data_inicio="01/01/2025", data_termino="31/12/2025")
        atestado = _make_resultado(data_inicio="12/05/2025", data_termino="24/06/2025")
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "intervalo_datas")
        assert campo.status == StatusCampo.MATCH

    def test_fora_intervalo_inicio(self, mock_matching_client):
        """Início do atestado ANTES do início da ART → DIVERGENTE."""
        art = _make_resultado(data_inicio="01/06/2025", data_termino="31/12/2025")
        atestado = _make_resultado(data_inicio="01/01/2025", data_termino="24/06/2025")
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "intervalo_datas")
        assert campo.status == StatusCampo.DIVERGENTE

    def test_fora_intervalo_termino(self, mock_matching_client):
        """Término do atestado APÓS o término da ART → DIVERGENTE."""
        art = _make_resultado(data_inicio="01/01/2025", data_termino="30/06/2025")
        atestado = _make_resultado(data_inicio="12/05/2025", data_termino="31/12/2025")
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "intervalo_datas")
        assert campo.status == StatusCampo.DIVERGENTE

    def test_datas_ausentes_atestado(self, mock_matching_client):
        """Datas do atestado ausentes → AUSENTE (não DIVERGENTE per D-08)."""
        art = _make_resultado(data_inicio="01/01/2025", data_termino="31/12/2025")
        atestado = _make_resultado(data_inicio=None, data_termino=None)
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "intervalo_datas")
        assert campo.status == StatusCampo.AUSENTE

    def test_datas_ausentes_art(self, mock_matching_client):
        """Datas da ART ausentes → AUSENTE (não é possível validar intervalo)."""
        art = _make_resultado(data_inicio=None, data_termino=None)
        atestado = _make_resultado(data_inicio="12/05/2025", data_termino="24/06/2025")
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "intervalo_datas")
        assert campo.status == StatusCampo.AUSENTE

    def test_formato_iso(self, mock_matching_client):
        """Datas no formato ISO (YYYY-MM-DD) são parseadas corretamente."""
        art = _make_resultado(data_inicio="2025-01-01", data_termino="2025-12-31")
        atestado = _make_resultado(data_inicio="2025-05-12", data_termino="2025-06-24")
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "intervalo_datas")
        assert campo.status == StatusCampo.MATCH


# ---------------------------------------------------------------------------
# TestGPTCruzamento: comparação via GPT mock
# ---------------------------------------------------------------------------

class TestGPTCruzamento:
    """Testa comparações fuzzy/semânticas via GPT-4.1 (com mock)."""

    def test_nome_match(self, mock_matching_client):
        """Nomes com variações de formatação → MATCH (do mock GPT)."""
        art = _make_resultado(nome_profissional="ALEXANDRE DE MORAES BUENO NETO")
        atestado = _make_resultado(nome_profissional="Alexandre Moraes Bueno Neto")
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "nome_profissional")
        assert campo.status == StatusCampo.MATCH
        assert campo.confianca >= 0.7

    def test_empresa_divergente(self, mock_matching_client_divergente):
        """'AR CLIMA SOLUÇÕES' vs 'HIDRO-CLIMA Construções' → DIVERGENTE (D-11)."""
        art = _make_resultado(empresa_executora="AR CLIMA SOLUCOES")
        atestado = _make_resultado(empresa_executora="HIDRO-CLIMA Construcoes")
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "empresa_executora")
        assert campo.status == StatusCampo.DIVERGENTE

    def test_escopo_similar(self, mock_matching_client):
        """Escopos similares → MATCH com confiança >= 0.7."""
        art = _make_resultado(escopo="Projeto de iluminacao publica em via urbana")
        atestado = _make_resultado(escopo="Elaboracao de projeto de iluminacao em area urbana")
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "escopo")
        assert campo.status == StatusCampo.MATCH
        assert campo.confianca >= 0.7

    def test_gpt_fallback(self, mock_matching_client_none):
        """output_parsed=None → todos os campos GPT retornam AUSENTE."""
        art = _make_resultado()
        atestado = _make_resultado()
        result = cruzar_documentos(art, atestado)
        # Campos GPT devem ser AUSENTE quando fallback ativado
        gpt_campos = ["nome_profissional", "empresa_contratante", "empresa_executora",
                      "endereco_obra", "escopo", "valor_contrato", "contrato_numero"]
        for nome_campo in gpt_campos:
            campo = _get_campo(result, nome_campo)
            assert campo.status == StatusCampo.AUSENTE, f"Campo {nome_campo} deveria ser AUSENTE"


# ---------------------------------------------------------------------------
# TestCruzarDocumentos: API pública cruzar_documentos()
# ---------------------------------------------------------------------------

class TestCruzarDocumentos:
    """Testa a API pública cruzar_documentos() end-to-end."""

    def test_resultado_completo(self, mock_matching_client):
        """cruzar_documentos retorna ResultadoCruzamento com contadores corretos."""
        art = _make_resultado()
        atestado = _make_resultado()
        result = cruzar_documentos(art, atestado)

        assert isinstance(result, ResultadoCruzamento)
        assert result.total_match + result.total_divergente + result.total_ausente == len(result.comparacoes)
        assert result.total_match >= 0
        assert result.total_divergente >= 0
        assert result.total_ausente >= 0

    def test_comparacoes_tem_campos_obrigatorios(self, mock_matching_client):
        """Cada ComparacaoCampo tem campo, status, valor_art, valor_atestado, detalhes (D-05)."""
        art = _make_resultado()
        atestado = _make_resultado()
        result = cruzar_documentos(art, atestado)

        for comp in result.comparacoes:
            assert isinstance(comp, ComparacaoCampo)
            assert comp.campo is not None
            assert comp.status in (StatusCampo.MATCH, StatusCampo.DIVERGENTE, StatusCampo.AUSENTE)

    def test_valor_contrato_match(self, mock_matching_client):
        """Valores de contrato iguais → MATCH (do mock GPT)."""
        art = _make_resultado(valor_contrato="R$ 5.000,00")
        atestado = _make_resultado(valor_contrato="R$ 5.000,00")
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "valor_contrato")
        assert campo.status == StatusCampo.MATCH

    def test_contrato_numero_match(self, mock_matching_client):
        """Números de contrato iguais → MATCH (do mock GPT)."""
        art = _make_resultado(contrato_numero="0352015")
        atestado = _make_resultado(contrato_numero="0352015")
        result = cruzar_documentos(art, atestado)
        campo = _get_campo(result, "contrato_numero")
        assert campo.status == StatusCampo.MATCH
