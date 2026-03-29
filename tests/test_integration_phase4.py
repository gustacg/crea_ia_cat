"""
Testes de integração da Fase 4 — Metadados e Assinatura Digital.

Executa contra os PDFs reais em "Documentos que crea recebe/".
Todos marcados com @pytest.mark.integration — excluídos do pytest padrão (pytest.ini).

Resultados esperados baseados em RESEARCH.md (verificados empiricamente):
- DECLARACAO_assinado: 1 assinatura, INTACT:TRUSTED,UNTOUCHED
- ACT_Alexandre: 0 assinaturas (presente=False)
- MA20250929762 (ART Par 1): 0 assinaturas
- MA20250957723 (ART Par 2): 0 assinaturas
- saude indigena: 2 assinaturas (Sig1 ILLEGAL_MODIFICATIONS, Sig2 UNTOUCHED)
"""

import pytest
from pathlib import Path

from crea_cat_ai.metadata import processar_documento as extrair_meta, MetadadosPDF
from crea_cat_ai.signature import validar_assinaturas, ResultadoAssinatura

PDF_DIR = Path(__file__).parent.parent / "Documentos que crea recebe"


# === Helpers ===

def _find_pdf(pattern: str) -> Path | None:
    """Busca um PDF no diretório usando glob. Retorna None se não encontrar."""
    if not PDF_DIR.exists():
        return None
    matches = list(PDF_DIR.glob(f"*{pattern}*"))
    return matches[0] if matches else None


def _require_pdf(pattern: str, description: str) -> Path:
    """Retorna o caminho do PDF ou pula o teste se não existir."""
    path = _find_pdf(pattern)
    if path is None:
        pytest.skip(f"PDF não encontrado: {description} (padrão: *{pattern}*)")
    return path


# === Testes de Metadados ===

@pytest.mark.integration
def test_meta_art_par1():
    """
    META-01: ART Par 1 (MA20250929762) deve retornar creator e producer não nulos.
    O PDF real foi gerado com iLovePDF/Adobe, tem docinfo populado.
    """
    pdf = _require_pdf("MA20250929762", "ART Par 1")
    resultado = extrair_meta(pdf)

    assert isinstance(resultado, MetadadosPDF), "extrair_meta deve retornar MetadadosPDF"
    # ART gerado tem creator ou producer — pelo menos um deve estar preenchido
    assert resultado.creator is not None or resultado.producer is not None, (
        f"ART Par 1 deve ter creator ou producer; got creator={resultado.creator!r}, "
        f"producer={resultado.producer!r}"
    )


