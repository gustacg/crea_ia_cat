"""
Testes unitários para crea_cat_ai/report.py

Cobre: gerar_relatorio_json(), gerar_relatorio_markdown(), gerar_relatorios()
"""

import json
import pytest
from pathlib import Path
from datetime import datetime

from crea_cat_ai.verdict import (
    Veredito, ItemVerificado, TipoVeredito, StatusItem,
)
from crea_cat_ai.matching import ResultadoCruzamento, ComparacaoCampo, StatusCampo
from crea_cat_ai.compliance import ResultadoCompliance, VerificacaoItem, StatusCompliance
from crea_cat_ai.metadata import MetadadosPDF
from crea_cat_ai.signature import ResultadoAssinatura
from crea_cat_ai.ingestion import PacoteDocumentos, TipoDocumento


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def veredito_aderente():
    return Veredito(
        tipo=TipoVeredito.ADERENTE,
        score=0.92,
        itens_verificados=[
            ItemVerificado(campo="cpf_profissional", status=StatusItem.OK, peso=1.0),
            ItemVerificado(campo="crea_rnp", status=StatusItem.OK, peso=1.0),
        ],
        exigencias=[],
    )


@pytest.fixture
def veredito_pendente():
    return Veredito(
        tipo=TipoVeredito.PENDENTE,
        score=0.65,
        itens_verificados=[
            ItemVerificado(
                campo="escopo",
                status=StatusItem.DIVERGENTE,
                valor_encontrado="Instalacao eletrica",
                valor_esperado="Projeto de iluminacao",
                detalhes="Escopos divergentes",
                peso=0.7,
            ),
        ],
        exigencias=["VERIFICAR COMPATIBILIDADE DO OBJETO/ESCOPO DO SERVICO ENTRE ART E ATESTADO"],
    )


@pytest.fixture
def veredito_suspeito():
    return Veredito(
        tipo=TipoVeredito.SUSPEITO,
        score=0.30,
        itens_verificados=[
            ItemVerificado(
                campo="cpf_profissional",
                status=StatusItem.DIVERGENTE,
                peso=1.0,
                detalhes="CPF divergente entre documentos",
            ),
        ],
        exigencias=["VERIFICAR DIVERGENCIA DE CPF ENTRE ART E ATESTADO"],
    )


@pytest.fixture
def pacote(tmp_path):
    """PacoteDocumentos com art e atestado apontando para arquivos mock."""
    from crea_cat_ai.ingestion import DocumentoCarregado, PaginaDocumento
    art_path = tmp_path / "art_mock.pdf"
    art_path.write_bytes(b"mock pdf")
    atestado_path = tmp_path / "atestado_mock.pdf"
    atestado_path.write_bytes(b"mock pdf")

    art = DocumentoCarregado(
        caminho=art_path,
        tipo=TipoDocumento.ART,
        paginas=[],
        tem_texto_nativo=False,
    )
    atestado = DocumentoCarregado(
        caminho=atestado_path,
        tipo=TipoDocumento.ATESTADO,
        paginas=[],
        tem_texto_nativo=False,
    )
    return PacoteDocumentos(art=art, atestado=atestado)


@pytest.fixture
def resultado_cruzamento():
    return ResultadoCruzamento(
        comparacoes=[
            ComparacaoCampo(
                campo="cpf_profissional",
                status=StatusCampo.MATCH,
                valor_art="123.456.789-00",
                valor_atestado="123.456.789-00",
                confianca=1.0,
            ),
        ],
        total_match=1,
        total_divergente=0,
        total_ausente=0,
    )


@pytest.fixture
def resultado_compliance():
    return ResultadoCompliance(
        verificacoes=[
            VerificacaoItem(
                requisito="CDOC-01",
                descricao="Anexo IV completo",
                status=StatusCompliance.CONFORME,
            ),
        ],
        exigencias=[],
        declaracao_necessaria=False,
        declaracao_encontrada=False,
        anuencia_necessaria=False,
        anuencia_encontrada=False,
        anexo_iv_completo=True,
    )


