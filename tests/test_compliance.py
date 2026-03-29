"""
Testes unitários para crea_cat_ai/compliance.py

Cobre:
- TestDeclaracaoTrigger: trigger de Declaração quando assinante não é engenheiro
- TestDeclaracaoVerificacao: verificação de conformidade da Declaração
- TestDeclaracaoCrossRef: cruzamento de dados da Declaração com ART
- TestAnuencia: detecção de subcontratação e verificação de Anuência
- TestAnexoIV: checklist de 6 categorias obrigatórias do Anexo IV
- TestRes1160: hook estrutural da Resolução 1.160/2025
- TestVerificarCompliance: orquestrador verificar_compliance()
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from crea_cat_ai.compliance import (
    verificar_compliance,
    verificar_declaracao,
    verificar_anuencia,
    verificar_anexo_iv,
    _verificacoes_1160_overrides,
    ResultadoCompliance,
    StatusCompliance,
    VerificacaoItem,
    ResultadoEspecialidadeGPT,
)
from crea_cat_ai.analysis import (
    ResultadoAnalise,
    EntidadesProfissional,
    EntidadesOrganizacao,
    EntidadesEndereco,
    EntidadesData,
    AnaliseVisual,
    AssinanteInfo,
)
from crea_cat_ai.ingestion import (
    TipoDocumento,
    PacoteDocumentos,
    DocumentoCarregado,
    PaginaDocumento,
)
from crea_cat_ai.matching import ResultadoCruzamento


# ---------------------------------------------------------------------------
# Helpers para construir objetos de teste
# ---------------------------------------------------------------------------

def _make_resultado_analise(
    numero_documento: str | None = "MA20250929762",
    nome_profissional: str = "ALEXANDRE DE MORAES BUENO NETO",
    titulo_profissional: str = "ENGENHEIRO ELETRICISTA",
    crea_rnp: str | None = "1120893194",
    contratante_nome: str = "TABOCA AGRO NEGOCIOS LTDA",
    contratante_cnpj: str | None = "36.408.654/0001-04",
    contratante_cpf: str | None = None,
    empresa_executora_nome: str | None = None,
    data_inicio: str | None = "12/05/2025",
    data_termino: str | None = "24/06/2025",
    escopo: str | None = "Elaboracao de projeto de sistema de iluminacao",
    endereco_cidade: str | None = "Sao Luis",
    endereco_uf: str | None = "MA",
    tem_timbre: bool = True,
    tem_assinatura_visual: bool = True,
    assinantes: list[AssinanteInfo] | None = None,
    art_referenciada: str | None = None,
) -> ResultadoAnalise:
    """Cria um ResultadoAnalise com campos customizáveis para testes."""
    if assinantes is None:
        assinantes = [
            AssinanteInfo(
                nome="RUAN FERNANDES AZEVEDO DA NOBREGA",
                cargo="ADMINISTRADOR",
                engenheiro_habilitado=False,
            )
        ]

    profissional = EntidadesProfissional(
        nome=nome_profissional,
        titulo=titulo_profissional,
        crea_rnp=crea_rnp,
    )

    contratante = EntidadesOrganizacao(
        nome=contratante_nome,
        cnpj=contratante_cnpj,
        cpf=contratante_cpf,
    )

    empresa_executora = None
    if empresa_executora_nome:
        empresa_executora = EntidadesOrganizacao(nome=empresa_executora_nome)

    endereco_obra = None
    if endereco_cidade or endereco_uf:
        endereco_obra = EntidadesEndereco(
            cidade=endereco_cidade,
            uf=endereco_uf,
        )

    return ResultadoAnalise(
        numero_documento=numero_documento,
        profissional=profissional,
        contratante=contratante,
        empresa_executora=empresa_executora,
        endereco_obra=endereco_obra,
        datas=EntidadesData(
            data_inicio=data_inicio,
            data_termino=data_termino,
        ),
        escopo=escopo,
        art_referenciada=art_referenciada,
        visual=AnaliseVisual(
            tem_timbre=tem_timbre,
            tem_assinatura_visual=tem_assinatura_visual,
            assinantes=assinantes,
        ),
        confianca=0.95,
    )


def _make_pacote(
    tem_declaracao: bool = False,
    tem_anuencia: bool = False,
    tem_art: bool = True,
    tem_atestado: bool = True,
) -> PacoteDocumentos:
    """Cria um PacoteDocumentos com MagicMocks para testes."""
    pagina_mock = PaginaDocumento(numero=1, texto_nativo="", imagem_b64="abc123")

    art = None
    if tem_art:
        art = MagicMock(spec=DocumentoCarregado)
        art.tipo = TipoDocumento.ART
        art.caminho = Path("MA20250929762.pdf")
        art.paginas = [pagina_mock]

    atestado = None
    if tem_atestado:
        atestado = MagicMock(spec=DocumentoCarregado)
        atestado.tipo = TipoDocumento.ATESTADO
        atestado.caminho = Path("atestado.pdf")
        atestado.paginas = [pagina_mock]

    complementares = []
    if tem_declaracao:
        decl = MagicMock(spec=DocumentoCarregado)
        decl.tipo = TipoDocumento.DECLARACAO
        decl.caminho = Path("declaracao.pdf")
        decl.paginas = [pagina_mock]
        complementares.append(decl)

    if tem_anuencia:
        anuen = MagicMock(spec=DocumentoCarregado)
        anuen.tipo = TipoDocumento.ANUENCIA
        anuen.caminho = Path("anuencia.pdf")
        anuen.paginas = [pagina_mock]
        complementares.append(anuen)

    return PacoteDocumentos(
        art=art,
        atestado=atestado,
        complementares=complementares,
    )


@pytest.fixture
def mock_compliance_client(monkeypatch):
    """
    Substitui o cliente OpenAI em crea_cat_ai.compliance por MagicMock.
    Retorna especialidade compatível por padrão.
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.output_parsed = ResultadoEspecialidadeGPT(
        compativel=True,
        confianca=0.90,
        justificativa="Engenheiro Eletricista compativel com projeto de iluminacao",
    )
    mock_client.responses.parse.return_value = mock_response
    monkeypatch.setattr("crea_cat_ai.compliance.client", mock_client)
    return mock_client


