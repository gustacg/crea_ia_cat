"""
CREA CAT AI - Cruzamento de Campos entre Documentos

Responsável por:
- Match exato: CPF, CNPJ, CREA/RNP (tratados como equivalentes), ART referenciada
- Validação de intervalo de datas (atestado DENTRO do intervalo da ART)
- Match fuzzy/semântico via GPT-4.1: nomes, empresas, endereços, escopo
- Comparação de valores financeiros e número de contrato
"""

import re
from datetime import datetime, date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from openai import OpenAI

import config
from crea_cat_ai.analysis import ResultadoAnalise, EntidadesEndereco, normalizar_crea_rnp


# ---------------------------------------------------------------------------
# Modelos Pydantic — estruturas de dados (D-04, D-05, D-06)
# ---------------------------------------------------------------------------

class StatusCampo(str, Enum):
    """Status de comparação de um campo entre ART e Atestado."""
    MATCH = "MATCH"
    DIVERGENTE = "DIVERGENTE"
    AUSENTE = "AUSENTE"


class ComparacaoCampo(BaseModel):
    """Resultado da comparação de um campo específico entre ART e Atestado."""
    campo: str                              # Nome do campo (ex: "cpf", "escopo")
    status: StatusCampo
    valor_art: Optional[str] = None         # Valor extraído da ART
    valor_atestado: Optional[str] = None    # Valor extraído do Atestado
    confianca: float = 1.0                  # 1.0 para match exato; score GPT para fuzzy
    detalhes: Optional[str] = None          # Explicação (obrigatório quando DIVERGENTE ou AUSENTE)


class ResultadoCruzamento(BaseModel):
    """Resultado completo do cruzamento entre ART e Atestado."""
    comparacoes: list[ComparacaoCampo] = Field(default_factory=list)
    total_match: int = 0
    total_divergente: int = 0
    total_ausente: int = 0
    observacoes: Optional[str] = None


class ComparacaoGPT(BaseModel):
    """Resultado de comparação de um campo retornado pelo GPT-4.1."""
    campo: str
    status: StatusCampo
    confianca: float = Field(description="Score de confiança 0.0 a 1.0")
    detalhes: str = Field(description="Justificativa obrigatória da comparação")


class ResultadoGPTCruzamento(BaseModel):
    """Resultado estruturado retornado pelo GPT-4.1 para comparação em lote."""
    comparacoes: list[ComparacaoGPT]


# ---------------------------------------------------------------------------
# Cliente OpenAI (módulo-level — reutilizado entre chamadas)
# ---------------------------------------------------------------------------

client = OpenAI(api_key=config.OPENAI_API_KEY)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

DATE_FORMATS = ["%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"]

PROMPT_CRUZAMENTO = """Você é um especialista em análise de documentos técnicos do CREA (Conselho Regional de Engenharia e Agronomia do Brasil).

Compare os campos dos dois documentos abaixo (ART e Atestado) e retorne uma comparação para cada campo informado.

REGRA CRÍTICA — Critério de MATCH vs DIVERGENTE:
- MATCH: variações de formatação, abreviação, capitalização ou pontuação do MESMO nome/entidade.
  Exemplos de MATCH: "Taboca Agro" vs "TABOCA AGRO NEGÓCIOS LTDA", "Rua Dom Pedro II" vs "R. Dom Pedro 2"
- DIVERGENTE: nomes ou entidades DISTINTAS, mesmo que pareçam relacionados.
  Exemplos de DIVERGENTE: "AR CLIMA SOLUÇÕES" vs "HIDRO-CLIMA Construções" são empresas COMPLETAMENTE DIFERENTES.
- AUSENTE: campo não informado ("N/A") em um ou ambos os documentos.

Para escopo/objeto: retorne confianca entre 0.0 e 1.0 indicando similaridade semântica.
confianca >= 0.7 + status MATCH = escopos compatíveis.
confianca < 0.7 + status DIVERGENTE = escopos incompatíveis.

Retorne exatamente os campos solicitados, sem adicionar nem omitir campos."""


# ---------------------------------------------------------------------------
# Layer 1 — Match exato de identificadores (D-02, D-09, XREF-01)
# ---------------------------------------------------------------------------