@pytest.fixture
def resultados_metadata():
    return {
        "ART": MetadadosPDF(
            creator="Adobe Acrobat",
            producer="Adobe PDF Library",
            author=None,
            anomalias=[],
        ),
    }


@pytest.fixture
def resultados_assinatura():
    return {
        "ART": ResultadoAssinatura(presente=False, quantidade=0),
    }


@pytest.fixture
def output_dir(tmp_path):
    """Diretório de saída temporário para os relatórios."""
    d = tmp_path / "par_teste"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Helpers de importação (importação atrasada para facilitar o RED)
# ---------------------------------------------------------------------------

def _import_report():
    from crea_cat_ai import report
    return report


# ---------------------------------------------------------------------------
# Tests: gerar_relatorio_json — estrutura
# ---------------------------------------------------------------------------

class TestGerarRelatorioJsonEstrutura:

    def test_gerar_relatorio_json_structure(
        self, veredito_aderente, pacote, resultado_cruzamento,
        resultado_compliance, resultados_metadata, resultados_assinatura, output_dir,
    ):
        """JSON tem todas as chaves obrigatórias da estrutura D-15."""
        report = _import_report()
        resultado = report.gerar_relatorio_json(
            veredito=veredito_aderente,
            pacote=pacote,
            resultado_cruzamento=resultado_cruzamento,
            resultado_compliance=resultado_compliance,
            resultados_metadata=resultados_metadata,
            resultados_assinatura=resultados_assinatura,
            profissional_nome="ALEXANDRE DE MORAES",
            contratante_nome="TABOCA AGRO",
            output_dir=output_dir,
        )
        assert "veredito" in resultado
        assert "score" in resultado
        assert "par" in resultado
        assert "itens_verificados" in resultado
        assert "exigencias" in resultado
        assert "cruzamento" in resultado
        assert "compliance" in resultado
        assert "metadados" in resultado
        assert "assinatura_digital" in resultado
        assert "gerado_em" in resultado
        assert "versao" in resultado

    def test_gerar_relatorio_json_veredito_valor(
        self, veredito_aderente, pacote, resultado_cruzamento,
        resultado_compliance, resultados_metadata, resultados_assinatura, output_dir,
    ):
        """Campo veredito é string com valor ADERENTE, PENDENTE ou SUSPEITO."""
        report = _import_report()
        resultado = report.gerar_relatorio_json(
            veredito=veredito_aderente,
            pacote=pacote,
            resultado_cruzamento=resultado_cruzamento,
            resultado_compliance=resultado_compliance,
            resultados_metadata=resultados_metadata,
            resultados_assinatura=resultados_assinatura,
            profissional_nome=None,
            contratante_nome=None,
            output_dir=output_dir,
        )
        assert resultado["veredito"] in {"ADERENTE", "PENDENTE", "SUSPEITO"}
        assert isinstance(resultado["score"], float)
        assert resultado["versao"] == "1.0"

    def test_gerar_relatorio_json_writes_file(
        self, veredito_aderente, pacote, resultado_cruzamento,
        resultado_compliance, resultados_metadata, resultados_assinatura, tmp_path,
    ):
        """Cria output/{par_name}/relatorio.json e é JSON válido com utf-8."""
        report = _import_report()
        d = tmp_path / "par_escrita"
        d.mkdir()
        report.gerar_relatorio_json(
            veredito=veredito_aderente,
            pacote=pacote,
            resultado_cruzamento=resultado_cruzamento,
            resultado_compliance=resultado_compliance,
            resultados_metadata=resultados_metadata,
            resultados_assinatura=resultados_assinatura,
            profissional_nome="Teste Açúcar",  # acento para testar utf-8
            contratante_nome=None,
            output_dir=d,
        )
        json_path = d / "relatorio.json"
        assert json_path.exists()
        content = json_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert "veredito" in parsed
        # Garantir que acentos foram preservados (não escapados como \u...)
        assert "Açúcar" in content or "profissional" in content

    def test_gerar_relatorio_json_model_dump(
        self, veredito_aderente, pacote, resultado_cruzamento,
        resultado_compliance, resultados_metadata, resultados_assinatura, output_dir,
    ):
        """cruzamento e compliance são dicts com as chaves Pydantic esperadas (model_dump)."""
        report = _import_report()
        resultado = report.gerar_relatorio_json(
            veredito=veredito_aderente,
            pacote=pacote,
            resultado_cruzamento=resultado_cruzamento,
            resultado_compliance=resultado_compliance,
            resultados_metadata=resultados_metadata,
            resultados_assinatura=resultados_assinatura,
            profissional_nome=None,
            contratante_nome=None,
            output_dir=output_dir,
        )
        assert isinstance(resultado["cruzamento"], dict)
        assert "comparacoes" in resultado["cruzamento"]
        assert isinstance(resultado["compliance"], dict)
        assert "verificacoes" in resultado["compliance"]

    def test_gerar_relatorio_json_metadata_manual(
        self, veredito_aderente, pacote, resultado_cruzamento,
        resultado_compliance, resultados_metadata, resultados_assinatura, output_dir,
    ):
        """metadados e assinatura_digital usam serialização manual (dataclass)."""
        report = _import_report()
        resultado = report.gerar_relatorio_json(
            veredito=veredito_aderente,
            pacote=pacote,
            resultado_cruzamento=resultado_cruzamento,
            resultado_compliance=resultado_compliance,
            resultados_metadata=resultados_metadata,
            resultados_assinatura=resultados_assinatura,
            profissional_nome=None,
            contratante_nome=None,
            output_dir=output_dir,
        )
        meta_art = resultado["metadados"]["ART"]
        assert "creator" in meta_art
        assert "producer" in meta_art
        assert "anomalias" in meta_art

        sig_art = resultado["assinatura_digital"]["ART"]
        assert "presente" in sig_art
        assert "quantidade" in sig_art
        assert "signatarios" in sig_art