# ---------------------------------------------------------------------------
# TestDeclaracaoTrigger — CDOC-01, COMP-03
# ---------------------------------------------------------------------------

class TestDeclaracaoTrigger:
    """Testa o trigger de Declaração baseado em engenheiro_habilitado dos assinantes."""

    def test_assinante_nao_engenheiro_requer_declaracao(self, mock_compliance_client):
        """Assinante com engenheiro_habilitado=False → declaracao_necessaria=True."""
        pacote = _make_pacote(tem_declaracao=False)
        atestado = _make_resultado_analise(
            assinantes=[
                AssinanteInfo(nome="RUAN", cargo="ADMINISTRADOR", engenheiro_habilitado=False)
            ]
        )
        resultados = {TipoDocumento.ATESTADO.value: atestado}

        verifs, exigs, necessaria, encontrada = verificar_declaracao(pacote, resultados, None)

        assert necessaria is True

    def test_assinante_engenheiro_nao_requer_declaracao(self, mock_compliance_client):
        """Assinante com engenheiro_habilitado=True → declaracao_necessaria=False."""
        pacote = _make_pacote(tem_declaracao=False)
        atestado = _make_resultado_analise(
            assinantes=[
                AssinanteInfo(
                    nome="ALEXANDRE DE MORAES BUENO NETO",
                    cargo="ENGENHEIRO ELETRICISTA",
                    crea_rnp="1120893194",
                    engenheiro_habilitado=True,
                )
            ]
        )
        resultados = {TipoDocumento.ATESTADO.value: atestado}

        verifs, exigs, necessaria, encontrada = verificar_declaracao(pacote, resultados, None)

        assert necessaria is False

    def test_atestado_ausente_nao_aplicavel(self, mock_compliance_client):
        """Sem Atestado no resultados_analise → verificação NAO_APLICAVEL."""
        pacote = _make_pacote()
        resultados: dict = {}

        verifs, exigs, necessaria, encontrada = verificar_declaracao(pacote, resultados, None)

        assert necessaria is False
        assert len(verifs) > 0
        assert verifs[0].status == StatusCompliance.NAO_APLICAVEL