@pytest.mark.integration
def test_meta_todos_docs():
    """
    META-01: processar_documento() não deve lançar exceção em nenhum dos PDFs de teste.
    Verifica que a API de metadados funciona para todos os 5 documentos.
    """
    if not PDF_DIR.exists():
        pytest.skip(f"Diretório de PDFs não encontrado: {PDF_DIR}")

    pdfs = list(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        pytest.skip("Nenhum PDF encontrado no diretório de teste")

    erros = []
    for pdf in pdfs:
        try:
            resultado = extrair_meta(pdf)
            assert isinstance(resultado, MetadadosPDF), (
                f"{pdf.name}: extrair_meta deve retornar MetadadosPDF"
            )
        except Exception as e:
            erros.append(f"{pdf.name}: {type(e).__name__}: {e}")

    assert not erros, (
        f"extrair_meta() lançou exceções nos seguintes PDFs:\n" + "\n".join(erros)
    )


@pytest.mark.integration
def test_meta_sem_software_suspeito():
    """
    META-02: Nenhum dos 5 PDFs de teste deve sinalizar SOFTWARE_SUSPEITO.
    Os PDFs usam iLovePDF, LibreOffice, Adobe — não estão na lista negra.
    """
    if not PDF_DIR.exists():
        pytest.skip(f"Diretório de PDFs não encontrado: {PDF_DIR}")

    pdfs = list(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        pytest.skip("Nenhum PDF encontrado no diretório de teste")

    suspeitos = []
    for pdf in pdfs:
        resultado = extrair_meta(pdf)
        anomalias_software = [
            a for a in resultado.anomalias
            if "Software de edição suspeito" in a
        ]
        if anomalias_software:
            suspeitos.append(f"{pdf.name}: {anomalias_software}")

    assert not suspeitos, (
        f"PDFs de teste não deveriam ter software suspeito, mas foram detectados:\n"
        + "\n".join(suspeitos)
    )


# === Testes de Assinatura Digital ===

@pytest.mark.integration
def test_sig_declaracao_assinada():
    """
    SIGN-01, SIGN-02: DECLARACAO_assinado deve ter 1 assinatura válida e confiável.
    Resultado esperado: presente=True, quantidade=1, valido=True, confiavel=True.
    """
    pdf = _require_pdf("DECLARACAO", "Declaração assinada")
    resultado = validar_assinaturas(pdf)

    assert isinstance(resultado, ResultadoAssinatura)
    assert resultado.presente is True, (
        f"DECLARACAO deve ter assinatura digital presente; got presente={resultado.presente}"
    )
    assert resultado.quantidade == 1, (
        f"DECLARACAO deve ter 1 assinatura; got quantidade={resultado.quantidade}"
    )
    assert len(resultado.signatarios) == 1, (
        f"DECLARACAO deve ter 1 signatário; got {len(resultado.signatarios)}"
    )

    sig = resultado.signatarios[0]
    assert sig["valido"] is True, (
        f"Assinatura da DECLARACAO deve ser válida; got valido={sig['valido']}, "
        f"erro={sig.get('erro')}, sumario={sig.get('sumario')}"
    )
    assert sig["confiavel"] is True, (
        f"Assinatura da DECLARACAO deve ser confiável (Gov-Br chain); "
        f"got confiavel={sig['confiavel']}, erro={sig.get('erro')}"
    )


@pytest.mark.integration
def test_sig_act_alexandre_sem_assinatura():
    """
    SIGN-01, SIGN-03: ACT_Alexandre não tem assinatura digital.
    Resultado esperado: presente=False, quantidade=0.
    Ausência de assinatura é estado válido (SIGN-03) — sem anomalia.
    """
    pdf = _require_pdf("ACT_Alexandre", "Atestado Alexandre")
    resultado = validar_assinaturas(pdf)

    assert isinstance(resultado, ResultadoAssinatura)
    assert resultado.presente is False, (
        f"ACT_Alexandre não deve ter assinatura digital; got presente={resultado.presente}"
    )
    assert resultado.quantidade == 0, (
        f"ACT_Alexandre deve ter 0 assinaturas; got quantidade={resultado.quantidade}"
    )
    assert resultado.signatarios == [], (
        f"ACT_Alexandre deve ter lista de signatários vazia; got {resultado.signatarios}"
    )


@pytest.mark.integration
def test_sig_art_sem_assinatura():
    """
    SIGN-01, SIGN-03: ART Par 1 (MA20250929762) não tem assinatura digital.
    Resultado esperado: presente=False.
    """
    pdf = _require_pdf("MA20250929762", "ART Par 1")
    resultado = validar_assinaturas(pdf)

    assert isinstance(resultado, ResultadoAssinatura)
    assert resultado.presente is False, (
        f"ART MA20250929762 não deve ter assinatura digital; got presente={resultado.presente}"
    )


@pytest.mark.integration
def test_sig_saude_indigena_duas_assinaturas():
    """
    SIGN-01, SIGN-02: saude indigena.pdf tem 2 assinaturas digitais.
    Resultado esperado: presente=True, quantidade=2.
    Sig1: ILLEGAL_MODIFICATIONS (doc modificado após cert signature)
    Sig2: UNTOUCHED (aprovação da modificação)
    """
    pdf = _require_pdf("saude indigena", "Atestado Saúde Indígena")
    resultado = validar_assinaturas(pdf)

    assert isinstance(resultado, ResultadoAssinatura)
    assert resultado.presente is True, (
        f"saude indigena deve ter assinatura digital; got presente={resultado.presente}"
    )
    assert resultado.quantidade == 2, (
        f"saude indigena deve ter 2 assinaturas; got quantidade={resultado.quantidade}"
    )
    assert len(resultado.signatarios) == 2, (
        f"saude indigena deve ter 2 signatários; got {len(resultado.signatarios)}"
    )


@pytest.mark.integration
def test_sig_ausencia_e_estado_valido():
    """
    SIGN-03: PDFs sem assinatura devem retornar presente=False sem erros ou anomalias.
    Verifica que ausência de assinatura é tratada como estado válido em todos os PDFs
    que sabemos não terem assinatura: ACT_Alexandre, MA20250929762, MA20250957723.
    """
    pdfs_sem_assinatura = [
        ("ACT_Alexandre", "Atestado Alexandre"),
        ("MA20250929762", "ART Par 1"),
        ("MA20250957723", "ART Par 2"),
    ]

    for padrao, descricao in pdfs_sem_assinatura:
        path = _find_pdf(padrao)
        if path is None:
            continue  # Pula silenciosamente se PDF não existe

        resultado = validar_assinaturas(path)

        assert resultado.presente is False, (
            f"{descricao}: deve retornar presente=False; got {resultado.presente}"
        )
        assert resultado.quantidade == 0, (
            f"{descricao}: deve retornar quantidade=0; got {resultado.quantidade}"
        )
        assert resultado.signatarios == [], (
            f"{descricao}: deve retornar signatarios=[]; got {resultado.signatarios}"
        )
        # SIGN-03: ResultadoAssinatura não tem campo 'anomalias'
        assert not hasattr(resultado, "anomalias"), (
            f"ResultadoAssinatura não deve ter campo 'anomalias' (SIGN-03)"
        )