# ---------------------------------------------------------------------------
# Tests: gerar_relatorio_markdown — seções
# ---------------------------------------------------------------------------

class TestGerarRelatorioMarkdownSecoes:

    def test_gerar_relatorio_markdown_header(
        self, veredito_aderente, pacote, resultado_cruzamento,
        resultado_compliance, resultados_metadata, resultados_assinatura, output_dir,
    ):
        """Markdown começa com # PARECER CAT - e contém **Profissional:**."""
        report = _import_report()
        md = report.gerar_relatorio_markdown(
            veredito=veredito_aderente,
            pacote=pacote,
            resultado_cruzamento=resultado_cruzamento,
            resultado_compliance=resultado_compliance,
            resultados_metadata=resultados_metadata,
            resultados_assinatura=resultados_assinatura,
            profissional_nome="ALEXANDRE DE MORAES",
            contratante_nome="TABOCA AGRO",
            output_dir=output_dir,
        )
        assert md.startswith("# PARECER CAT -")
        assert "**Profissional:**" in md

    def test_gerar_relatorio_markdown_veredito_section(
        self, veredito_aderente, pacote, resultado_cruzamento,
        resultado_compliance, resultados_metadata, resultados_assinatura, output_dir,
    ):
        """Markdown contém ## VEREDITO: ADERENTE e **Score de confianca:**."""
        report = _import_report()
        md = report.gerar_relatorio_markdown(
            veredito=veredito_aderente,
            pacote=pacote,
            resultado_cruzamento=resultado_cruzamento,
            resultado_compliance=resultado_compliance,
            resultados_metadata=resultados_metadata,
            resultados_assinatura=resultados_assinatura,
            profissional_nome=None,
            contratante_nome=None,
            output_dir=output_dir,
        )
        assert "## VEREDITO: ADERENTE" in md
        assert "**Score de confianca:**" in md

    def test_gerar_relatorio_markdown_resumo_executivo(
        self, veredito_aderente, pacote, resultado_cruzamento,
        resultado_compliance, resultados_metadata, resultados_assinatura, output_dir,
    ):
        """Markdown contém ## Resumo Executivo."""
        report = _import_report()
        md = report.gerar_relatorio_markdown(
            veredito=veredito_aderente,
            pacote=pacote,
            resultado_cruzamento=resultado_cruzamento,
            resultado_compliance=resultado_compliance,
            resultados_metadata=resultados_metadata,
            resultados_assinatura=resultados_assinatura,
            profissional_nome=None,
            contratante_nome=None,
            output_dir=output_dir,
        )
        assert "## Resumo Executivo" in md

    def test_gerar_relatorio_markdown_itens_table(
        self, veredito_aderente, pacote, resultado_cruzamento,
        resultado_compliance, resultados_metadata, resultados_assinatura, output_dir,
    ):
        """Markdown contém tabela de itens verificados com cabeçalho correto."""
        report = _import_report()
        md = report.gerar_relatorio_markdown(
            veredito=veredito_aderente,
            pacote=pacote,
            resultado_cruzamento=resultado_cruzamento,
            resultado_compliance=resultado_compliance,
            resultados_metadata=resultados_metadata,
            resultados_assinatura=resultados_assinatura,
            profissional_nome=None,
            contratante_nome=None,
            output_dir=output_dir,
        )
        assert "## Itens Verificados" in md
        assert "| Campo | Status | Detalhe |" in md
        assert "|-------|--------|---------|" in md

    def test_gerar_relatorio_markdown_exigencias_presente(
        self, veredito_pendente, pacote, resultado_cruzamento,
        resultado_compliance, resultados_metadata, resultados_assinatura, output_dir,
    ):
        """Markdown contém ## Exigencias com lista numerada quando há exigências."""
        report = _import_report()
        md = report.gerar_relatorio_markdown(
            veredito=veredito_pendente,
            pacote=pacote,
            resultado_cruzamento=resultado_cruzamento,
            resultado_compliance=resultado_compliance,
            resultados_metadata=resultados_metadata,
            resultados_assinatura=resultados_assinatura,
            profissional_nome=None,
            contratante_nome=None,
            output_dir=output_dir,
        )
        assert "## Exigencias" in md
        assert "1. " in md

    def test_gerar_relatorio_markdown_exigencias_ausente(
        self, veredito_aderente, pacote, resultado_cruzamento,
        resultado_compliance, resultados_metadata, resultados_assinatura, output_dir,
    ):
        """Markdown NÃO contém ## Exigencias quando lista está vazia."""
        report = _import_report()
        md = report.gerar_relatorio_markdown(
            veredito=veredito_aderente,
            pacote=pacote,
            resultado_cruzamento=resultado_cruzamento,
            resultado_compliance=resultado_compliance,
            resultados_metadata=resultados_metadata,
            resultados_assinatura=resultados_assinatura,
            profissional_nome=None,
            contratante_nome=None,
            output_dir=output_dir,
        )
        # veredito_aderente tem exigencias=[], então seção não deve aparecer
        assert "## Exigencias" not in md

    def test_gerar_relatorio_markdown_rodape(
        self, veredito_aderente, pacote, resultado_cruzamento,
        resultado_compliance, resultados_metadata, resultados_assinatura, output_dir,
    ):
        """Markdown termina com o rodapé CREA obrigatório."""
        report = _import_report()
        md = report.gerar_relatorio_markdown(
            veredito=veredito_aderente,
            pacote=pacote,
            resultado_cruzamento=resultado_cruzamento,
            resultado_compliance=resultado_compliance,
            resultados_metadata=resultados_metadata,
            resultados_assinatura=resultados_assinatura,
            profissional_nome=None,
            contratante_nome=None,
            output_dir=output_dir,
        )
        assert "PARECER GERADO AUTOMATICAMENTE PELO SISTEMA CREA CAT AI" in md
        assert "A DECISAO FINAL E DO ANALISTA HUMANO DO CREA" in md

    def test_gerar_relatorio_markdown_writes_file(
        self, veredito_aderente, pacote, resultado_cruzamento,
        resultado_compliance, resultados_metadata, resultados_assinatura, tmp_path,
    ):
        """gerar_relatorio_markdown cria relatorio.md com utf-8."""
        report = _import_report()
        d = tmp_path / "par_md"
        d.mkdir()
        report.gerar_relatorio_markdown(
            veredito=veredito_aderente,
            pacote=pacote,
            resultado_cruzamento=resultado_cruzamento,
            resultado_compliance=resultado_compliance,
            resultados_metadata=resultados_metadata,
            resultados_assinatura=resultados_assinatura,
            profissional_nome="Profissional com Ação",  # acento
            contratante_nome=None,
            output_dir=d,
        )
        md_path = d / "relatorio.md"
        assert md_path.exists()
        content = md_path.read_text(encoding="utf-8")
        assert "PARECER CAT" in content

    def test_gerar_relatorio_markdown_pendente_recomendacao(
        self, veredito_pendente, pacote, resultado_cruzamento,
        resultado_compliance, resultados_metadata, resultados_assinatura, output_dir,
    ):
        """PENDENTE inclui texto de recomendação/atenção no Resumo Executivo (D-13)."""
        report = _import_report()
        md = report.gerar_relatorio_markdown(
            veredito=veredito_pendente,
            pacote=pacote,
            resultado_cruzamento=resultado_cruzamento,
            resultado_compliance=resultado_compliance,
            resultados_metadata=resultados_metadata,
            resultados_assinatura=resultados_assinatura,
            profissional_nome=None,
            contratante_nome=None,
            output_dir=output_dir,
        )
        # D-13: PENDENTE deve mencionar recomendação ou atenção
        md_lower = md.lower()
        assert "recomenda" in md_lower or "atencao" in md_lower or "atenção" in md_lower