# ---------------------------------------------------------------------------
# TestDeclaracaoVerificacao — CDOC-02
# ---------------------------------------------------------------------------

class TestDeclaracaoVerificacao:
    """Testa verificação de conformidade da Declaração encontrada."""

    def test_declaracao_encontrada_engenheiro_area_correta(self, mock_compliance_client):
        """Declaração presente + GPT confirma especialidade compatível → CONFORME."""
        pacote = _make_pacote(tem_declaracao=True)
        atestado = _make_resultado_analise(
            assinantes=[
                AssinanteInfo(nome="RUAN", cargo="ADMINISTRADOR", engenheiro_habilitado=False)
            ]
        )
        declaracao = _make_resultado_analise(
            assinantes=[
                AssinanteInfo(
                    nome="ALEXANDRE",
                    cargo="ENGENHEIRO ELETRICISTA",
                    engenheiro_habilitado=True,
                )
            ]
        )
        resultados = {
            TipoDocumento.ATESTADO.value: atestado,
            TipoDocumento.DECLARACAO.value: declaracao,
        }

        verifs, exigs, necessaria, encontrada = verificar_declaracao(pacote, resultados, None)

        assert encontrada is True
        # Verificação CDOC-01 deve ser CONFORME (declaração encontrada)
        cdoc01 = next((v for v in verifs if v.requisito == "CDOC-01"), None)
        assert cdoc01 is not None
        assert cdoc01.status == StatusCompliance.CONFORME

    def test_declaracao_ausente_gera_exigencia(self, mock_compliance_client):
        """Sem Declaração quando necessária → exigência contém 'APRESENTAR DECLARACAO'."""
        pacote = _make_pacote(tem_declaracao=False)
        atestado = _make_resultado_analise(
            assinantes=[
                AssinanteInfo(nome="RUAN", cargo="ADMINISTRADOR", engenheiro_habilitado=False)
            ]
        )
        resultados = {TipoDocumento.ATESTADO.value: atestado}

        verifs, exigs, necessaria, encontrada = verificar_declaracao(pacote, resultados, None)

        assert encontrada is False
        assert len(exigs) > 0
        assert any("APRESENTAR DECLARACAO DE PROFISSIONAL HABILITADO" in e for e in exigs)

    def test_exigencia_formato_crea_correto(self, mock_compliance_client):
        """Exigência deve estar em maiúsculas e conter 'ART. 59' e 'RESOLUCAO 1137'."""
        pacote = _make_pacote(tem_declaracao=False)
        atestado = _make_resultado_analise(
            assinantes=[
                AssinanteInfo(nome="RUAN", cargo="ADMINISTRADOR", engenheiro_habilitado=False)
            ]
        )
        resultados = {TipoDocumento.ATESTADO.value: atestado}

        _, exigs, _, _ = verificar_declaracao(pacote, resultados, None)

        assert len(exigs) > 0
        exigencia = exigs[0]
        # Formato CREA: maiúsculas
        assert exigencia == exigencia.upper()
        # Deve referenciar Art. 59 e Resolução 1137
        assert "ART. 59" in exigencia
        assert "RESOLUCAO 1137" in exigencia


# ---------------------------------------------------------------------------
# TestDeclaracaoCrossRef — CDOC-04
# ---------------------------------------------------------------------------

