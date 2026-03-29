"""
Testes unitários para crea_cat_ai/verdict.py

Cobre:
- TestEnums: StatusItem, TipoVeredito
- TestModels: ItemVerificado, Veredito
- TestCalcularScore: cálculo de média ponderada
- TestKnockouts: regras de knock-out (CPF/CNPJ/CREA/empresa) e penalidades
- TestVeredito: determinação do tipo de veredito pelo score
- TestConsolidarItens: consolidação de itens de cruzamento, compliance, metadados, assinatura
- TestExigencias: geração de exigências no formato CREA
- TestCalcularVeredito: API pública calcular_veredito()
"""

import pytest
from crea_cat_ai.verdict import (
    calcular_veredito,
    StatusItem,
    TipoVeredito,
    ItemVerificado,
    Veredito,
)
from crea_cat_ai.matching import (
    StatusCampo,
    ComparacaoCampo,
    ResultadoCruzamento,
)
from crea_cat_ai.compliance import (
    StatusCompliance,
    VerificacaoItem,
    ResultadoCompliance,
)
from crea_cat_ai.metadata import MetadadosPDF
from crea_cat_ai.signature import ResultadoAssinatura
import config


# ---------------------------------------------------------------------------
# Helpers para construir objetos de teste
# ---------------------------------------------------------------------------

def _make_cruzamento(comparacoes: list[ComparacaoCampo] | None = None) -> ResultadoCruzamento:
    """Cria um ResultadoCruzamento simples para testes."""
    if comparacoes is None:
        comparacoes = []
    total_match = sum(1 for c in comparacoes if c.status == StatusCampo.MATCH)
    total_divergente = sum(1 for c in comparacoes if c.status == StatusCampo.DIVERGENTE)
    total_ausente = sum(1 for c in comparacoes if c.status == StatusCampo.AUSENTE)
    return ResultadoCruzamento(
        comparacoes=comparacoes,
        total_match=total_match,
        total_divergente=total_divergente,
        total_ausente=total_ausente,
    )


def _make_compliance(
    verificacoes: list[VerificacaoItem] | None = None,
    exigencias: list[str] | None = None,
    declaracao_necessaria: bool = False,
    declaracao_encontrada: bool = False,
    anuencia_necessaria: bool = False,
    anuencia_encontrada: bool = False,
    anexo_iv_completo: bool = True,
) -> ResultadoCompliance:
    """Cria um ResultadoCompliance simples para testes."""
    return ResultadoCompliance(
        verificacoes=verificacoes or [],
        exigencias=exigencias or [],
        declaracao_necessaria=declaracao_necessaria,
        declaracao_encontrada=declaracao_encontrada,
        anuencia_necessaria=anuencia_necessaria,
        anuencia_encontrada=anuencia_encontrada,
        anexo_iv_completo=anexo_iv_completo,
    )


def _make_metadata_limpa() -> MetadadosPDF:
    """Cria MetadadosPDF sem anomalias."""
    return MetadadosPDF(creator="Microsoft Word", anomalias=[])


def _make_metadata_suspeita() -> MetadadosPDF:
    """Cria MetadadosPDF com anomalia de software suspeito."""
    return MetadadosPDF(
        creator="Adobe Photoshop 2024",
        anomalias=["Software de edição suspeito detectado: Adobe Photoshop 2024"],
    )


def _make_assinatura_ausente() -> ResultadoAssinatura:
    """Cria ResultadoAssinatura sem assinatura digital."""
    return ResultadoAssinatura(presente=False)


def _make_assinatura_valida() -> ResultadoAssinatura:
    """Cria ResultadoAssinatura com assinatura digital válida."""
    return ResultadoAssinatura(
        presente=True,
        quantidade=1,
        signatarios=[{
            "nome": "JOAO DA SILVA",
            "emissor": "AC GOV-BR",
            "valido": True,
            "integro": True,
            "confiavel": True,
            "sumario": "VALID",
            "erro": None,
        }],
    )