def _status_exato(campo: str, val_art: str | None, val_atestado: str | None) -> ComparacaoCampo:
    """
    Compara dois valores com match exato após normalização.

    Regras (D-08):
    - Ambos ausentes → AUSENTE
    - Um ausente → AUSENTE
    - Iguais → MATCH
    - Diferentes → DIVERGENTE
    """
    if val_art is None and val_atestado is None:
        return ComparacaoCampo(
            campo=campo,
            status=StatusCampo.AUSENTE,
            detalhes="Campo ausente em ambos os documentos",
        )
    if val_art is None or val_atestado is None:
        presente = val_art or val_atestado
        return ComparacaoCampo(
            campo=campo,
            status=StatusCampo.AUSENTE,
            valor_art=val_art,
            valor_atestado=val_atestado,
            detalhes=f"Campo presente somente em um documento: {presente}",
        )
    if val_art == val_atestado:
        return ComparacaoCampo(
            campo=campo,
            status=StatusCampo.MATCH,
            valor_art=val_art,
            valor_atestado=val_atestado,
            confianca=1.0,
        )
    return ComparacaoCampo(
        campo=campo,
        status=StatusCampo.DIVERGENTE,
        valor_art=val_art,
        valor_atestado=val_atestado,
        confianca=0.0,
        detalhes=f"Valores divergentes após normalização: {val_art!r} != {val_atestado!r}",
    )


def _comparar_identificadores(
    art: ResultadoAnalise,
    atestado: ResultadoAnalise,
) -> list[ComparacaoCampo]:
    """
    Compara identificadores com match exato (CPF, CNPJ, CREA/RNP, ART referenciada).

    Usa normalizar_crea_rnp() para remover não-dígitos antes de comparar (D-09).
    """
    comparacoes = []

    # CREA/RNP — D-09: strip non-digits antes de comparar
    crea_art = normalizar_crea_rnp(
        art.profissional.crea_rnp if art.profissional else None
    )
    crea_atestado = normalizar_crea_rnp(
        atestado.profissional.crea_rnp if atestado.profissional else None
    )
    comparacoes.append(_status_exato("crea_rnp", crea_art, crea_atestado))

    # CPF do profissional
    cpf_art = normalizar_crea_rnp(
        art.profissional.cpf if art.profissional else None
    )
    cpf_atestado = normalizar_crea_rnp(
        atestado.profissional.cpf if atestado.profissional else None
    )
    comparacoes.append(_status_exato("cpf_profissional", cpf_art, cpf_atestado))

    # CNPJ contratante
    cnpj_art = normalizar_crea_rnp(
        art.contratante.cnpj if art.contratante else None
    )
    cnpj_atestado = normalizar_crea_rnp(
        atestado.contratante.cnpj if atestado.contratante else None
    )
    comparacoes.append(_status_exato("cnpj_contratante", cnpj_art, cnpj_atestado))

    # ART referenciada: atestado.art_referenciada vs art.numero_documento
    num_art = normalizar_crea_rnp(art.numero_documento)
    art_ref = normalizar_crea_rnp(atestado.art_referenciada)
    # Só compara se atestado referencia uma ART
    if art_ref is not None or num_art is not None:
        comparacoes.append(_status_exato("art_referenciada", num_art, art_ref))

    return comparacoes


# ---------------------------------------------------------------------------
# Layer 2 — Validação de intervalo de datas (D-03, D-07, D-08, XREF-04)
# ---------------------------------------------------------------------------

def _parse_date(valor: str | None) -> date | None:
    """
    Parseia string de data em múltiplos formatos.

    Tentativas: DD/MM/YYYY, YYYY-MM-DD, DD/MM/YY.
    Nunca levanta exceção — retorna None para malformado (D-08).
    """
    if not valor:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(valor.strip(), fmt).date()
        except ValueError:
            continue
    return None  # Malformado → tratar como ausente (D-08)