class TestDeclaracaoCrossRef:
    """Testa cruzamento de dados da Declaração com ART."""

    def test_crea_declarante_matches_profissional(self, mock_compliance_client):
        """CREA normalizado do declarante coincide com ART → CONFORME."""
        pacote = _make_pacote(tem_declaracao=True)
        atestado = _make_resultado_analise(
            assinantes=[
                AssinanteInfo(nome="RUAN", cargo="ADMINISTRADOR", engenheiro_habilitado=False)
            ]
        )
        art = _make_resultado_analise(
            numero_documento="MA20250929762",
            crea_rnp="1120893194",
        )
        # Declaração com mesmo CREA (formato diferente)
        declaracao = _make_resultado_analise(
            crea_rnp="1120893194MA",  # Mesmo número com sufixo de estado
        )
        resultados = {
            TipoDocumento.ATESTADO.value: atestado,
            TipoDocumento.ART.value: art,
            TipoDocumento.DECLARACAO.value: declaracao,
        }

        verifs, exigs, _, _ = verificar_declaracao(pacote, resultados, None)

        # Deve ter verificação CDOC-04 como CONFORME
        cdoc04 = [v for v in verifs if v.requisito == "CDOC-04"]
        assert len(cdoc04) > 0
        crea_verif = next(
            (v for v in cdoc04 if "CREA" in v.descricao.upper()), None
        )
        assert crea_verif is not None
        assert crea_verif.status == StatusCompliance.CONFORME

    def test_art_number_cross_reference(self, mock_compliance_client):
        """Número de ART na Declaração coincide com ART do pacote → CONFORME."""
        pacote = _make_pacote(tem_declaracao=True)
        atestado = _make_resultado_analise(
            assinantes=[
                AssinanteInfo(nome="RUAN", cargo="ADMINISTRADOR", engenheiro_habilitado=False)
            ]
        )
        art = _make_resultado_analise(numero_documento="MA20250929762")
        declaracao = _make_resultado_analise(
            art_referenciada="MA20250929762",  # Referencia correta à ART
        )
        resultados = {
            TipoDocumento.ATESTADO.value: atestado,
            TipoDocumento.ART.value: art,
            TipoDocumento.DECLARACAO.value: declaracao,
        }

        verifs, exigs, _, _ = verificar_declaracao(pacote, resultados, None)

        # Deve ter verificação de número ART
        art_verif = next(
            (v for v in verifs if v.requisito == "CDOC-04" and "ART" in v.descricao.upper()),
            None,
        )
        assert art_verif is not None
        assert art_verif.status == StatusCompliance.CONFORME

    def test_nome_profissional_cross_ref(self, mock_compliance_client):
        """GPT confirma nome da Declaração coincide com ART → CONFORME (mock GPT)."""
        pacote = _make_pacote(tem_declaracao=True)
        atestado = _make_resultado_analise(
            assinantes=[
                AssinanteInfo(nome="RUAN", cargo="ADMINISTRADOR", engenheiro_habilitado=False)
            ]
        )
        declaracao = _make_resultado_analise()
        resultados = {
            TipoDocumento.ATESTADO.value: atestado,
            TipoDocumento.DECLARACAO.value: declaracao,
        }

        verifs, exigs, _, encontrada = verificar_declaracao(pacote, resultados, None)

        assert encontrada is True


# ---------------------------------------------------------------------------
# TestAnuencia — CDOC-03
# ---------------------------------------------------------------------------

class TestAnuencia:
    """Testa detecção de subcontratação e verificação de Anuência."""

    def test_sem_subcontratacao_nao_aplicavel(self, mock_compliance_client):
        """Mesma empresa_executora em ART e Atestado → NAO_APLICAVEL."""
        pacote = _make_pacote()
        art = _make_resultado_analise(empresa_executora_nome="EMPRESA ALFA LTDA")
        atestado = _make_resultado_analise(empresa_executora_nome="EMPRESA ALFA LTDA")
        resultados = {
            TipoDocumento.ART.value: art,
            TipoDocumento.ATESTADO.value: atestado,
        }

        verifs, exigs, necessaria, encontrada = verificar_anuencia(pacote, resultados)

        assert necessaria is False
        assert len(verifs) > 0
        assert verifs[0].status == StatusCompliance.NAO_APLICAVEL

    def test_subcontratacao_sem_anuencia_gera_exigencia(self, mock_compliance_client):
        """Empresas diferentes + sem Anuência → exigência gerada."""
        pacote = _make_pacote(tem_anuencia=False)
        art = _make_resultado_analise(empresa_executora_nome="AR CLIMA SOLUCOES")
        atestado = _make_resultado_analise(empresa_executora_nome="HIDRO-CLIMA CONSTRUCOES")
        resultados = {
            TipoDocumento.ART.value: art,
            TipoDocumento.ATESTADO.value: atestado,
        }

        verifs, exigs, necessaria, encontrada = verificar_anuencia(pacote, resultados)

        assert necessaria is True
        assert encontrada is False
        assert len(exigs) > 0
        assert any("ANUENCIA" in e for e in exigs)

    def test_subcontratacao_com_anuencia_conforme(self, mock_compliance_client):
        """Empresas diferentes + Anuência presente → CONFORME."""
        pacote = _make_pacote(tem_anuencia=True)
        art = _make_resultado_analise(empresa_executora_nome="AR CLIMA SOLUCOES")
        atestado = _make_resultado_analise(empresa_executora_nome="HIDRO-CLIMA CONSTRUCOES")
        resultados = {
            TipoDocumento.ART.value: art,
            TipoDocumento.ATESTADO.value: atestado,
        }

        verifs, exigs, necessaria, encontrada = verificar_anuencia(pacote, resultados)

        assert necessaria is True
        assert encontrada is True
        assert len(exigs) == 0
        assert verifs[0].status == StatusCompliance.CONFORME


