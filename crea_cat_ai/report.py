"""
CREA CAT AI - Geração de Relatórios JSON e Markdown

Responsável por:
- Gerar relatório estruturado em JSON (veredito, score, itens verificados, exigências)
- Gerar relatório legível em Markdown para o analista humano do CREA
- Salvar relatórios em output/{par_name}/ com codificação utf-8

Estruturas de saída:
    - JSON (D-15/D-16): relatorio.json — consumo programático / integração SITAC
    - Markdown (D-12/D-13/D-14): relatorio.md — leitura humana pelo analista
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import config
from crea_cat_ai.verdict import Veredito, TipoVeredito, ItemVerificado
from crea_cat_ai.matching import ResultadoCruzamento
from crea_cat_ai.compliance import ResultadoCompliance
from crea_cat_ai.metadata import MetadadosPDF
from crea_cat_ai.signature import ResultadoAssinatura
from crea_cat_ai.ingestion import PacoteDocumentos


# ---------------------------------------------------------------------------
# Constante de rodapé (D-14) — obrigatório em todos os relatórios
# ---------------------------------------------------------------------------

_RODAPE = (
    "PARECER GERADO AUTOMATICAMENTE PELO SISTEMA CREA CAT AI "
    "— A DECISAO FINAL E DO ANALISTA HUMANO DO CREA"
)


# ---------------------------------------------------------------------------
# Função privada: resumo executivo (D-13)
# ---------------------------------------------------------------------------

def _resumo_executivo(veredito: Veredito) -> str:
    """
    Gera o texto do Resumo Executivo com base no TipoVeredito (D-13).

    Args:
        veredito: Objeto Veredito com tipo e score calculados

    Returns:
        Texto do resumo executivo em português (pt-BR)
    """
    score_fmt = f"{veredito.score:.2f}"

    if veredito.tipo == TipoVeredito.ADERENTE:
        return (
            f"Analise indica ADERENCIA entre os documentos apresentados. "
            f"Score de confianca: {score_fmt}. "
            f"Os campos verificados estao em conformidade."
        )
    elif veredito.tipo == TipoVeredito.PENDENTE:
        return (
            f"Analise indica PENDENCIAS nos documentos apresentados. "
            f"Score de confianca: {score_fmt}. "
            f"Recomenda-se atencao aos itens com status DIVERGENTE ou AUSENTE listados abaixo."
        )
    else:  # SUSPEITO
        return (
            f"Analise indica INCONSISTENCIAS GRAVES nos documentos apresentados. "
            f"Score de confianca: {score_fmt}. "
            f"Foram detectadas divergencias criticas que requerem verificacao do analista."
        )


# ---------------------------------------------------------------------------
# Geração do relatório JSON (D-15/D-16)
# ---------------------------------------------------------------------------

def gerar_relatorio_json(
    veredito: Veredito,
    pacote: PacoteDocumentos,
    resultado_cruzamento: Optional[ResultadoCruzamento],
    resultado_compliance: ResultadoCompliance,
    resultados_metadata: dict[str, MetadadosPDF],
    resultados_assinatura: dict[str, ResultadoAssinatura],
    profissional_nome: Optional[str],
    contratante_nome: Optional[str],
    output_dir: Path,
) -> dict:
    """
    Gera o relatório estruturado em JSON e salva em output_dir/relatorio.json.

    Serialização:
    - Pydantic models (Veredito, ResultadoCruzamento, ResultadoCompliance):
      model_dump() — serialização nativa e consistente
    - Dataclasses (MetadadosPDF, ResultadoAssinatura):
      serialização manual — dataclasses não têm model_dump()

    Args:
        veredito: Resultado do veredito calculado (verdict.py)
        pacote: Pacote de documentos com caminhos ART e Atestado
        resultado_cruzamento: Resultado do cruzamento (pode ser None)
        resultado_compliance: Resultado do compliance regulatório
        resultados_metadata: Dict nome_doc -> MetadadosPDF
        resultados_assinatura: Dict nome_doc -> ResultadoAssinatura
        profissional_nome: Nome do profissional (do analysis.py)
        contratante_nome: Nome do contratante (do analysis.py)
        output_dir: Diretório de saída (já deve existir)

    Returns:
        Dict com a estrutura completa do relatório JSON (D-15)
    """
    relatorio: dict = {
        "veredito": veredito.tipo.value,
        "score": round(veredito.score, 4),
        "par": {
            "art": pacote.art.caminho.name if pacote.art else None,
            "atestado": pacote.atestado.caminho.name if pacote.atestado else None,
            "profissional": profissional_nome,
            "contratante": contratante_nome,
        },
        "itens_verificados": [item.model_dump() for item in veredito.itens_verificados],
        "exigencias": list(veredito.exigencias),
        "cruzamento": resultado_cruzamento.model_dump() if resultado_cruzamento else None,
        "compliance": resultado_compliance.model_dump(),
        "metadados": {
            tipo: {
                "creator": m.creator,
                "producer": m.producer,
                "author": m.author,
                "creation_date": str(m.creation_date) if m.creation_date else None,
                "mod_date": str(m.mod_date) if m.mod_date else None,
                "anomalias": m.anomalias,
            }
            for tipo, m in resultados_metadata.items()
        },
        "assinatura_digital": {
            tipo: {
                "presente": a.presente,
                "quantidade": a.quantidade,
                "signatarios": a.signatarios,
            }
            for tipo, a in resultados_assinatura.items()
        },
        "gerado_em": datetime.now().isoformat(),
        "versao": "1.0",
    }

    json_path = output_dir / "relatorio.json"
    json_path.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return relatorio


# ---------------------------------------------------------------------------
# Geração do relatório Markdown (D-12/D-13/D-14)
# ---------------------------------------------------------------------------

def gerar_relatorio_markdown(
    veredito: Veredito,
    pacote: PacoteDocumentos,
    resultado_cruzamento: Optional[ResultadoCruzamento],
    resultado_compliance: ResultadoCompliance,
    resultados_metadata: dict[str, MetadadosPDF],
    resultados_assinatura: dict[str, ResultadoAssinatura],
    profissional_nome: Optional[str],
    contratante_nome: Optional[str],
    output_dir: Path,
) -> str:
    """
    Gera o relatório legível em Markdown e salva em output_dir/relatorio.md.

    Seções (D-12):
    1. Cabeçalho — # PARECER CAT - {art_stem}, profissional, contratante
    2. Veredito — ## VEREDITO: {tipo}, score
    3. Resumo Executivo — texto narrativo (D-13)
    4. Itens Verificados — tabela de todos os campos
    5. Exigências — lista numerada (omitida se vazia)
    6. Detalhes — cruzamento, compliance, metadados, assinatura digital
    7. Rodapé — aviso CREA obrigatório (D-14)

    Args:
        veredito: Resultado do veredito calculado
        pacote: Pacote de documentos com caminhos ART e Atestado
        resultado_cruzamento: Resultado do cruzamento (pode ser None)
        resultado_compliance: Resultado do compliance regulatório
        resultados_metadata: Dict nome_doc -> MetadadosPDF
        resultados_assinatura: Dict nome_doc -> ResultadoAssinatura
        profissional_nome: Nome do profissional (do analysis.py)
        contratante_nome: Nome do contratante (do analysis.py)
        output_dir: Diretório de saída (já deve existir)

    Returns:
        String com o conteúdo completo do relatório Markdown
    """
    linhas: list[str] = []

    # --- Seção 1: Cabeçalho ---
    art_stem = pacote.art.caminho.stem if pacote.art else "SEM-ART"
    linhas.append(f"# PARECER CAT - {art_stem}")
    linhas.append("")

    if profissional_nome:
        linhas.append(f"**Profissional:** {profissional_nome}")
    if contratante_nome:
        linhas.append(f"**Contratante:** {contratante_nome}")
    if pacote.atestado:
        linhas.append(f"**Atestado:** {pacote.atestado.caminho.name}")
    linhas.append(f"**Data do Parecer:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    linhas.append("")

    # --- Seção 2: Veredito ---
    linhas.append(f"## VEREDITO: {veredito.tipo.value}")
    linhas.append("")
    linhas.append(f"**Score de confianca:** {veredito.score:.2f} / 1.00")
    linhas.append("")

    # --- Seção 3: Resumo Executivo ---
    linhas.append("## Resumo Executivo")
    linhas.append("")
    linhas.append(_resumo_executivo(veredito))
    linhas.append("")

    # --- Seção 4: Itens Verificados (tabela) ---
    linhas.append("## Itens Verificados")
    linhas.append("")
    linhas.append("| Campo | Status | Detalhe |")
    linhas.append("|-------|--------|---------|")

    for item in veredito.itens_verificados:
        campo = item.campo.replace("_", " ").title()
        status = item.status.value
        detalhe = item.detalhes or ""
        # Escapar pipes para não quebrar tabela Markdown
        detalhe = detalhe.replace("|", "\\|")
        linhas.append(f"| {campo} | {status} | {detalhe} |")

    linhas.append("")

    # --- Seção 5: Exigências (apenas se houver) ---
    if veredito.exigencias:
        linhas.append("## Exigencias")
        linhas.append("")
        for i, exigencia in enumerate(veredito.exigencias, start=1):
            linhas.append(f"{i}. {exigencia}")
        linhas.append("")

    # --- Seção 6: Detalhes ---
    linhas.append("## Detalhes")
    linhas.append("")

    # 6a. Cruzamento ART x Atestado
    linhas.append("### Cruzamento ART x Atestado")
    linhas.append("")
    if resultado_cruzamento:
        linhas.append(f"- **Campos com MATCH:** {resultado_cruzamento.total_match}")
        linhas.append(f"- **Campos DIVERGENTES:** {resultado_cruzamento.total_divergente}")
        linhas.append(f"- **Campos AUSENTES:** {resultado_cruzamento.total_ausente}")
        if resultado_cruzamento.observacoes:
            linhas.append(f"- **Observacoes:** {resultado_cruzamento.observacoes}")
    else:
        linhas.append("_Cruzamento nao realizado (ART ou Atestado ausente)._")
    linhas.append("")

    # 6b. Compliance regulatório
    linhas.append("### Compliance Regulatorio")
    linhas.append("")
    linhas.append(f"- **Anexo IV completo:** {'Sim' if resultado_compliance.anexo_iv_completo else 'Nao'}")
    linhas.append(f"- **Declaracao (Art. 59 §1º):** necessaria={resultado_compliance.declaracao_necessaria}, encontrada={resultado_compliance.declaracao_encontrada}")
    linhas.append(f"- **Anuencia:** necessaria={resultado_compliance.anuencia_necessaria}, encontrada={resultado_compliance.anuencia_encontrada}")
    if resultado_compliance.observacoes:
        linhas.append(f"- **Observacoes:** {resultado_compliance.observacoes}")
    linhas.append("")

    # 6c. Metadados PDF
    linhas.append("### Metadados PDF")
    linhas.append("")
    for nome_doc, meta in resultados_metadata.items():
        linhas.append(f"**{nome_doc}:**")
        linhas.append(f"- Creator: {meta.creator or 'N/A'}")
        linhas.append(f"- Producer: {meta.producer or 'N/A'}")
        if meta.anomalias:
            linhas.append(f"- Anomalias: {'; '.join(meta.anomalias)}")
        else:
            linhas.append("- Anomalias: nenhuma")
    linhas.append("")

    # 6d. Assinatura Digital
    linhas.append("### Assinatura Digital ICP-Brasil")
    linhas.append("")
    for nome_doc, assinatura in resultados_assinatura.items():
        linhas.append(f"**{nome_doc}:**")
        linhas.append(f"- Presente: {'Sim' if assinatura.presente else 'Nao'}")
        if assinatura.presente:
            linhas.append(f"- Quantidade: {assinatura.quantidade}")
            for sig in assinatura.signatarios:
                nome_sig = sig.get("nome", "Desconhecido")
                valido = sig.get("valido", False)
                linhas.append(f"  - {nome_sig} — {'valida' if valido else 'invalida'}")
    linhas.append("")

    # --- Seção 7: Rodapé ---
    linhas.append("---")
    linhas.append("")
    linhas.append(_RODAPE)
    linhas.append("")

    conteudo = "\n".join(linhas)

    md_path = output_dir / "relatorio.md"
    md_path.write_text(conteudo, encoding="utf-8")

    return conteudo


# ---------------------------------------------------------------------------
# API pública: gerar_relatorios
# ---------------------------------------------------------------------------

def gerar_relatorios(
    veredito: Veredito,
    pacote: PacoteDocumentos,
    resultado_cruzamento: Optional[ResultadoCruzamento],
    resultado_compliance: ResultadoCompliance,
    resultados_metadata: dict[str, MetadadosPDF],
    resultados_assinatura: dict[str, ResultadoAssinatura],
    profissional_nome: Optional[str],
    contratante_nome: Optional[str],
    par_name: str,
) -> dict[str, Path]:
    """
    Gera os dois relatórios finais (JSON + Markdown) e os salva em output/{par_name}/.

    Esta é a função de entrada principal para o módulo report.py.
    Cria o diretório de saída se necessário (parents=True, exist_ok=True).

    Args:
        veredito: Resultado do veredito calculado (verdict.py)
        pacote: Pacote de documentos com caminhos ART e Atestado
        resultado_cruzamento: Resultado do cruzamento (pode ser None)
        resultado_compliance: Resultado do compliance regulatório
        resultados_metadata: Dict nome_doc -> MetadadosPDF
        resultados_assinatura: Dict nome_doc -> ResultadoAssinatura
        profissional_nome: Nome do profissional (do analysis.py)
        contratante_nome: Nome do contratante (do analysis.py)
        par_name: Nome do par de documentos (usado como subdiretório em output/)

    Returns:
        Dict com chaves "json_path" e "md_path" (objetos Path)
    """
    # Criar diretório de saída
    output_dir = config.OUTPUT_DIR / par_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Gerar JSON
    gerar_relatorio_json(
        veredito=veredito,
        pacote=pacote,
        resultado_cruzamento=resultado_cruzamento,
        resultado_compliance=resultado_compliance,
        resultados_metadata=resultados_metadata,
        resultados_assinatura=resultados_assinatura,
        profissional_nome=profissional_nome,
        contratante_nome=contratante_nome,
        output_dir=output_dir,
    )

    # Gerar Markdown
    gerar_relatorio_markdown(
        veredito=veredito,
        pacote=pacote,
        resultado_cruzamento=resultado_cruzamento,
        resultado_compliance=resultado_compliance,
        resultados_metadata=resultados_metadata,
        resultados_assinatura=resultados_assinatura,
        profissional_nome=profissional_nome,
        contratante_nome=contratante_nome,
        output_dir=output_dir,
    )

    json_path = output_dir / "relatorio.json"
    md_path = output_dir / "relatorio.md"

    print(f"Relatorios gerados em: {output_dir}")

    return {
        "json_path": json_path,
        "md_path": md_path,
    }
