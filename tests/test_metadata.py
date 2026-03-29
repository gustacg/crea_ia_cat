"""
Testes unitários para crea_cat_ai/metadata.py.

Cobre os requisitos:
- META-01: Extração de metadados do PDF (creator, producer, author, datas)
- META-02: Detecção de anomalias (software suspeito, datas inconsistentes)
"""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from crea_cat_ai.metadata import (
    MetadadosPDF,
    extrair_metadados,
    detectar_anomalias,
    _parse_pdf_date,
    processar_documento,
)


# ---------------------------------------------------------------------------
# Testes de _parse_pdf_date
# ---------------------------------------------------------------------------

class TestParsePdfDate:
    """Testa a função auxiliar _parse_pdf_date."""

    def test_parse_pdf_date_standard(self):
        """Data padrão com fuso horário -03'00' retorna datetime com tzinfo."""
        resultado = _parse_pdf_date("D:20250115143000-03'00'")
        assert resultado is not None
        assert resultado.year == 2025
        assert resultado.month == 1
        assert resultado.day == 15
        assert resultado.hour == 14
        assert resultado.minute == 30
        assert resultado.second == 0
        assert resultado.tzinfo is not None

    def test_parse_pdf_date_no_tz(self):
        """Data sem fuso horário retorna datetime naive."""
        resultado = _parse_pdf_date("D:20250115143000")
        assert resultado is not None
        assert resultado.year == 2025
        assert resultado.month == 1
        assert resultado.day == 15
        assert resultado.hour == 14
        assert resultado.minute == 30
        assert resultado.second == 0
        assert resultado.tzinfo is None

    def test_parse_pdf_date_empty(self):
        """String vazia retorna None."""
        resultado = _parse_pdf_date("")
        assert resultado is None

    def test_parse_pdf_date_z(self):
        """Data com fuso UTC ('Z') retorna datetime com tzinfo UTC."""
        resultado = _parse_pdf_date("D:20250115143000Z")
        assert resultado is not None
        assert resultado.year == 2025
        assert resultado.month == 1
        assert resultado.day == 15
        assert resultado.tzinfo is not None

    def test_parse_pdf_date_sem_prefixo_d(self):
        """Data sem prefixo 'D:' ainda é parseada corretamente."""
        resultado = _parse_pdf_date("20250101120000")
        assert resultado is not None
        assert resultado.year == 2025

    def test_parse_pdf_date_invalida(self):
        """String inválida retorna None."""
        resultado = _parse_pdf_date("data-invalida-xyz")
        assert resultado is None


# ---------------------------------------------------------------------------
# META-01: Testes de extrair_metadados (com mock do pikepdf)
# ---------------------------------------------------------------------------

class TestExtrairMetadados:
    """Testa extrair_metadados — META-01."""

    @patch("crea_cat_ai.metadata.pikepdf.open")
    def test_extrai_metadados_campos(self, mock_open):
        """META-01: Todos os campos de docinfo são extraídos corretamente."""
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.docinfo = {
            "/Creator": "iLovePDF",
            "/Producer": "Lib",
            "/Author": "User",
            "/CreationDate": "D:20250101120000",
            "/ModDate": "D:20250102120000",
        }
        mock_open.return_value = mock_pdf

        resultado = extrair_metadados(Path("fake.pdf"))

        assert resultado.creator == "iLovePDF"
        assert resultado.producer == "Lib"
        assert resultado.author == "User"
        assert resultado.creation_date is not None
        assert resultado.creation_date.year == 2025
        assert resultado.creation_date.month == 1
        assert resultado.creation_date.day == 1
        assert resultado.mod_date is not None
        assert resultado.mod_date.day == 2

    @patch("crea_cat_ai.metadata.pikepdf.open")
    def test_extrai_metadados_campos_vazios(self, mock_open):
        """META-01: Docinfo vazio retorna todos os campos como None."""
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.docinfo = {}
        mock_open.return_value = mock_pdf

        resultado = extrair_metadados(Path("fake.pdf"))

        assert resultado.creator is None
        assert resultado.producer is None
        assert resultado.author is None
        assert resultado.creation_date is None
        assert resultado.mod_date is None

    @patch("crea_cat_ai.metadata.pikepdf.open")
    def test_extrai_metadados_retorna_metadadospdf(self, mock_open):
        """META-01: Retorno é instância de MetadadosPDF."""
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.docinfo = {}
        mock_open.return_value = mock_pdf

        resultado = extrair_metadados(Path("fake.pdf"))

        assert isinstance(resultado, MetadadosPDF)


# ---------------------------------------------------------------------------
# META-02: Testes de detectar_anomalias
# ---------------------------------------------------------------------------