# ---------------------------------------------------------------------------
# TestAnexoIV — COMP-01
# ---------------------------------------------------------------------------

class TestAnexoIV:
    """Testa verificação das 6 categorias obrigatórias do Anexo IV."""

    def test_atestado_completo_todas_categorias_conforme(self, mock_compliance_client):
        """Atestado com todos os 6 campos → anexo_iv_completo=True."""
        atestado = _make_resultado_analise(
            contratante_cnpj="36.408.654/0001-04",
            crea_rnp="1120893194",
            escopo="Elaboracao de projeto",
            data_inicio="12/05/2025",
            endereco_cidade="Sao Luis",
            tem_assinatura_visual=True,
            assinantes=[],
        )
        resultados = {TipoDocumento.ATESTADO.value: atestado}

        verifs, exigs, completo = verificar_anexo_iv(resultados)

        assert completo is True
        assert len(exigs) == 0

    def test_atestado_sem_escopo_gera_exigencia(self, mock_compliance_client):
        """escopo=None → NAO_CONFORME + exigência mencionando 'DESCRICAO' e 'ITEM 1.5'."""
        atestado = _make_resultado_analise(escopo=None, assinantes=[])
        resultados = {TipoDocumento.ATESTADO.value: atestado}

        verifs, exigs, completo = verificar_anexo_iv(resultados)

        assert completo is False
        exig_escopo = next((e for e in exigs if "DESCRICAO" in e and "1.5" in e), None)
        assert exig_escopo is not None

    def test_atestado_sem_assinatura_gera_exigencia(self, mock_compliance_client):
        """tem_assinatura_visual=False → NAO_CONFORME + exigência com 'ASSINATURA' e 'ITEM 1.6'."""
        atestado = _make_resultado_analise(
            tem_assinatura_visual=False,
            assinantes=[],
        )
        resultados = {TipoDocumento.ATESTADO.value: atestado}

        verifs, exigs, completo = verificar_anexo_iv(resultados)

        assert completo is False
        exig_assin = next((e for e in exigs if "ASSINATURA" in e and "1.6" in e), None)
        assert exig_assin is not None

    def test_atestado_sem_contratante_cnpj(self, mock_compliance_client):
        """contratante sem cnpj e sem cpf → NAO_CONFORME."""
        atestado = _make_resultado_analise(
            contratante_cnpj=None,
            contratante_cpf=None,
            assinantes=[],
        )
        resultados = {TipoDocumento.ATESTADO.value: atestado}

        verifs, exigs, completo = verificar_anexo_iv(resultados)

        assert completo is False
        # Deve ter exigência sobre identificação do contratante
        exig_cont = next(
            (e for e in exigs if "CONTRATANTE" in e and "CNPJ" in e), None
        )
        assert exig_cont is not None


# ---------------------------------------------------------------------------
# TestRes1160 — COMP-02
# ---------------------------------------------------------------------------