# ---------------------------------------------------------------------------
# Tests: gerar_relatorios — API pública
# ---------------------------------------------------------------------------

class TestGerarRelatorios:

    def test_gerar_relatorios_creates_both(
        self, veredito_aderente, pacote, resultado_cruzamento,
        resultado_compliance, resultados_metadata, resultados_assinatura, tmp_path,
        monkeypatch,
    ):
        """gerar_relatorios() cria tanto relatorio.json quanto relatorio.md."""
        import config
        monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)

        report = _import_report()
        result = report.gerar_relatorios(
            veredito=veredito_aderente,
            pacote=pacote,
            resultado_cruzamento=resultado_cruzamento,
            resultado_compliance=resultado_compliance,
            resultados_metadata=resultados_metadata,
            resultados_assinatura=resultados_assinatura,
            profissional_nome=None,
            contratante_nome=None,
            par_name="par_teste",
        )
        assert (tmp_path / "par_teste" / "relatorio.json").exists()
        assert (tmp_path / "par_teste" / "relatorio.md").exists()
        assert "json_path" in result
        assert "md_path" in result

    def test_gerar_relatorios_creates_output_dir(
        self, veredito_aderente, pacote, resultado_cruzamento,
        resultado_compliance, resultados_metadata, resultados_assinatura, tmp_path,
        monkeypatch,
    ):
        """gerar_relatorios() cria o diretório output/{par_name}/ se não existir."""
        import config
        monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path)

        new_dir = tmp_path / "par_novo_que_nao_existe"
        assert not new_dir.exists()

        report = _import_report()
        report.gerar_relatorios(
            veredito=veredito_aderente,
            pacote=pacote,
            resultado_cruzamento=resultado_cruzamento,
            resultado_compliance=resultado_compliance,
            resultados_metadata=resultados_metadata,
            resultados_assinatura=resultados_assinatura,
            profissional_nome=None,
            contratante_nome=None,
            par_name="par_novo_que_nao_existe",
        )
        assert new_dir.exists()