class TestDetectarAnomalias:
    """Testa detectar_anomalias — META-02."""

    def test_detecta_software_suspeito_photoshop(self):
        """META-02: creator com Photoshop gera anomalia de software suspeito."""
        m = MetadadosPDF(creator="Adobe Photoshop CC 2024")
        anomalias = detectar_anomalias(m)
        assert len(anomalias) > 0
        mensagem = anomalias[0]
        assert "suspeito" in mensagem.lower() or "Adobe Photoshop" in mensagem

    def test_detecta_software_suspeito_gimp(self):
        """META-02: producer com GIMP gera anomalia de software suspeito."""
        m = MetadadosPDF(producer="GIMP PDF Export Plugin")
        anomalias = detectar_anomalias(m)
        assert len(anomalias) > 0
        mensagem = " ".join(anomalias)
        assert "suspeito" in mensagem.lower() or "GIMP" in mensagem

    def test_detecta_software_suspeito_paint_net(self):
        """META-02: creator com Paint.NET gera anomalia de software suspeito."""
        m = MetadadosPDF(creator="Paint.NET 5.0")
        anomalias = detectar_anomalias(m)
        assert len(anomalias) > 0

    def test_detecta_software_suspeito_inkscape(self):
        """META-02: producer com Inkscape gera anomalia de software suspeito."""
        m = MetadadosPDF(producer="Inkscape 1.3")
        anomalias = detectar_anomalias(m)
        assert len(anomalias) > 0

    def test_software_normal_sem_anomalia(self):
        """META-02: Software normal (Microsoft Word) não gera anomalia."""
        m = MetadadosPDF(creator="Microsoft Word")
        anomalias = detectar_anomalias(m)
        assert anomalias == []

    def test_detecta_data_inconsistente(self):
        """META-02: mod_date anterior a creation_date gera anomalia de data."""
        m = MetadadosPDF(
            creation_date=datetime(2025, 3, 1),
            mod_date=datetime(2025, 1, 1),
        )
        anomalias = detectar_anomalias(m)
        assert len(anomalias) > 0
        mensagem = " ".join(anomalias)
        assert "modificaç" in mensagem.lower() or "modifica" in mensagem.lower() or "Data" in mensagem

    def test_datas_normais_sem_anomalia(self):
        """META-02: mod_date posterior a creation_date não gera anomalia de data."""
        m = MetadadosPDF(
            creation_date=datetime(2025, 1, 1),
            mod_date=datetime(2025, 3, 1),
        )
        anomalias = detectar_anomalias(m)
        assert anomalias == []

    def test_datas_nenhuma_sem_anomalia(self):
        """META-02: Sem datas não gera anomalia de data."""
        m = MetadadosPDF()
        anomalias = detectar_anomalias(m)
        assert anomalias == []

    def test_detectar_anomalias_retorna_lista(self):
        """META-02: detectar_anomalias sempre retorna uma lista."""
        m = MetadadosPDF()
        resultado = detectar_anomalias(m)
        assert isinstance(resultado, list)


# ---------------------------------------------------------------------------
# Testes de processar_documento
# ---------------------------------------------------------------------------

class TestProcessarDocumento:
    """Testa processar_documento — combina extrair + detectar."""

    @patch("crea_cat_ai.metadata.pikepdf.open")
    def test_processar_documento_retorna_metadados_com_anomalias(self, mock_open):
        """processar_documento retorna MetadadosPDF com campo anomalias populado."""
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.docinfo = {
            "/Creator": "Adobe Photoshop CC 2024",
            "/Producer": "Adobe Photoshop",
            "/CreationDate": "D:20250301120000",
            "/ModDate": "D:20250101120000",  # mod anterior à criação — anomalia
        }
        mock_open.return_value = mock_pdf

        resultado = processar_documento(Path("fake.pdf"))

        assert isinstance(resultado, MetadadosPDF)
        assert resultado.creator == "Adobe Photoshop CC 2024"
        assert len(resultado.anomalias) > 0

    @patch("crea_cat_ai.metadata.pikepdf.open")
    def test_processar_documento_sem_anomalias(self, mock_open):
        """processar_documento retorna anomalias vazio para documento normal."""
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.docinfo = {
            "/Creator": "Microsoft Word",
            "/CreationDate": "D:20250101120000",
            "/ModDate": "D:20250201120000",
        }
        mock_open.return_value = mock_pdf

        resultado = processar_documento(Path("fake.pdf"))

        assert isinstance(resultado, MetadadosPDF)
        assert resultado.anomalias == []

    @patch("crea_cat_ai.metadata.pikepdf.open")
    def test_processar_documento_retorna_instancia_correta(self, mock_open):
        """processar_documento retorna instância de MetadadosPDF."""
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.docinfo = {}
        mock_open.return_value = mock_pdf

        resultado = processar_documento(Path("fake.pdf"))

        assert isinstance(resultado, MetadadosPDF)


# ---------------------------------------------------------------------------
# Testes de integração (requerem PDFs reais — marcados com integration)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_extrair_metadados_pdf_real(pdf_art_path):
    """Integração META-01: Extrai metadados de PDF de ART real."""
    resultado = extrair_metadados(pdf_art_path)
    assert isinstance(resultado, MetadadosPDF)
    # PDFs de ART gerados por sistemas eletrônicos têm ao menos creator ou producer
    assert resultado.creator is not None or resultado.producer is not None or resultado.creation_date is not None


@pytest.mark.integration
def test_processar_documento_pdf_real(pdf_art_path):
    """Integração META-01+META-02: processar_documento no PDF de ART real."""
    resultado = processar_documento(pdf_art_path)
    assert isinstance(resultado, MetadadosPDF)
    assert isinstance(resultado.anomalias, list)
