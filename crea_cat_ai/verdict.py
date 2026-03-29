"""
CREA CAT AI - Score de Confiança e Veredito

Responsável por:
- Calcular score de confiança (0.0 a 1.0) com base nos pesos de config.py
- Determinar veredito: ADERENTE / PENDENTE / SUSPEITO
- Gerar lista de itens verificados com status (OK/DIVERGENTE/AUSENTE/SUSPEITO)
- Formatar exigências no formato real do CREA (maiúsculas, base legal)

Algoritmo de scoring (D-01 a D-04):
- Score = média ponderada: soma(peso_i * score_i) / soma(peso_i)
- MATCH=1.0, DIVERGENTE=0.0, AUSENTE=0.5 (ausência não é fraude)
- Knock-out rules fazem cap/penalidade antes da classificação final
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

import config
from crea_cat_ai.matching import StatusCampo, ComparacaoCampo, ResultadoCruzamento
from crea_cat_ai.compliance import StatusCompliance, VerificacaoItem, ResultadoCompliance
from crea_cat_ai.metadata import MetadadosPDF
from crea_cat_ai.signature import ResultadoAssinatura


# ---------------------------------------------------------------------------
# Enums de status
# ---------------------------------------------------------------------------

class StatusItem(str, Enum):
    """Status final de um item verificado no parecer."""
    OK = "OK"
    DIVERGENTE = "DIVERGENTE"
    AUSENTE = "AUSENTE"
    SUSPEITO = "SUSPEITO"


class TipoVeredito(str, Enum):
    """Tipo de veredito emitido para o pedido CAT."""
    ADERENTE = "ADERENTE"
    PENDENTE = "PENDENTE"
    SUSPEITO = "SUSPEITO"


# ---------------------------------------------------------------------------
# Modelos Pydantic
# ---------------------------------------------------------------------------

class ItemVerificado(BaseModel):
    """Item individual verificado no processo de análise do pedido CAT."""
    campo: str                              # Nome do campo verificado
    status: StatusItem                      # Resultado da verificação
    valor_encontrado: Optional[str] = None  # Valor encontrado no documento
    valor_esperado: Optional[str] = None    # Valor esperado (da ART ou norma)
    detalhes: Optional[str] = None          # Explicação do resultado
    peso: float = 0.0                       # Peso no cálculo do score (0.0 = não pondera)


class Veredito(BaseModel):
    """Resultado final da análise do pedido CAT."""
    tipo: TipoVeredito                                    # ADERENTE / PENDENTE / SUSPEITO
    score: float                                          # Score de confiança (0.0 a 1.0)
    itens_verificados: list[ItemVerificado] = Field(default_factory=list)
    exigencias: list[str] = Field(default_factory=list)   # Exigências no formato CREA


# ---------------------------------------------------------------------------
# Constantes de scoring e knock-out (D-01, D-02)
# ---------------------------------------------------------------------------

# Mapeamento campo -> peso de config.py (D-01)
CAMPO_PESOS: dict[str, float] = {
    "cpf_profissional": config.PESO_CPF,
    "cnpj_contratante": config.PESO_CNPJ,
    "crea_rnp": config.PESO_CREA_RNP,
    "nome_profissional": config.PESO_NOME,
    "empresa_executora": config.PESO_EMPRESA,
    "empresa_contratante": config.PESO_NOME,   # Usa PESO_NOME como proxy para nome de organização
    "endereco_obra": config.PESO_ENDERECO,
    "intervalo_datas": config.PESO_DATA,
    "escopo": config.PESO_ESCOPO,
    "valor_contrato": config.PESO_VALOR,
    "contrato_numero": config.PESO_CONTRATO,
    "art_referenciada": config.PESO_CONTRATO,  # Referência de ART usa mesmo peso de contrato
}

# Score numérico por status (D-01)
STATUS_SCORE: dict[str, float] = {
    "MATCH": 1.0,
    "CONFORME": 1.0,
    "OK": 1.0,
    "DIVERGENTE": 0.0,
    "NAO_CONFORME": 0.0,
    "AUSENTE": 0.5,
    "NAO_APLICAVEL": 0.5,
    "SUSPEITO": 0.0,
}

# Knock-out caps (D-02)
KNOCKOUT_CAP_CRITICO = 0.49    # CPF / CNPJ / CREA divergente → força SUSPEITO
KNOCKOUT_CAP_EMPRESA = 0.79    # Empresa executora divergente → nunca ADERENTE

# Penalidades aditivas (D-02)
PENALIDADE_METADATA_SUSPEITO = 0.15
PENALIDADE_DECLARACAO_AUSENTE = 0.20

# Campos críticos que ativam o cap de 0.49
_CAMPOS_CRITICOS = {"cpf_profissional", "cnpj_contratante", "crea_rnp"}

# Mapeamento StatusCampo -> StatusItem
_CAMPO_TO_ITEM: dict[str, StatusItem] = {
    "MATCH": StatusItem.OK,
    "DIVERGENTE": StatusItem.DIVERGENTE,
    "AUSENTE": StatusItem.AUSENTE,
}

# Mapeamento StatusCompliance -> StatusItem
_COMPLIANCE_TO_ITEM: dict[str, StatusItem] = {
    "CONFORME": StatusItem.OK,
    "NAO_CONFORME": StatusItem.DIVERGENTE,
    "NAO_APLICAVEL": StatusItem.AUSENTE,
}


# ---------------------------------------------------------------------------
# Funções privadas de mapeamento
# ---------------------------------------------------------------------------

def _mapear_status_campo(status: StatusCampo) -> StatusItem:
    """Mapeia StatusCampo (cruzamento) para StatusItem (veredito)."""
    return _CAMPO_TO_ITEM.get(status.value, StatusItem.AUSENTE)


def _mapear_status_compliance(status: StatusCompliance) -> StatusItem:
    """Mapeia StatusCompliance para StatusItem (veredito)."""
    return _COMPLIANCE_TO_ITEM.get(status.value, StatusItem.AUSENTE)


# ---------------------------------------------------------------------------
# Consolidação de itens de todas as fontes (D-06, D-07)
# ---------------------------------------------------------------------------

def _consolidar_itens(
    resultado_cruzamento: ResultadoCruzamento | None,
    resultado_compliance: ResultadoCompliance,
    resultados_metadata: dict[str, MetadadosPDF],
    resultados_assinatura: dict[str, ResultadoAssinatura],
) -> list[ItemVerificado]:
    """
    Consolida todos os itens verificados em uma lista unificada ItemVerificado.

    Fontes (D-06):
    1. Cruzamento (Phase 5): ComparacaoCampo -> peso via CAMPO_PESOS
    2. Compliance (Phase 6): VerificacaoItem -> peso=0.0 (não pondera no score numérico)
    3. Metadados (Phase 4): anomalias -> status=SUSPEITO, peso=0.0
    4. Assinatura digital (Phase 4): signatários -> status baseado no resultado

    Args:
        resultado_cruzamento: Resultado do cruzamento ART x Atestado (pode ser None)
        resultado_compliance: Resultado das verificações de conformidade regulatória
        resultados_metadata: Dict nome_doc -> MetadadosPDF
        resultados_assinatura: Dict nome_doc -> ResultadoAssinatura

    Returns:
        Lista unificada de ItemVerificado de todas as fontes
    """
    itens: list[ItemVerificado] = []

    # 1. Itens do cruzamento (ComparacaoCampo -> ItemVerificado com peso)
    if resultado_cruzamento is not None:
        for comp in resultado_cruzamento.comparacoes:
            peso = CAMPO_PESOS.get(comp.campo, 0.0)
            status_item = _mapear_status_campo(comp.status)
            itens.append(ItemVerificado(
                campo=comp.campo,
                status=status_item,
                valor_encontrado=comp.valor_atestado,
                valor_esperado=comp.valor_art,
                detalhes=comp.detalhes,
                peso=peso,
            ))

    # 2. Itens do compliance (VerificacaoItem -> ItemVerificado sem peso no score)
    for verif in resultado_compliance.verificacoes:
        status_item = _mapear_status_compliance(verif.status)
        itens.append(ItemVerificado(
            campo=verif.requisito,
            status=status_item,
            detalhes=verif.detalhes or verif.descricao,
            peso=0.0,   # Compliance não pondera na média — já gera exigências próprias
        ))

    # 3. Itens de metadados (anomalias -> SUSPEITO)
    for nome_doc, meta in resultados_metadata.items():
        if meta.anomalias:
            for anomalia in meta.anomalias:
                itens.append(ItemVerificado(
                    campo=f"metadados_{nome_doc}",
                    status=StatusItem.SUSPEITO,
                    detalhes=anomalia,
                    peso=0.0,  # Penalidade aplicada pelo knock-out, não pela média
                ))
        else:
            itens.append(ItemVerificado(
                campo=f"metadados_{nome_doc}",
                status=StatusItem.OK,
                detalhes="Metadados PDF sem anomalias detectadas",
                peso=0.0,
            ))

    # 4. Itens de assinatura digital
    for nome_doc, assinatura in resultados_assinatura.items():
        if not assinatura.presente:
            itens.append(ItemVerificado(
                campo=f"assinatura_digital_{nome_doc}",
                status=StatusItem.AUSENTE,
                detalhes="Assinatura digital ICP-Brasil não encontrada (estado válido — SIGN-03)",
                peso=0.0,
            ))
        else:
            for sig in assinatura.signatarios:
                # Determinar status baseado no resultado de validação
                sumario = sig.get("sumario", "")
                erro = sig.get("erro")
                valido = sig.get("valido", False)
                integro = sig.get("integro", False)

                if erro:
                    status_item = StatusItem.SUSPEITO
                    detalhes = f"Erro na validação: {erro}"
                elif valido and integro:
                    status_item = StatusItem.OK
                    detalhes = f"Assinatura válida: {sig.get('nome', 'Desconhecido')} — {sumario}"
                else:
                    status_item = StatusItem.DIVERGENTE
                    detalhes = f"Assinatura inválida: {sig.get('nome', 'Desconhecido')} — {sumario}"

                itens.append(ItemVerificado(
                    campo=f"assinatura_digital_{nome_doc}",
                    status=status_item,
                    valor_encontrado=sig.get("nome"),
                    detalhes=detalhes,
                    peso=0.0,
                ))

    return itens


# ---------------------------------------------------------------------------
# Cálculo do score (D-01)
# ---------------------------------------------------------------------------

def _calcular_score(itens: list[ItemVerificado]) -> float:
    """
    Calcula o score de confiança como média ponderada dos itens com peso > 0.

    Fórmula (D-01):
        score = soma(STATUS_SCORE[item.status] * item.peso) / soma(item.peso)

    Itens com peso=0.0 (compliance, metadados, assinatura) não entram na média.
    Retorna 1.0 se não há itens com peso > 0 (sem cruzamento disponível).

    Args:
        itens: Lista de ItemVerificado

    Returns:
        Score de confiança entre 0.0 e 1.0
    """
    soma_ponderada = 0.0
    soma_pesos = 0.0

    for item in itens:
        if item.peso > 0.0:
            score_item = STATUS_SCORE.get(item.status.value, 0.5)
            soma_ponderada += score_item * item.peso
            soma_pesos += item.peso

    if soma_pesos == 0.0:
        return 1.0  # Sem campos ponderados — sem penalidade por ausência de cruzamento

    return soma_ponderada / soma_pesos


# ---------------------------------------------------------------------------
# Aplicação de knock-outs e penalidades (D-02)
# ---------------------------------------------------------------------------

def _aplicar_knockouts(
    score: float,
    itens: list[ItemVerificado],
    resultado_compliance: ResultadoCompliance,
    resultados_metadata: dict[str, MetadadosPDF],
) -> float:
    """
    Aplica regras de knock-out e penalidades ao score calculado (D-02).

    Regras em ordem de aplicação:
    1. CPF / CNPJ / CREA divergente → cap em 0.49 (força SUSPEITO)
    2. Empresa executora divergente → cap em 0.79 (nunca ADERENTE)
    3. Metadados com software suspeito → penalidade -0.15
    4. Declaração obrigatória ausente → penalidade -0.20
    5. Clamp a 0.0 mínimo

    Args:
        score: Score base calculado pela média ponderada
        itens: Lista de ItemVerificado consolidados
        resultado_compliance: Resultado do compliance (para declaração ausente)
        resultados_metadata: Dict nome_doc -> MetadadosPDF

    Returns:
        Score após aplicação de knock-outs e penalidades
    """
    # 1. Campos críticos (CPF/CNPJ/CREA) divergentes → cap 0.49
    for item in itens:
        if item.campo in _CAMPOS_CRITICOS and item.status == StatusItem.DIVERGENTE:
            score = min(score, KNOCKOUT_CAP_CRITICO)

    # 2. Empresa executora divergente → cap 0.79
    for item in itens:
        if item.campo == "empresa_executora" and item.status == StatusItem.DIVERGENTE:
            score = min(score, KNOCKOUT_CAP_EMPRESA)

    # 3. Metadados suspeitos → penalidade -0.15 por documento com anomalia
    for meta in resultados_metadata.values():
        if meta.anomalias:
            score -= PENALIDADE_METADATA_SUSPEITO
            break  # Uma penalidade por análise, independente de quantos docs têm anomalia

    # 4. Declaração obrigatória ausente → penalidade -0.20
    if resultado_compliance.declaracao_necessaria and not resultado_compliance.declaracao_encontrada:
        score -= PENALIDADE_DECLARACAO_AUSENTE

    # 5. Clamp: score nunca abaixo de 0.0
    return max(score, 0.0)


# ---------------------------------------------------------------------------
# Determinação do tipo de veredito (D-03)
# ---------------------------------------------------------------------------

def _determinar_tipo(score: float) -> TipoVeredito:
    """
    Determina o TipoVeredito com base no score e nos thresholds de config.py (D-03).

    Thresholds (config.py):
        ADERENTE:  score >= SCORE_ADERENTE (0.80)
        PENDENTE:  score >= SCORE_PENDENTE (0.50) e < SCORE_ADERENTE
        SUSPEITO:  score < SCORE_PENDENTE (0.50)

    Args:
        score: Score de confiança após knock-outs

    Returns:
        TipoVeredito correspondente ao score
    """
    if score >= config.SCORE_ADERENTE:
        return TipoVeredito.ADERENTE
    if score >= config.SCORE_PENDENTE:
        return TipoVeredito.PENDENTE
    return TipoVeredito.SUSPEITO


# ---------------------------------------------------------------------------
# Geração de exigências de cruzamento (D-08, D-10, D-11)
# ---------------------------------------------------------------------------

def _gerar_exigencias_cruzamento(
    resultado_cruzamento: ResultadoCruzamento | None,
) -> list[str]:
    """
    Gera exigências no formato CREA para divergências detectadas no cruzamento (D-10).

    Exigências de cruzamento NÃO incluem base legal (D-11) — apenas campos divergentes.
    Formato: frase declarativa em MAIÚSCULAS (D-08).

    Args:
        resultado_cruzamento: Resultado do cruzamento ART x Atestado (pode ser None)

    Returns:
        Lista de exigências em MAIÚSCULAS para cada divergência
    """
    if resultado_cruzamento is None:
        return []

    exigencias: list[str] = []

    for comp in resultado_cruzamento.comparacoes:
        if comp.status != StatusCampo.DIVERGENTE:
            continue

        campo = comp.campo
        val_art = comp.valor_art or "NAO INFORMADO"
        val_atestado = comp.valor_atestado or "NAO INFORMADO"

        if campo == "cpf_profissional":
            exigencias.append(
                f"VERIFICAR DIVERGENCIA DE CPF ENTRE ART E ATESTADO "
                f"— CPF DA ART: {val_art}, CPF DO ATESTADO: {val_atestado}"
            )
        elif campo == "cnpj_contratante":
            exigencias.append(
                f"VERIFICAR DIVERGENCIA DE CNPJ ENTRE ART E ATESTADO "
                f"— CNPJ DA ART: {val_art}, CNPJ DO ATESTADO: {val_atestado}"
            )
        elif campo == "crea_rnp":
            exigencias.append(
                f"VERIFICAR DIVERGENCIA DE CREA/RNP ENTRE ART E ATESTADO "
                f"— CREA/RNP DA ART: {val_art}, CREA/RNP DO ATESTADO: {val_atestado}"
            )
        elif campo == "empresa_executora":
            exigencias.append(
                f"VERIFICAR DIVERGENCIA DE EMPRESA EXECUTORA ENTRE ART E ATESTADO "
                f"— ART: {val_art}, ATESTADO: {val_atestado}"
            )
        elif campo == "escopo":
            exigencias.append(
                "VERIFICAR COMPATIBILIDADE DO OBJETO/ESCOPO DO SERVICO ENTRE ART E ATESTADO"
            )
        elif campo == "intervalo_datas":
            exigencias.append(
                "VERIFICAR PERIODO DE EXECUCAO "
                "— DATAS DO ATESTADO NAO ESTAO DENTRO DO INTERVALO DA ART"
            )
        else:
            # Outros campos divergentes: exigência genérica (D-11)
            exigencias.append(
                f"VERIFICAR DIVERGENCIA DE {campo.upper()} ENTRE ART E ATESTADO"
            )

    return exigencias


# ---------------------------------------------------------------------------
# API pública: calcular_veredito (D-01 a D-11, D-20)
# ---------------------------------------------------------------------------

def calcular_veredito(
    resultado_cruzamento: ResultadoCruzamento | None,
    resultado_compliance: ResultadoCompliance,
    resultados_metadata: dict[str, MetadadosPDF],
    resultados_assinatura: dict[str, ResultadoAssinatura],
) -> Veredito:
    """
    Calcula o veredito final do pedido CAT (ADERENTE / PENDENTE / SUSPEITO).

    Fluxo (D-01 a D-11):
    1. Consolida itens verificados de 4 fontes (cruzamento, compliance, metadados, assinatura)
    2. Calcula score como média ponderada (apenas campos com peso > 0)
    3. Aplica knock-out rules e penalidades
    4. Determina TipoVeredito pelos thresholds de config.py
    5. Gera exigências: compliance.exigencias + exigências de cruzamento
    6. Retorna Veredito consolidado

    Nota (D-20): resultado_cruzamento=None é válido — ocorre quando ART ou Atestado
    está ausente. Nesse caso, o veredito é calculado apenas com compliance/metadados/assinatura.

    Args:
        resultado_cruzamento: Resultado do cruzamento ART x Atestado (pode ser None)
        resultado_compliance: Resultado das verificações de conformidade regulatória
        resultados_metadata: Dict nome_doc -> MetadadosPDF (de processar_documento())
        resultados_assinatura: Dict nome_doc -> ResultadoAssinatura (de validar_assinaturas())

    Returns:
        Veredito com tipo, score, itens_verificados e exigencias no formato CREA
    """
    # 1. Consolidar itens de todas as fontes
    itens = _consolidar_itens(
        resultado_cruzamento,
        resultado_compliance,
        resultados_metadata,
        resultados_assinatura,
    )

    # 2. Calcular score base (média ponderada dos campos com peso > 0)
    score = _calcular_score(itens)

    # 3. Aplicar knock-outs e penalidades (D-02)
    score = _aplicar_knockouts(score, itens, resultado_compliance, resultados_metadata)

    # 4. Determinar tipo de veredito pelos thresholds (D-03)
    tipo = _determinar_tipo(score)

    # 5. Gerar exigências (D-09):
    #    - Compliance.exigencias: já formatadas corretamente pela Phase 6 (reutilização direta)
    #    - Cruzamento: novas exigências para divergências de campos (D-10)
    exigencias_compliance = list(resultado_compliance.exigencias)
    exigencias_cruzamento = _gerar_exigencias_cruzamento(resultado_cruzamento)

    # Combinar sem duplicação (D-09)
    todas_exigencias: list[str] = []
    seen: set[str] = set()
    for exig in exigencias_compliance + exigencias_cruzamento:
        if exig not in seen:
            todas_exigencias.append(exig)
            seen.add(exig)

    return Veredito(
        tipo=tipo,
        score=round(score, 4),
        itens_verificados=itens,
        exigencias=todas_exigencias,
    )