# ---------------------------------------------------------------------------
# TestEnums: StatusItem e TipoVeredito
# ---------------------------------------------------------------------------

class TestEnums:
    """Testa os enums StatusItem e TipoVeredito."""

    def test_status_item_enum(self):
        """StatusItem tem valores OK, DIVERGENTE, AUSENTE, SUSPEITO."""
        assert StatusItem.OK == "OK"
        assert StatusItem.DIVERGENTE == "DIVERGENTE"
        assert StatusItem.AUSENTE == "AUSENTE"
        assert StatusItem.SUSPEITO == "SUSPEITO"

    def test_status_item_is_str_enum(self):
        """StatusItem é str Enum (consistente com padrão do projeto)."""
        assert isinstance(StatusItem.OK, str)
        assert isinstance(StatusItem.DIVERGENTE, str)

    def test_tipo_veredito_enum(self):
        """TipoVeredito tem valores ADERENTE, PENDENTE, SUSPEITO."""
        assert TipoVeredito.ADERENTE == "ADERENTE"
        assert TipoVeredito.PENDENTE == "PENDENTE"
        assert TipoVeredito.SUSPEITO == "SUSPEITO"

    def test_tipo_veredito_is_str_enum(self):
        """TipoVeredito é str Enum."""
        assert isinstance(TipoVeredito.ADERENTE, str)


# ---------------------------------------------------------------------------
# TestModels: ItemVerificado e Veredito
# ---------------------------------------------------------------------------

class TestModels:
    """Testa os modelos Pydantic ItemVerificado e Veredito."""

    def test_item_verificado_model(self):
        """ItemVerificado tem campos: campo, status, valor_encontrado, valor_esperado, detalhes, peso."""
        item = ItemVerificado(
            campo="cpf_profissional",
            status=StatusItem.OK,
            valor_encontrado="12345678900",
            valor_esperado="12345678900",
            detalhes="Match exato",
            peso=1.0,
        )
        assert item.campo == "cpf_profissional"
        assert item.status == StatusItem.OK
        assert item.valor_encontrado == "12345678900"
        assert item.valor_esperado == "12345678900"
        assert item.detalhes == "Match exato"
        assert item.peso == 1.0

    def test_item_verificado_defaults(self):
        """ItemVerificado tem valores padrão para campos opcionais."""
        item = ItemVerificado(campo="escopo", status=StatusItem.DIVERGENTE)
        assert item.valor_encontrado is None
        assert item.valor_esperado is None
        assert item.detalhes is None
        assert item.peso == 0.0

    def test_veredito_model(self):
        """Veredito tem campos: tipo, score, itens_verificados, exigencias."""
        item = ItemVerificado(campo="cpf", status=StatusItem.OK, peso=1.0)
        veredito = Veredito(
            tipo=TipoVeredito.ADERENTE,
            score=0.95,
            itens_verificados=[item],
            exigencias=[],
        )
        assert veredito.tipo == TipoVeredito.ADERENTE
        assert veredito.score == 0.95
        assert len(veredito.itens_verificados) == 1
        assert veredito.exigencias == []


# ---------------------------------------------------------------------------
# TestCalcularScore: cálculo de média ponderada
# ---------------------------------------------------------------------------