def _comparar_datas(
    art: ResultadoAnalise,
    atestado: ResultadoAnalise,
) -> ComparacaoCampo:
    """
    Valida que as datas do atestado estão DENTRO do intervalo da ART.

    Regras (D-07, D-08):
    - Datas da ART ausentes/malformadas → AUSENTE
    - Datas do atestado ausentes → AUSENTE
    - Atestado fora do intervalo → DIVERGENTE com detalhes das violações
    - Dentro do intervalo → MATCH
    """
    inicio_art = _parse_date(art.datas.data_inicio)
    termino_art = _parse_date(art.datas.data_termino)
    inicio_atestado = _parse_date(atestado.datas.data_inicio)
    termino_atestado = _parse_date(atestado.datas.data_termino)

    # D-08: Datas da ART ausentes/malformadas — não é possível validar
    if inicio_art is None or termino_art is None:
        return ComparacaoCampo(
            campo="intervalo_datas",
            status=StatusCampo.AUSENTE,
            detalhes="Datas da ART ausentes ou malformadas — não é possível validar intervalo",
        )

    # D-08: Datas do atestado ausentes → AUSENTE (ausência não é fraude)
    if inicio_atestado is None and termino_atestado is None:
        return ComparacaoCampo(
            campo="intervalo_datas",
            status=StatusCampo.AUSENTE,
            valor_art=f"{art.datas.data_inicio} a {art.datas.data_termino}",
            detalhes="Datas do atestado ausentes ou malformadas",
        )

    # D-07: Verificação de contenção estrita
    violacoes = []
    if inicio_atestado and inicio_atestado < inicio_art:
        violacoes.append(
            f"Início do atestado ({inicio_atestado}) é anterior ao início da ART ({inicio_art})"
        )
    if termino_atestado and termino_atestado > termino_art:
        violacoes.append(
            f"Término do atestado ({termino_atestado}) é posterior ao término da ART ({termino_art})"
        )

    if violacoes:
        return ComparacaoCampo(
            campo="intervalo_datas",
            status=StatusCampo.DIVERGENTE,
            valor_art=f"{art.datas.data_inicio} a {art.datas.data_termino}",
            valor_atestado=f"{atestado.datas.data_inicio} a {atestado.datas.data_termino}",
            confianca=0.0,
            detalhes="; ".join(violacoes),
        )

    return ComparacaoCampo(
        campo="intervalo_datas",
        status=StatusCampo.MATCH,
        valor_art=f"{art.datas.data_inicio} a {art.datas.data_termino}",
        valor_atestado=f"{atestado.datas.data_inicio} a {atestado.datas.data_termino}",
        confianca=1.0,
    )


# ---------------------------------------------------------------------------
# Layer 3 — Comparação fuzzy/semântica via GPT-4.1 (D-01, D-10, D-11, XREF-02, XREF-03, XREF-05, XREF-06, XREF-07)
# ---------------------------------------------------------------------------

def _formatar_endereco(endereco: EntidadesEndereco | None) -> str:
    """Formata EntidadesEndereco como string legível para o GPT."""
    if endereco is None:
        return "N/A"
    partes = []
    if endereco.logradouro:
        partes.append(endereco.logradouro)
    if endereco.numero:
        partes.append(endereco.numero)
    if endereco.bairro:
        partes.append(endereco.bairro)
    if endereco.cidade:
        partes.append(endereco.cidade)
    if endereco.uf:
        partes.append(endereco.uf)
    if endereco.cep:
        partes.append(endereco.cep)
    return ", ".join(partes) if partes else "N/A"