class TestRes1160:
    """Testa hook estrutural da Resolução 1.160/2025."""

    def test_verificacoes_1137_aplicadas(self, mock_compliance_client):
        """verificar_compliance retorna verificações que incluem itens do Anexo IV."""
        pacote = _make_pacote()
        atestado = _make_resultado_analise(
            assinantes=[
                AssinanteInfo(
                    nome="ALEXANDRE",
                    cargo="ENGENHEIRO ELETRICISTA",
                    engenheiro_habilitado=True,
                )
            ]
        )
        resultados = {TipoDocumento.ATESTADO.value: atestado}

        resultado = verificar_compliance(pacote, resultados, None)

        # Deve conter verificações relacionadas ao Anexo IV
        ids_requisitos = [v.requisito for v in resultado.verificacoes]
        # Pelo menos um item COMP-01.x deve estar presente
        assert any("COMP-01" in req for req in ids_requisitos)

    def test_hook_1160_exists(self, mock_compliance_client):
        """_verificacoes_1160_overrides existe e retorna lista."""
        atestado = _make_resultado_analise(assinantes=[])
        resultado = _verificacoes_1160_overrides(atestado)

        assert isinstance(resultado, list)


# ---------------------------------------------------------------------------
# TestVerificarCompliance — orquestrador
# ---------------------------------------------------------------------------

class TestVerificarCompliance:
    """Testa a API pública verificar_compliance()."""

    def test_resultado_compliance_completo(self, mock_compliance_client):
        """verificar_compliance retorna ResultadoCompliance com todos os campos."""
        pacote = _make_pacote()
        atestado = _make_resultado_analise(
            assinantes=[
                AssinanteInfo(
                    nome="ALEXANDRE",
                    cargo="ENGENHEIRO ELETRICISTA",
                    engenheiro_habilitado=True,
                )
            ]
        )
        resultados = {TipoDocumento.ATESTADO.value: atestado}
        cruzamento = ResultadoCruzamento()

        resultado = verificar_compliance(pacote, resultados, cruzamento)

        assert isinstance(resultado, ResultadoCompliance)
        assert isinstance(resultado.verificacoes, list)
        assert isinstance(resultado.exigencias, list)
        assert isinstance(resultado.declaracao_necessaria, bool)
        assert isinstance(resultado.declaracao_encontrada, bool)
        assert isinstance(resultado.anuencia_necessaria, bool)
        assert isinstance(resultado.anuencia_encontrada, bool)
        assert isinstance(resultado.anexo_iv_completo, bool)

    def test_par1_ruan_administrador(self, mock_compliance_client):
        """Simula Par 1 (Ruan Administrador) → declaracao_necessaria=True."""
        pacote = _make_pacote(tem_declaracao=False)
        atestado = _make_resultado_analise(
            assinantes=[
                AssinanteInfo(
                    nome="RUAN FERNANDES AZEVEDO DA NOBREGA",
                    cargo="ADMINISTRADOR",
                    engenheiro_habilitado=False,
                    cpf="620.456.233-94",
                )
            ]
        )
        resultados = {TipoDocumento.ATESTADO.value: atestado}

        resultado = verificar_compliance(pacote, resultados, None)

        assert resultado.declaracao_necessaria is True
        assert resultado.declaracao_encontrada is False
        # Deve ter exigência sobre Declaração
        assert any("DECLARACAO" in e for e in resultado.exigencias)

    def test_resultado_sem_nenhum_documento(self, mock_compliance_client):
        """Pacote sem documentos → ResultadoCompliance retornado (sem erros)."""
        pacote = _make_pacote(tem_art=False, tem_atestado=False)
        resultados: dict = {}

        resultado = verificar_compliance(pacote, resultados, None)

        assert isinstance(resultado, ResultadoCompliance)
        # Sem atestado, nada pode ser verificado
        assert resultado.declaracao_necessaria is False
        assert resultado.anuencia_necessaria is False

    def test_cruzamento_none_aceito(self, mock_compliance_client):
        """resultado_cruzamento=None não causa erro (Phase 5 pode não ter rodado)."""
        pacote = _make_pacote()
        atestado = _make_resultado_analise(assinantes=[])
        resultados = {TipoDocumento.ATESTADO.value: atestado}

        resultado = verificar_compliance(pacote, resultados, None)

        assert isinstance(resultado, ResultadoCompliance)