class TestCalcularScore:
    """Testa o cálculo de score de confiança (média ponderada)."""

    def test_calcular_score_all_match(self):
        """Todos os campos MATCH com pesos variados -> score = 1.0."""
        comparacoes = [
            ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.MATCH,
                            valor_art="123", valor_atestado="123", confianca=1.0),
            ComparacaoCampo(campo="empresa_executora", status=StatusCampo.MATCH,
                            valor_art="Empresa A", valor_atestado="Empresa A", confianca=1.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        assert veredito.score == pytest.approx(1.0, abs=0.01)

    def test_calcular_score_mixed(self):
        """CPF MATCH (peso 1.0) + empresa DIVERGENTE (peso 0.8) -> score = 1.0*1.0 / (1.0+0.8) = 0.556."""
        comparacoes = [
            ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.MATCH,
                            valor_art="123", valor_atestado="123", confianca=1.0),
            ComparacaoCampo(campo="empresa_executora", status=StatusCampo.DIVERGENTE,
                            valor_art="Empresa A", valor_atestado="Empresa B", confianca=0.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        # Score base: (1.0 * 1.0 + 0.8 * 0.0) / (1.0 + 0.8) = 1.0 / 1.8 = 0.556
        # Empresa divergente -> knockout cap 0.79 -> ainda 0.556 < 0.79
        assert veredito.score == pytest.approx(0.556, abs=0.01)

    def test_calcular_score_ausente_half(self):
        """Campo único AUSENTE -> score = 0.5 (ausência não é fraude, D-01)."""
        comparacoes = [
            ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.AUSENTE),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        assert veredito.score == pytest.approx(0.5, abs=0.01)


# ---------------------------------------------------------------------------
# TestKnockouts: regras de knock-out e penalidades
# ---------------------------------------------------------------------------

class TestKnockouts:
    """Testa as regras de knock-out e penalidades (D-02)."""

    def test_knockout_cpf_divergente(self):
        """CPF divergente caps score em max 0.49 (força SUSPEITO)."""
        comparacoes = [
            ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.DIVERGENTE,
                            valor_art="111", valor_atestado="222", confianca=0.0),
            # Outros campos todos match para garantir score base alto
            ComparacaoCampo(campo="crea_rnp", status=StatusCampo.MATCH,
                            valor_art="123", valor_atestado="123", confianca=1.0),
            ComparacaoCampo(campo="escopo", status=StatusCampo.MATCH,
                            valor_art="servico X", valor_atestado="servico X", confianca=1.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        assert veredito.score <= 0.49
        assert veredito.tipo == TipoVeredito.SUSPEITO

    def test_knockout_cnpj_divergente(self):
        """CNPJ divergente caps score em max 0.49."""
        comparacoes = [
            ComparacaoCampo(campo="cnpj_contratante", status=StatusCampo.DIVERGENTE,
                            valor_art="111", valor_atestado="222", confianca=0.0),
            ComparacaoCampo(campo="crea_rnp", status=StatusCampo.MATCH,
                            valor_art="123", valor_atestado="123", confianca=1.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        assert veredito.score <= 0.49

    def test_knockout_crea_rnp_divergente(self):
        """CREA/RNP divergente caps score em max 0.49."""
        comparacoes = [
            ComparacaoCampo(campo="crea_rnp", status=StatusCampo.DIVERGENTE,
                            valor_art="111", valor_atestado="222", confianca=0.0),
            ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.MATCH,
                            valor_art="123", valor_atestado="123", confianca=1.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        assert veredito.score <= 0.49

    def test_knockout_empresa_divergente(self):
        """Empresa executora divergente caps score em max 0.79 (nunca ADERENTE)."""
        comparacoes = [
            ComparacaoCampo(campo="empresa_executora", status=StatusCampo.DIVERGENTE,
                            valor_art="AR CLIMA", valor_atestado="HIDRO-CLIMA", confianca=0.0),
            ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.MATCH,
                            valor_art="123", valor_atestado="123", confianca=1.0),
            ComparacaoCampo(campo="crea_rnp", status=StatusCampo.MATCH,
                            valor_art="456", valor_atestado="456", confianca=1.0),
            ComparacaoCampo(campo="cnpj_contratante", status=StatusCampo.MATCH,
                            valor_art="789", valor_atestado="789", confianca=1.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        assert veredito.score <= 0.79
        assert veredito.tipo != TipoVeredito.ADERENTE

    def test_knockout_metadata_suspeito_penalty(self):
        """Anomalia de software suspeito nos metadados aplica penalidade -0.15."""
        comparacoes = [
            ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.MATCH,
                            valor_art="123", valor_atestado="123", confianca=1.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        # Score base = 1.0 (todos match)
        # Com penalidade -0.15 = 0.85
        metadata_suspeita = _make_metadata_suspeita()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={"atestado": metadata_suspeita},
            resultados_assinatura={},
        )
        assert veredito.score == pytest.approx(0.85, abs=0.01)

    def test_knockout_declaracao_ausente_penalty(self):
        """Declaração obrigatória ausente (necessaria=True, encontrada=False) aplica penalidade -0.20."""
        comparacoes = [
            ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.MATCH,
                            valor_art="123", valor_atestado="123", confianca=1.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance(
            declaracao_necessaria=True,
            declaracao_encontrada=False,
        )
        # Score base = 1.0, penalidade -0.20 = 0.80
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        assert veredito.score == pytest.approx(0.80, abs=0.01)


# ---------------------------------------------------------------------------
# TestVeredito: determinação do tipo de veredito
# ---------------------------------------------------------------------------

class TestVereditoTipo:
    """Testa a determinação do tipo de veredito baseado no score."""

    def test_veredito_aderente(self):
        """Score >= 0.80 -> TipoVeredito.ADERENTE."""
        comparacoes = [
            ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.MATCH,
                            valor_art="123", valor_atestado="123", confianca=1.0),
            ComparacaoCampo(campo="crea_rnp", status=StatusCampo.MATCH,
                            valor_art="456", valor_atestado="456", confianca=1.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        assert veredito.score >= config.SCORE_ADERENTE
        assert veredito.tipo == TipoVeredito.ADERENTE

    def test_veredito_pendente(self):
        """Score >= 0.50 e < 0.80 -> TipoVeredito.PENDENTE."""
        # Um campo match, um divergente -> score ~0.556
        comparacoes = [
            ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.MATCH,
                            valor_art="123", valor_atestado="123", confianca=1.0),
            ComparacaoCampo(campo="empresa_executora", status=StatusCampo.DIVERGENTE,
                            valor_art="A", valor_atestado="B", confianca=0.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        assert config.SCORE_PENDENTE <= veredito.score < config.SCORE_ADERENTE
        assert veredito.tipo == TipoVeredito.PENDENTE

    def test_veredito_suspeito(self):
        """Score < 0.50 -> TipoVeredito.SUSPEITO."""
        comparacoes = [
            ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.DIVERGENTE,
                            valor_art="111", valor_atestado="222", confianca=0.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        assert veredito.score < config.SCORE_PENDENTE
        assert veredito.tipo == TipoVeredito.SUSPEITO


# ---------------------------------------------------------------------------
# TestConsolidarItens: consolidação de itens de todas as fontes
# ---------------------------------------------------------------------------

class TestConsolidarItens:
    """Testa a consolidação de itens verificados de cruzamento, compliance, metadados, assinatura."""

    def test_consolidar_itens_from_cruzamento(self):
        """ComparacaoCampo cpf_profissional MATCH -> ItemVerificado status=OK, peso=1.0."""
        comparacoes = [
            ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.MATCH,
                            valor_art="123", valor_atestado="123", confianca=1.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        itens_cpf = [i for i in veredito.itens_verificados if i.campo == "cpf_profissional"]
        assert len(itens_cpf) == 1
        assert itens_cpf[0].status == StatusItem.OK
        assert itens_cpf[0].peso == config.PESO_CPF

    def test_consolidar_itens_from_compliance_conforme(self):
        """VerificacaoItem CONFORME -> ItemVerificado status=OK, peso=0.0."""
        compliance = _make_compliance(verificacoes=[
            VerificacaoItem(
                requisito="CDOC-01",
                descricao="Declaração verificada",
                status=StatusCompliance.CONFORME,
                detalhes="Declaração encontrada",
            )
        ])
        veredito = calcular_veredito(
            resultado_cruzamento=None,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        itens_decl = [i for i in veredito.itens_verificados if "CDOC-01" in i.campo or "declaracao" in i.campo.lower() or "CDOC-01" in (i.detalhes or "")]
        # Verificar que há pelo menos um item vindo do compliance
        assert len(veredito.itens_verificados) >= 1
        compliance_items = [i for i in veredito.itens_verificados if i.peso == 0.0]
        assert any(i.status == StatusItem.OK for i in compliance_items)

    def test_consolidar_itens_from_compliance_nao_conforme(self):
        """VerificacaoItem NAO_CONFORME -> ItemVerificado status=DIVERGENTE, peso=0.0."""
        compliance = _make_compliance(verificacoes=[
            VerificacaoItem(
                requisito="COMP-01.1",
                descricao="CNPJ contratante ausente",
                status=StatusCompliance.NAO_CONFORME,
                detalhes="Campo obrigatório ausente",
            )
        ])
        veredito = calcular_veredito(
            resultado_cruzamento=None,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        compliance_items = [i for i in veredito.itens_verificados if i.peso == 0.0]
        assert any(i.status == StatusItem.DIVERGENTE for i in compliance_items)

    def test_consolidar_itens_from_metadata_anomalias(self):
        """MetadadosPDF com anomalias -> ItemVerificado status=SUSPEITO."""
        metadata_suspeita = _make_metadata_suspeita()
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=None,
            resultado_compliance=compliance,
            resultados_metadata={"atestado": metadata_suspeita},
            resultados_assinatura={},
        )
        itens_suspeitos = [i for i in veredito.itens_verificados if i.status == StatusItem.SUSPEITO]
        assert len(itens_suspeitos) >= 1

    def test_consolidar_itens_from_assinatura_valida(self):
        """ResultadoAssinatura válida -> ItemVerificado status=OK."""
        compliance = _make_compliance()
        assinatura_valida = _make_assinatura_valida()
        veredito = calcular_veredito(
            resultado_cruzamento=None,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={"atestado": assinatura_valida},
        )
        itens_assinatura = [
            i for i in veredito.itens_verificados
            if "assinatura" in i.campo.lower() or "digital" in i.campo.lower()
        ]
        assert len(itens_assinatura) >= 1
        assert any(i.status == StatusItem.OK for i in itens_assinatura)


# ---------------------------------------------------------------------------
# TestExigencias: geração de exigências no formato CREA
# ---------------------------------------------------------------------------

class TestExigencias:
    """Testa a geração de exigências no formato CREA (maiúsculas declarativas)."""

    def test_exigencias_cruzamento_cpf(self):
        """CPF divergente -> exigência com 'VERIFICAR DIVERGENCIA DE CPF'."""
        comparacoes = [
            ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.DIVERGENTE,
                            valor_art="11111111111", valor_atestado="22222222222", confianca=0.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        exig_cpf = [e for e in veredito.exigencias if "CPF" in e]
        assert len(exig_cpf) >= 1
        assert "VERIFICAR DIVERGENCIA DE CPF" in exig_cpf[0]
        assert "11111111111" in exig_cpf[0]
        assert "22222222222" in exig_cpf[0]

    def test_exigencias_cruzamento_empresa(self):
        """empresa_executora divergente -> exigência com 'VERIFICAR DIVERGENCIA DE EMPRESA EXECUTORA'."""
        comparacoes = [
            ComparacaoCampo(campo="empresa_executora", status=StatusCampo.DIVERGENTE,
                            valor_art="AR CLIMA", valor_atestado="HIDRO-CLIMA", confianca=0.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        exig_empresa = [e for e in veredito.exigencias if "EMPRESA EXECUTORA" in e]
        assert len(exig_empresa) >= 1
        assert "VERIFICAR DIVERGENCIA DE EMPRESA EXECUTORA" in exig_empresa[0]

    def test_exigencias_cruzamento_escopo(self):
        """escopo divergente -> exigência específica de compatibilidade de escopo."""
        comparacoes = [
            ComparacaoCampo(campo="escopo", status=StatusCampo.DIVERGENTE,
                            valor_art="iluminacao", valor_atestado="construcao civil", confianca=0.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        exig_escopo = [e for e in veredito.exigencias if "ESCOPO" in e or "OBJETO" in e]
        assert len(exig_escopo) >= 1
        assert "VERIFICAR COMPATIBILIDADE DO OBJETO/ESCOPO" in exig_escopo[0]

    def test_exigencias_cruzamento_datas(self):
        """intervalo_datas divergente -> exigência de verificação de período."""
        comparacoes = [
            ComparacaoCampo(campo="intervalo_datas", status=StatusCampo.DIVERGENTE,
                            valor_art="01/2025 a 06/2025", valor_atestado="07/2024 a 12/2024"),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        exig_datas = [e for e in veredito.exigencias if "PERIODO" in e or "DATA" in e]
        assert len(exig_datas) >= 1
        assert "VERIFICAR PERIODO DE EXECUCAO" in exig_datas[0]

    def test_exigencias_compliance_reused(self):
        """Exigências do compliance aparecem diretamente na lista final sem duplicação."""
        exigencia_compliance = "APRESENTAR DECLARACAO DE PROFISSIONAL HABILITADO NA AREA, DE ACORDO COM O PAR. 1, DO ART. 59 DA RESOLUCAO 1137 DO CONFEA"
        compliance = _make_compliance(exigencias=[exigencia_compliance])
        veredito = calcular_veredito(
            resultado_cruzamento=None,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        assert exigencia_compliance in veredito.exigencias

    def test_exigencias_no_duplicates(self):
        """Exigências de compliance + cruzamento combinadas sem duplicação."""
        exigencia_compliance = "EXIGENCIA DO COMPLIANCE"
        comparacoes = [
            ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.DIVERGENTE,
                            valor_art="111", valor_atestado="222", confianca=0.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance(exigencias=[exigencia_compliance])
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        # Sem duplicatas: cada exigência deve aparecer uma única vez
        assert len(veredito.exigencias) == len(set(veredito.exigencias))
        assert exigencia_compliance in veredito.exigencias


# ---------------------------------------------------------------------------
# TestCalcularVeredito: API pública calcular_veredito()
# ---------------------------------------------------------------------------

class TestCalcularVeredito:
    """Testa a API pública calcular_veredito() end-to-end."""

    def test_calcular_veredito_retorna_veredito(self):
        """calcular_veredito() retorna uma instância Veredito."""
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=None,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        assert isinstance(veredito, Veredito)

    def test_calcular_veredito_no_cruzamento(self):
        """resultado_cruzamento=None produz veredito apenas de compliance/metadata/assinatura (D-20)."""
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=None,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        assert veredito is not None
        assert isinstance(veredito.tipo, TipoVeredito)
        assert 0.0 <= veredito.score <= 1.0

    def test_calcular_veredito_score_range(self):
        """Score sempre dentro do intervalo [0.0, 1.0] mesmo com penalidades cumulativas."""
        comparacoes = [
            ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.DIVERGENTE,
                            valor_art="111", valor_atestado="222", confianca=0.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance(
            declaracao_necessaria=True,
            declaracao_encontrada=False,
        )
        metadata_suspeita = _make_metadata_suspeita()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={"doc": metadata_suspeita},
            resultados_assinatura={},
        )
        assert 0.0 <= veredito.score <= 1.0

    def test_calcular_veredito_itens_verificados_nao_vazio(self):
        """itens_verificados não é vazio quando há dados para analisar."""
        comparacoes = [
            ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.MATCH,
                            valor_art="123", valor_atestado="123", confianca=1.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        assert len(veredito.itens_verificados) >= 1

    def test_calcular_veredito_exigencias_maiusculas(self):
        """Todas as exigências geradas são em maiúsculas."""
        comparacoes = [
            ComparacaoCampo(campo="cpf_profissional", status=StatusCampo.DIVERGENTE,
                            valor_art="111", valor_atestado="222", confianca=0.0),
        ]
        cruzamento = _make_cruzamento(comparacoes)
        compliance = _make_compliance()
        veredito = calcular_veredito(
            resultado_cruzamento=cruzamento,
            resultado_compliance=compliance,
            resultados_metadata={},
            resultados_assinatura={},
        )
        for exigencia in veredito.exigencias:
            assert exigencia == exigencia.upper(), f"Exigência não está em maiúsculas: {exigencia}"