def _comparar_via_gpt(
    art: ResultadoAnalise,
    atestado: ResultadoAnalise,
) -> list[ComparacaoCampo]:
    """
    Compara campos fuzzy/semânticos via GPT-4.1 em uma única chamada em lote (D-01).

    Campos comparados: nome_profissional, empresa_contratante, empresa_executora,
    endereco_obra, escopo, valor_contrato, contrato_numero.

    Fallback (D-08): se output_parsed=None, retorna todos os campos como AUSENTE.
    """
    campos_esperados = [
        "nome_profissional",
        "empresa_contratante",
        "empresa_executora",
        "endereco_obra",
        "escopo",
        "valor_contrato",
        "contrato_numero",
    ]

    # Formatar valores para o prompt
    nome_prof_art = art.profissional.nome if art.profissional else "N/A"
    nome_prof_atestado = atestado.profissional.nome if atestado.profissional else "N/A"
    empresa_cont_art = art.contratante.nome if art.contratante else "N/A"
    empresa_cont_atestado = atestado.contratante.nome if atestado.contratante else "N/A"
    empresa_exec_art = art.empresa_executora.nome if art.empresa_executora else "N/A"
    empresa_exec_atestado = atestado.empresa_executora.nome if atestado.empresa_executora else "N/A"

    bloco_input = f"""Documento ART:
- Nome do profissional: {nome_prof_art}
- Empresa contratante: {empresa_cont_art}
- Empresa executora: {empresa_exec_art}
- Endereço da obra: {_formatar_endereco(art.endereco_obra)}
- Escopo: {art.escopo or 'N/A'}
- Valor do contrato: {art.valor_contrato or 'N/A'}
- Número do contrato: {art.contrato_numero or 'N/A'}

Documento Atestado:
- Nome do profissional: {nome_prof_atestado}
- Empresa contratante: {empresa_cont_atestado}
- Empresa executora: {empresa_exec_atestado}
- Endereço da obra: {_formatar_endereco(atestado.endereco_obra)}
- Escopo: {atestado.escopo or 'N/A'}
- Valor do contrato: {atestado.valor_contrato or 'N/A'}
- Número do contrato: {atestado.contrato_numero or 'N/A'}

Campos a comparar: {', '.join(campos_esperados)}"""

    response = client.responses.parse(
        model=config.OPENAI_MODEL,
        instructions=PROMPT_CRUZAMENTO,
        input=[{"role": "user", "content": bloco_input}],
        text_format=ResultadoGPTCruzamento,
    )

    # Fallback: GPT não retornou resultado estruturado
    if response.output_parsed is None:
        return [
            ComparacaoCampo(
                campo=campo,
                status=StatusCampo.AUSENTE,
                detalhes="GPT nao retornou resultado",
            )
            for campo in campos_esperados
        ]

    # Converter ComparacaoGPT para ComparacaoCampo com valor_art e valor_atestado
    valores_art = {
        "nome_profissional": nome_prof_art,
        "empresa_contratante": empresa_cont_art,
        "empresa_executora": empresa_exec_art,
        "endereco_obra": _formatar_endereco(art.endereco_obra),
        "escopo": art.escopo,
        "valor_contrato": art.valor_contrato,
        "contrato_numero": art.contrato_numero,
    }
    valores_atestado = {
        "nome_profissional": nome_prof_atestado,
        "empresa_contratante": empresa_cont_atestado,
        "empresa_executora": empresa_exec_atestado,
        "endereco_obra": _formatar_endereco(atestado.endereco_obra),
        "escopo": atestado.escopo,
        "valor_contrato": atestado.valor_contrato,
        "contrato_numero": atestado.contrato_numero,
    }

    comparacoes = []
    for comp_gpt in response.output_parsed.comparacoes:
        comparacoes.append(
            ComparacaoCampo(
                campo=comp_gpt.campo,
                status=comp_gpt.status,
                valor_art=valores_art.get(comp_gpt.campo),
                valor_atestado=valores_atestado.get(comp_gpt.campo),
                confianca=comp_gpt.confianca,
                detalhes=comp_gpt.detalhes,
            )
        )

    # Garantir que todos os campos esperados estejam presentes (fallback por campo)
    campos_retornados = {c.campo for c in comparacoes}
    for campo in campos_esperados:
        if campo not in campos_retornados:
            comparacoes.append(
                ComparacaoCampo(
                    campo=campo,
                    status=StatusCampo.AUSENTE,
                    detalhes="Campo não retornado pelo GPT",
                )
            )

    return comparacoes


# ---------------------------------------------------------------------------
# API pública — cruzar_documentos (XREF-01 a XREF-07)
# ---------------------------------------------------------------------------

def cruzar_documentos(
    art: ResultadoAnalise,
    atestado: ResultadoAnalise,
) -> ResultadoCruzamento:
    """
    Cruza campos entre ART e Atestado, gerando comparação por campo.

    Executa três camadas:
    1. Match exato local: CPF, CNPJ, CREA/RNP, ART referenciada
    2. Intervalo de datas local: atestado DENTRO do período da ART
    3. Comparação fuzzy/semântica via GPT-4.1: nomes, empresas, endereços, escopo, valores

    Args:
        art: ResultadoAnalise extraído do documento ART.
        atestado: ResultadoAnalise extraído do documento Atestado.

    Returns:
        ResultadoCruzamento com comparacoes por campo e totais de MATCH/DIVERGENTE/AUSENTE.
    """
    comparacoes: list[ComparacaoCampo] = []

    # Camada 1: match exato de identificadores (Python puro)
    comparacoes.extend(_comparar_identificadores(art, atestado))

    # Camada 2: intervalo de datas (Python puro)
    comparacoes.append(_comparar_datas(art, atestado))

    # Camada 3: fuzzy/semântico (única chamada GPT em lote — D-01)
    comparacoes.extend(_comparar_via_gpt(art, atestado))

    return ResultadoCruzamento(
        comparacoes=comparacoes,
        total_match=sum(1 for c in comparacoes if c.status == StatusCampo.MATCH),
        total_divergente=sum(1 for c in comparacoes if c.status == StatusCampo.DIVERGENTE),
        total_ausente=sum(1 for c in comparacoes if c.status == StatusCampo.AUSENTE),
    )
