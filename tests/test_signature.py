"""
Testes unitários para crea_cat_ai/signature.py.

Cobre os requisitos de assinatura digital:
- SIGN-01: pyHanko detecta presença/ausência de assinatura digital em PDFs
- SIGN-02: pyHanko valida certificados Gov-Br/ICP-Brasil (cadeia de confiança, integridade)
- SIGN-03: Ausência de assinatura tratada como estado válido (não gera anomalia)
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from pathlib import Path
from dataclasses import fields as dataclass_fields

from crea_cat_ai.signature import (
    ResultadoAssinatura,
    validar_assinaturas,
    _carregar_govbr_chain,
    GOVBR_CHAIN_URL,
    GOVBR_CHAIN_CACHE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_sig(nome="João Silva", emissor="AC Gov-Br", timestamp=None):
    """Cria um mock de objeto de assinatura pyHanko."""
    sig = MagicMock()
    cert = MagicMock()
    cert.subject.human_friendly = nome
    cert.issuer.human_friendly = emissor
    sig.signer_cert = cert
    sig.self_reported_timestamp = timestamp
    return sig


def _make_mock_reader(sigs=None):
    """Cria um mock de PdfFileReader com lista de assinaturas."""
    reader = MagicMock()
    reader.embedded_regular_signatures = sigs if sigs is not None else []
    return reader


# ---------------------------------------------------------------------------
# SIGN-03: ResultadoAssinatura — estrutura de dados
# ---------------------------------------------------------------------------

class TestResultadoAssinatura:
    """Testa a estrutura do dataclass ResultadoAssinatura."""

    def test_resultado_sem_assinatura(self):
        """ResultadoAssinatura(presente=False) deve ter quantidade=0 e signatarios=[]."""
        resultado = ResultadoAssinatura(presente=False)
        assert resultado.presente is False
        assert resultado.quantidade == 0
        assert resultado.signatarios == []

    def test_resultado_com_assinatura(self):
        """ResultadoAssinatura(presente=True) deve ter estrutura correta."""
        signatario = {
            "nome": "João Silva",
            "emissor": "AC Gov-Br",
            "valido": True,
            "integro": True,
            "confiavel": True,
            "sumario": "INTACT:TRUSTED,UNTOUCHED",
            "erro": None,
        }
        resultado = ResultadoAssinatura(
            presente=True,
            quantidade=1,
            signatarios=[signatario],
        )
        assert resultado.presente is True
        assert resultado.quantidade == 1
        assert len(resultado.signatarios) == 1
        assert resultado.signatarios[0]["valido"] is True
        assert resultado.signatarios[0]["nome"] == "João Silva"

    def test_ausencia_nao_e_anomalia(self):
        """
        SIGN-03: ResultadoAssinatura(presente=False) NÃO deve ter campo anomalias.

        A ausência de assinatura digital é um estado válido (ex: ART e Atestado
        nos PDFs de teste não têm assinatura digital). Não deve gerar flag de suspeito.
        """
        resultado = ResultadoAssinatura(presente=False)
        # Verifica que o dataclass NÃO tem campo 'anomalias'
        nomes_campos = {f.name for f in dataclass_fields(resultado)}
        assert "anomalias" not in nomes_campos, (
            "ResultadoAssinatura NÃO deve ter campo 'anomalias' — "
            "ausência de assinatura é estado válido (SIGN-03)"
        )
        # Verifica também que não tem outros campos de suspeição
        assert "suspeito" not in nomes_campos
        assert "erro" not in nomes_campos


# ---------------------------------------------------------------------------
# SIGN-01: Detecção de assinatura digital
# ---------------------------------------------------------------------------

class TestDeteccaoAssinatura:
    """Testa detecção de presença/ausência de assinatura — SIGN-01."""

    def test_validar_sem_assinatura(self):
        """
        SIGN-01: PDF sem assinaturas deve retornar ResultadoAssinatura(presente=False).
        """
        mock_reader = _make_mock_reader(sigs=[])

        with patch("crea_cat_ai.signature.PdfFileReader", return_value=mock_reader), \
             patch("crea_cat_ai.signature._carregar_govbr_chain", return_value=([], [])), \
             patch("builtins.open", MagicMock()):
            resultado = validar_assinaturas(Path("fake.pdf"))

        assert resultado.presente is False
        assert resultado.quantidade == 0
        assert resultado.signatarios == []

    def test_validar_com_assinatura_valida(self):
        """
        SIGN-01 + SIGN-02: PDF com 1 assinatura válida deve retornar presente=True
        e signatarios[0]['valido']==True.
        """
        sig = _make_mock_sig(nome="Maria Santos", emissor="AC Gov-Br")
        mock_reader = _make_mock_reader(sigs=[sig])

        mock_result = MagicMock()
        mock_result.valid = True
        mock_result.intact = True
        mock_result.trusted = True
        mock_result.summary.return_value = "INTACT:TRUSTED,UNTOUCHED"

        with patch("crea_cat_ai.signature.PdfFileReader", return_value=mock_reader), \
             patch("crea_cat_ai.signature._carregar_govbr_chain", return_value=([], [])), \
             patch("crea_cat_ai.signature.validation.validate_pdf_signature", return_value=mock_result), \
             patch("builtins.open", MagicMock()):
            resultado = validar_assinaturas(Path("fake.pdf"))

        assert resultado.presente is True
        assert resultado.quantidade == 1
        assert len(resultado.signatarios) == 1
        assert resultado.signatarios[0]["valido"] is True
        assert resultado.signatarios[0]["integro"] is True
        assert resultado.signatarios[0]["confiavel"] is True
        assert resultado.signatarios[0]["nome"] == "Maria Santos"

    def test_validar_com_assinatura_invalida(self):
        """
        SIGN-02: Quando validate_pdf_signature lança exceção, signatarios[0]['erro']
        deve conter a mensagem de erro.
        """
        sig = _make_mock_sig()
        mock_reader = _make_mock_reader(sigs=[sig])

        with patch("crea_cat_ai.signature.PdfFileReader", return_value=mock_reader), \
             patch("crea_cat_ai.signature._carregar_govbr_chain", return_value=([], [])), \
             patch("crea_cat_ai.signature.validation.validate_pdf_signature",
                   side_effect=Exception("Cadeia de certificados não encontrada")), \
             patch("builtins.open", MagicMock()):
            resultado = validar_assinaturas(Path("fake.pdf"))

        assert resultado.presente is True
        assert resultado.signatarios[0]["erro"] is not None
        assert "Cadeia de certificados não encontrada" in resultado.signatarios[0]["erro"]
        assert resultado.signatarios[0]["valido"] is False


# ---------------------------------------------------------------------------
# SIGN-02: Parâmetros críticos de validação (anti-patterns do RESEARCH.md)
# ---------------------------------------------------------------------------

class TestParametrosCriticosValidacao:
    """
    Testa que os parâmetros críticos de validação são passados corretamente,
    conforme identificado na pesquisa (pitfalls 1-3 do RESEARCH.md).
    """

    def test_reader_strict_false(self):
        """
        Anti-pattern SIGN-01: PdfFileReader DEVE ser chamado com strict=False.
        PDFs Gov-Br são hybrid-reference e falham com strict=True.
        """
        sig = _make_mock_sig()
        mock_reader = _make_mock_reader(sigs=[sig])

        with patch("crea_cat_ai.signature.PdfFileReader", return_value=mock_reader) as mock_pdf_reader, \
             patch("crea_cat_ai.signature._carregar_govbr_chain", return_value=([], [])), \
             patch("crea_cat_ai.signature.validation.validate_pdf_signature", return_value=MagicMock(
                 valid=True, intact=True, trusted=True, summary=MagicMock(return_value="OK")
             )), \
             patch("builtins.open", MagicMock()) as mock_open:
            validar_assinaturas(Path("fake.pdf"))

        # Verifica que PdfFileReader foi chamado com strict=False
        call_kwargs = mock_pdf_reader.call_args
        assert call_kwargs is not None, "PdfFileReader deve ter sido chamado"
        # strict=False pode estar em args posicionais ou kwargs
        args, kwargs = call_kwargs
        assert kwargs.get("strict") is False or (len(args) > 1 and args[1] is False), \
            "PdfFileReader deve ser chamado com strict=False"

    def test_key_usage_constraints(self):
        """
        Anti-pattern SIGN-02: validate_pdf_signature DEVE receber key_usage_settings
        com digital_signature para compatibilidade com certificados Gov-Br.
        Sem isso, ocorre InvalidCertificateError (non_repudiation ausente).
        """
        from pyhanko.sign.validation.settings import KeyUsageConstraints

        sig = _make_mock_sig()
        mock_reader = _make_mock_reader(sigs=[sig])
        mock_result = MagicMock(valid=True, intact=True, trusted=True,
                                 summary=MagicMock(return_value="OK"))

        with patch("crea_cat_ai.signature.PdfFileReader", return_value=mock_reader), \
             patch("crea_cat_ai.signature._carregar_govbr_chain", return_value=([], [])), \
             patch("crea_cat_ai.signature.validation.validate_pdf_signature",
                   return_value=mock_result) as mock_validate, \
             patch("builtins.open", MagicMock()):
            validar_assinaturas(Path("fake.pdf"))

        mock_validate.assert_called_once()
        call_kwargs = mock_validate.call_args[1]
        assert "key_usage_settings" in call_kwargs, \
            "validate_pdf_signature deve receber key_usage_settings"
        kus = call_kwargs["key_usage_settings"]
        assert isinstance(kus, KeyUsageConstraints), \
            "key_usage_settings deve ser instância de KeyUsageConstraints"
        # Verifica que digital_signature está incluído
        assert "digital_signature" in kus.key_usage, \
            "KeyUsageConstraints deve incluir 'digital_signature'"

    def test_moment_self_reported(self):
        """
        Anti-pattern SIGN-02: ValidationContext DEVE receber moment=sig.self_reported_timestamp.
        Sem isso, certs expirados geram ExpiredError mesmo quando válidos na data de assinatura.

        Verifica que ValidationContext é construído com o timestamp da assinatura,
        usando patch de ValidationContext para capturar os kwargs.
        """
        import datetime
        from pyhanko_certvalidator.context import ValidationContext

        # timezone-aware timestamp (necessário para ValidationContext)
        timestamp = datetime.datetime(2026, 1, 20, 10, 0, 0,
                                      tzinfo=datetime.timezone.utc)
        sig = _make_mock_sig(timestamp=timestamp)
        mock_reader = _make_mock_reader(sigs=[sig])
        mock_result = MagicMock(valid=True, intact=True, trusted=True,
                                 summary=MagicMock(return_value="OK"))

        captured_vc_kwargs = []

        # Intercepta a construção de ValidationContext para capturar kwargs
        original_vc_init = ValidationContext.__init__

        def capture_vc_init(self_vc, *args, **kwargs):
            captured_vc_kwargs.append(kwargs)
            original_vc_init(self_vc, *args, **kwargs)

        with patch("crea_cat_ai.signature.PdfFileReader", return_value=mock_reader), \
             patch("crea_cat_ai.signature._carregar_govbr_chain", return_value=([], [])), \
             patch("crea_cat_ai.signature.validation.validate_pdf_signature",
                   return_value=mock_result), \
             patch.object(ValidationContext, "__init__", capture_vc_init), \
             patch("builtins.open", MagicMock()):
            validar_assinaturas(Path("fake.pdf"))

        assert len(captured_vc_kwargs) >= 1, "ValidationContext deve ter sido criado"
        kwargs = captured_vc_kwargs[0]
        assert "moment" in kwargs, \
            "ValidationContext deve receber kwarg 'moment'"
        assert kwargs["moment"] == timestamp, \
            "ValidationContext deve usar moment=sig.self_reported_timestamp"


# ---------------------------------------------------------------------------
# Carregamento da chain Gov-Br
# ---------------------------------------------------------------------------

class TestCarregarGovBrChain:
    """Testa _carregar_govbr_chain — download e cache do bundle Gov-Br."""

    def test_carregar_govbr_chain_cached(self, tmp_path, monkeypatch):
        """
        Quando certs/govbr-chain.p7b já existe, NÃO deve chamar urlopen.
        O arquivo cacheado deve ser lido diretamente.
        """
        # Criar um arquivo P7B mínimo válido para teste
        # (usamos patch de asn1_cms para evitar parsing real)
        cache_file = tmp_path / "govbr-chain.p7b"
        cache_file.write_bytes(b"fake-p7b-content")

        monkeypatch.setattr("crea_cat_ai.signature.GOVBR_CHAIN_CACHE", cache_file)

        mock_cert = MagicMock()
        mock_cert.subject.human_friendly = "Raiz Gov-Br"
        mock_cert.issuer.human_friendly = "Raiz Gov-Br"  # root: subject == issuer

        mock_content_info = MagicMock()
        mock_signed_data = MagicMock()
        mock_cert_choice = MagicMock()
        mock_cert_choice.chosen = mock_cert
        mock_signed_data.__getitem__ = MagicMock(
            return_value=[mock_cert_choice]
        )
        mock_content_info.__getitem__ = MagicMock(return_value=mock_signed_data)

        with patch("urllib.request.urlopen") as mock_urlopen, \
             patch("crea_cat_ai.signature.asn1_cms.ContentInfo.load",
                   return_value=mock_content_info):
            root_certs, other_certs = _carregar_govbr_chain()

        mock_urlopen.assert_not_called(), \
            "urlopen NÃO deve ser chamado quando o cache já existe"

    def test_carregar_govbr_chain_download(self, tmp_path, monkeypatch):
        """
        Quando certs/govbr-chain.p7b NÃO existe, deve chamar urlopen com GOVBR_CHAIN_URL.
        """
        cache_file = tmp_path / "govbr-chain.p7b"
        # Arquivo não existe — deve baixar
        monkeypatch.setattr("crea_cat_ai.signature.GOVBR_CHAIN_CACHE", cache_file)

        mock_response = MagicMock()
        mock_response.read.return_value = b"fake-p7b-content"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_cert = MagicMock()
        mock_cert.subject.human_friendly = "Raiz Gov-Br"
        mock_cert.issuer.human_friendly = "Raiz Gov-Br"

        mock_content_info = MagicMock()
        mock_signed_data = MagicMock()
        mock_cert_choice = MagicMock()
        mock_cert_choice.chosen = mock_cert
        mock_signed_data.__getitem__ = MagicMock(return_value=[mock_cert_choice])
        mock_content_info.__getitem__ = MagicMock(return_value=mock_signed_data)

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen, \
             patch("crea_cat_ai.signature.asn1_cms.ContentInfo.load",
                   return_value=mock_content_info):
            root_certs, other_certs = _carregar_govbr_chain()

        mock_urlopen.assert_called_once_with(GOVBR_CHAIN_URL, timeout=15), \
            "urlopen deve ser chamado com GOVBR_CHAIN_URL quando cache não existe"


# ---------------------------------------------------------------------------
# Testes de integração (requerem PDFs reais — marcados com integration)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_validar_sem_assinatura_real(pdf_art_path):
    """
    SIGN-01: ART real não tem assinatura digital — deve retornar presente=False.
    """
    resultado = validar_assinaturas(pdf_art_path)
    assert resultado.presente is False
    assert resultado.quantidade == 0


@pytest.mark.integration
def test_validar_declaracao_assinada_real(pdf_dir):
    """
    SIGN-02: DECLARACAO assinada deve retornar presente=True com pelo menos 1 assinatura.
    """
    declaracao = pdf_dir / "944678.2026__DECLARACAO__ENG_2_assinado__1_05022026162803.pdf"
    if not declaracao.exists():
        pytest.skip(f"PDF de declaração não encontrado: {declaracao}")

    resultado = validar_assinaturas(declaracao)
    assert resultado.presente is True
    assert resultado.quantidade >= 1
    assert len(resultado.signatarios) >= 1
    # Pelo menos um signatário deve ter sido validado com sucesso
    algum_valido = any(s.get("erro") is None for s in resultado.signatarios)
    assert algum_valido, "Pelo menos um signatário deve validar sem erro"
