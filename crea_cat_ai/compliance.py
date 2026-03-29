"""
CREA CAT AI - Verificação de Conformidade com Resoluções CONFEA

Responsável por:
- Conformidade com Anexo IV da Resolução 1.137/2023 (dados mínimos do atestado)
- Alterações da Resolução 1.160/2025
- Art. 59 §1º: Declaração obrigatória quando assinante não é engenheiro habilitado
- Verificação de Anuência em casos de subcontratação
- Cruzamento de documentos complementares (Declaração, Anuência)
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from openai import OpenAI

import config
from crea_cat_ai.ingestion import TipoDocumento, PacoteDocumentos, DocumentoCarregado
from crea_cat_ai.analysis import (
    ResultadoAnalise,
    AssinanteInfo,
    EntidadesProfissional,
    AnaliseVisual,
    EntidadesOrganizacao,
    EntidadesData,
    EntidadesEndereco,
    normalizar_crea_rnp,
)
from crea_cat_ai.matching import ResultadoCruzamento


# ---------------------------------------------------------------------------
# Cliente OpenAI (módulo-level — reutilizado entre chamadas)
# ---------------------------------------------------------------------------

client = OpenAI(api_key=config.OPENAI_API_KEY)


# ---------------------------------------------------------------------------
# Modelos Pydantic
# ---------------------------------------------------------------------------

class StatusCompliance(str, Enum):
    """Status de uma verificação de conformidade regulatória."""
    CONFORME = "CONFORME"
    NAO_CONFORME = "NAO_CONFORME"
    NAO_APLICAVEL = "NAO_APLICAVEL"


class VerificacaoItem(BaseModel):
    """Resultado de uma verificação regulatória específica."""
    requisito: str                        # ID do requisito (ex: "CDOC-01")
    descricao: str                        # Descrição legível da verificação
    status: StatusCompliance              # Resultado da verificação
    detalhes: Optional[str] = None        # Detalhes adicionais ou motivo da não conformidade


class ResultadoEspecialidadeGPT(BaseModel):
    """Resultado da verificação de compatibilidade de especialidade via GPT-4.1."""
    compativel: bool                      # Especialidade é compatível com o escopo
    confianca: float                      # Confiança da análise (0.0 a 1.0)
    justificativa: str                    # Justificativa da decisão


class ResultadoCompliance(BaseModel):
    """
    Resultado completo das verificações de conformidade regulatória.
    Consumido pela Phase 7 (veredito e scoring).
    """
    verificacoes: list[VerificacaoItem] = Field(default_factory=list)
    exigencias: list[str] = Field(default_factory=list)
    declaracao_necessaria: bool = False
    declaracao_encontrada: bool = False
    anuencia_necessaria: bool = False
    anuencia_encontrada: bool = False
    anexo_iv_completo: bool = False
    observacoes: Optional[str] = None


# ---------------------------------------------------------------------------
# Categorias obrigatórias do Anexo IV (Resolução 1.137/2023)
# ---------------------------------------------------------------------------

CATEGORIAS_ANEXO_IV = [
    {
        "id": "COMP-01.1",
        "descricao": "Identificação do contratante (razão social e CNPJ/CPF)",
        "check": lambda a: (
            a.contratante is not None
            and (a.contratante.cnpj is not None or a.contratante.cpf is not None)
        ),
        "exigencia": (
            "APRESENTAR IDENTIFICACAO COMPLETA DO CONTRATANTE (RAZAO SOCIAL E CNPJ/CPF) NO ATESTADO, "
            "CONFORME ITEM 1.2 DO ANEXO IV DA RESOLUCAO 1137 DO CONFEA"
        ),
    },
    {
        "id": "COMP-01.2",
        "descricao": "Identificação do responsável técnico (nome, título e RNP/CREA)",
        "check": lambda a: (
            a.profissional is not None
            and bool(a.profissional.nome)
            and (a.profissional.crea_rnp is not None or a.profissional.registro is not None)
        ),
        "exigencia": (
            "APRESENTAR IDENTIFICACAO COMPLETA DO RESPONSAVEL TECNICO (NOME, TITULO PROFISSIONAL E RNP/CREA) NO ATESTADO, "
            "CONFORME ITEM 1.4 DO ANEXO IV DA RESOLUCAO 1137 DO CONFEA"
        ),
    },
    {
        "id": "COMP-01.3",
        "descricao": "Descrição detalhada dos serviços realizados (escopo)",
        "check": lambda a: bool(a.escopo),
        "exigencia": (
            "APRESENTAR DESCRICAO DETALHADA DOS SERVICOS REALIZADOS NO ATESTADO, "
            "CONFORME ITEM 1.5 DO ANEXO IV DA RESOLUCAO 1137 DO CONFEA"
        ),
    },
    {
        "id": "COMP-01.4",
        "descricao": "Período de realização (data de início e conclusão)",
        "check": lambda a: (
            a.datas.data_inicio is not None or a.datas.data_termino is not None
        ),
        "exigencia": (
            "APRESENTAR PERIODO DE REALIZACAO (DATA DE INICIO E CONCLUSAO) NO ATESTADO, "
            "CONFORME ITEM 1.1 DO ANEXO IV DA RESOLUCAO 1137 DO CONFEA"
        ),
    },
    {
        "id": "COMP-01.5",
        "descricao": "Local de realização da obra/serviço",
        "check": lambda a: (
            a.endereco_obra is not None
            and (a.endereco_obra.cidade is not None or a.endereco_obra.uf is not None)
        ),
        "exigencia": (
            "APRESENTAR LOCAL DE REALIZACAO DA OBRA/SERVICO NO ATESTADO, "
            "CONFORME ITEM 1.1 DO ANEXO IV DA RESOLUCAO 1137 DO CONFEA"
        ),
    },
    {
        "id": "COMP-01.6",
        "descricao": "Assinatura do representante do contratante",
        "check": lambda a: a.visual.tem_assinatura_visual,
        "exigencia": (
            "APRESENTAR ASSINATURA DO REPRESENTANTE DO CONTRATANTE NO ATESTADO, "
            "CONFORME ITEM 1.6 DO ANEXO IV DA RESOLUCAO 1137 DO CONFEA"
        ),
    },
]


# ---------------------------------------------------------------------------
# Prompt GPT para verificação de especialidade
# ---------------------------------------------------------------------------

PROMPT_ESPECIALIDADE = (
    "Voce e um especialista em engenharia do CREA. Verifique se o titulo profissional do engenheiro "
    "e compativel com a area de servico descrita. Responda em JSON."
)


# ---------------------------------------------------------------------------
# Funções auxiliares internas
# ---------------------------------------------------------------------------

def _verificar_especialidade_gpt(
    titulo_declarante: str,
    escopo_art: str,
) -> ResultadoEspecialidadeGPT:
    """
    Verifica via GPT-4.1 se o título do engenheiro declarante é compatível
    com o escopo do serviço da ART (D-04, D-22).

    Uma única chamada à Responses API com structured output.

    Args:
        titulo_declarante: Título profissional do engenheiro (ex: "Engenheiro Eletricista")
        escopo_art: Descrição do escopo/serviço da ART

    Returns:
        ResultadoEspecialidadeGPT com resultado da verificação semântica
    """
    response = client.responses.parse(
        model=config.OPENAI_MODEL,
        instructions=PROMPT_ESPECIALIDADE,
        input=[{
            "role": "user",
            "content": (
                f"Titulo do engenheiro: {titulo_declarante}\n"
                f"Escopo do servico: {escopo_art}"
            ),
        }],
        text_format=ResultadoEspecialidadeGPT,
    )

    if response.output_parsed is None:
        return ResultadoEspecialidadeGPT(
            compativel=False,
            confianca=0.0,
            justificativa="GPT nao retornou resultado",
        )

    return response.output_parsed


def _verificacoes_1137(atestado: ResultadoAnalise) -> list[VerificacaoItem]:
    """
    Aplica verificações do Anexo IV da Resolução 1.137/2023 a um atestado.

    Verifica as 6 categorias obrigatórias de forma determinística (Python puro, D-13).
    Cada categoria é verificada contra os campos do ResultadoAnalise.

    Args:
        atestado: ResultadoAnalise do documento Atestado

    Returns:
        Lista de VerificacaoItem com o status de cada categoria
    """
    verificacoes: list[VerificacaoItem] = []
    for categoria in CATEGORIAS_ANEXO_IV:
        check_fn = categoria["check"]
        passou = check_fn(atestado)
        status = StatusCompliance.CONFORME if passou else StatusCompliance.NAO_CONFORME
        verificacoes.append(VerificacaoItem(
            requisito=categoria["id"],
            descricao=categoria["descricao"],
            status=status,
            detalhes=None if passou else f"Campo obrigatório ausente: {categoria['descricao']}",
        ))
    return verificacoes


def _verificacoes_1160_overrides(atestado: ResultadoAnalise) -> list[VerificacaoItem]:
    """
    Aplica verificações específicas da Resolução 1.160/2025 como overrides (D-16).

    PENDENTE: texto articulado da Res. 1.160/2025 nao disponivel no PDF fornecido.
    Retorna lista vazia ate que o texto seja fornecido.

    Estruturalmente separado das verificações base (D-16) para facilitar
    adição futura das regras da 1.160/2025.

    Args:
        atestado: ResultadoAnalise do documento Atestado

    Returns:
        Lista vazia — implementação completa aguarda texto da Res. 1.160/2025
    """
    return []


# ---------------------------------------------------------------------------
# Funções de verificação públicas
# ---------------------------------------------------------------------------

def verificar_declaracao(
    pacote: PacoteDocumentos,
    resultados_analise: dict[str, ResultadoAnalise],
    resultado_cruzamento: ResultadoCruzamento | None,
) -> tuple[list[VerificacaoItem], list[str], bool, bool]:
    """
    Verifica necessidade e conformidade da Declaração de Profissional Habilitado.

    Implementa Art. 59 §1º da Resolução 1.137/2023 (COMP-03):
    - D-01: Trigger — qualquer assinante com engenheiro_habilitado=False
    - D-02: Busca Declaração em pacote.complementares
    - D-05: Exigência quando necessária e ausente
    - D-06: Cruzamento de CREA e número de ART (CDOC-04)
    - D-04: Verificação de especialidade via GPT-4.1 (CDOC-02)

    Args:
        pacote: Pacote de documentos carregados
        resultados_analise: Dict tipo.value -> ResultadoAnalise (da Phase 3)
        resultado_cruzamento: Resultado do cruzamento da Phase 5 (opcional)

    Returns:
        Tupla: (verificacoes, exigencias, declaracao_necessaria, declaracao_encontrada)
    """
    verificacoes: list[VerificacaoItem] = []
    exigencias: list[str] = []

    # D-01: Verificar se Declaração é necessária via flag booleano
    atestado_analise = resultados_analise.get(TipoDocumento.ATESTADO.value)
    if atestado_analise is None:
        verificacoes.append(VerificacaoItem(
            requisito="CDOC-01",
            descricao="Verificação de Declaração de Profissional Habilitado (Art. 59 §1º)",
            status=StatusCompliance.NAO_APLICAVEL,
            detalhes="Atestado não encontrado no pacote — verificação não aplicável",
        ))
        return verificacoes, exigencias, False, False

    # D-01: Assinantes do atestado que não são engenheiros habilitados
    assinantes_nao_engenheiros = [
        a for a in atestado_analise.visual.assinantes
        if not a.engenheiro_habilitado
    ]
    declaracao_necessaria = len(assinantes_nao_engenheiros) > 0

    if not declaracao_necessaria:
        verificacoes.append(VerificacaoItem(
            requisito="CDOC-01",
            descricao="Verificação de Declaração de Profissional Habilitado (Art. 59 §1º)",
            status=StatusCompliance.NAO_APLICAVEL,
            detalhes="Todos os assinantes do atestado são engenheiros habilitados — Declaração não obrigatória",
        ))
        return verificacoes, exigencias, False, False

    # Declaração necessária — buscar em complementares (D-02)
    doc_declaracao = next(
        (d for d in pacote.complementares if d.tipo == TipoDocumento.DECLARACAO),
        None,
    )
    declaracao_encontrada = doc_declaracao is not None

    if not declaracao_encontrada:
        # D-05: Exigência no formato CREA quando Declaração ausente (COMP-03)
        exigencia = (
            "APRESENTAR DECLARACAO DE PROFISSIONAL HABILITADO NA AREA, "
            "DE ACORDO COM O PAR. 1, DO ART. 59 DA RESOLUCAO 1137 DO CONFEA"
        )
        exigencias.append(exigencia)
        verificacoes.append(VerificacaoItem(
            requisito="CDOC-01",
            descricao="Verificação de Declaração de Profissional Habilitado (Art. 59 §1º)",
            status=StatusCompliance.NAO_CONFORME,
            detalhes=(
                f"Assinante(s) não habilitado(s): "
                f"{', '.join(a.nome for a in assinantes_nao_engenheiros)}. "
                "Declaração obrigatória mas não encontrada."
            ),
        ))
        return verificacoes, exigencias, True, False

    # Declaração encontrada — marcar como CONFORME (CDOC-01)
    verificacoes.append(VerificacaoItem(
        requisito="CDOC-01",
        descricao="Verificação de Declaração de Profissional Habilitado (Art. 59 §1º)",
        status=StatusCompliance.CONFORME,
        detalhes="Declaração encontrada no pacote",
    ))

    # D-06: Cruzamento de entidades da Declaração (CDOC-04)
    declaracao_analise = resultados_analise.get(TipoDocumento.DECLARACAO.value)
    art_analise = resultados_analise.get(TipoDocumento.ART.value)

    if declaracao_analise is not None:
        # D-06: Cruzar CREA do declarante com CREA da ART
        if declaracao_analise.profissional and art_analise and art_analise.profissional:
            crea_declarante = normalizar_crea_rnp(declaracao_analise.profissional.crea_rnp)
            crea_art = normalizar_crea_rnp(art_analise.profissional.crea_rnp)

            if crea_declarante and crea_art:
                if crea_declarante == crea_art:
                    verificacoes.append(VerificacaoItem(
                        requisito="CDOC-04",
                        descricao="CREA do engenheiro declarante coincide com ART",
                        status=StatusCompliance.CONFORME,
                        detalhes=f"CREA normalizado: {crea_declarante}",
                    ))
                else:
                    verificacoes.append(VerificacaoItem(
                        requisito="CDOC-04",
                        descricao="CREA do engenheiro declarante coincide com ART",
                        status=StatusCompliance.NAO_CONFORME,
                        detalhes=(
                            f"CREA divergente — Declaração: {crea_declarante}, ART: {crea_art}"
                        ),
                    ))

        # D-06: Cruzar número de ART referenciada na Declaração
        if declaracao_analise.art_referenciada and art_analise:
            num_art_decl = normalizar_crea_rnp(declaracao_analise.art_referenciada)
            num_art = normalizar_crea_rnp(art_analise.numero_documento)
            if num_art_decl and num_art and num_art_decl == num_art:
                verificacoes.append(VerificacaoItem(
                    requisito="CDOC-04",
                    descricao="Número de ART na Declaração coincide com ART do pacote",
                    status=StatusCompliance.CONFORME,
                    detalhes=f"ART referenciada: {declaracao_analise.art_referenciada}",
                ))

        # D-04: Verificar compatibilidade de especialidade via GPT-4.1 (CDOC-02)
        if (declaracao_analise.profissional
                and art_analise
                and art_analise.escopo):
            titulo = declaracao_analise.profissional.titulo or ""
            escopo = art_analise.escopo or ""
            resultado_esp = _verificar_especialidade_gpt(titulo, escopo)
            status_esp = (
                StatusCompliance.CONFORME
                if resultado_esp.compativel
                else StatusCompliance.NAO_CONFORME
            )
            verificacoes.append(VerificacaoItem(
                requisito="CDOC-02",
                descricao="Especialidade do engenheiro declarante compatível com área do serviço",
                status=status_esp,
                detalhes=resultado_esp.justificativa,
            ))

            if not resultado_esp.compativel:
                exigencias.append(
                    "APRESENTAR DECLARACAO DE PROFISSIONAL HABILITADO NA AREA COMPATIVEL COM O SERVICO ATESTADO, "
                    "CONFORME ART. 59 §1 DA RESOLUCAO 1137 DO CONFEA"
                )

    return verificacoes, exigencias, True, True


def verificar_anuencia(
    pacote: PacoteDocumentos,
    resultados_analise: dict[str, ResultadoAnalise],
) -> tuple[list[VerificacaoItem], list[str], bool, bool]:
    """
    Verifica necessidade e presença de Anuência em casos de subcontratação.

    Implementa verificação de subcontratação (CDOC-03):
    - D-08: Subcontratação = empresa_executora diferentes na ART e Atestado
    - D-09: Exigência quando subcontratação sem Anuência
    - D-10: Anuência presente → CONFORME
    - D-11: Sem subcontratação → NAO_APLICAVEL

    Args:
        pacote: Pacote de documentos carregados
        resultados_analise: Dict tipo.value -> ResultadoAnalise

    Returns:
        Tupla: (verificacoes, exigencias, anuencia_necessaria, anuencia_encontrada)
    """
    verificacoes: list[VerificacaoItem] = []
    exigencias: list[str] = []

    art_analise = resultados_analise.get(TipoDocumento.ART.value)
    atestado_analise = resultados_analise.get(TipoDocumento.ATESTADO.value)

    # D-08: Ambos os documentos precisam estar presentes para comparar empresas
    if art_analise is None or atestado_analise is None:
        verificacoes.append(VerificacaoItem(
            requisito="CDOC-03",
            descricao="Verificação de Anuência para subcontratação",
            status=StatusCompliance.NAO_APLICAVEL,
            detalhes="ART ou Atestado ausente — verificação de Anuência não aplicável",
        ))
        return verificacoes, exigencias, False, False

    # D-08: Comparar empresa_executora normalizada (strip + upper)
    empresa_art = (
        art_analise.empresa_executora.nome.strip().upper()
        if art_analise.empresa_executora
        else None
    )
    empresa_atestado = (
        atestado_analise.empresa_executora.nome.strip().upper()
        if atestado_analise.empresa_executora
        else None
    )

    # Se uma ou ambas ausentes → subcontratação não detectada
    if empresa_art is None or empresa_atestado is None:
        verificacoes.append(VerificacaoItem(
            requisito="CDOC-03",
            descricao="Verificação de Anuência para subcontratação",
            status=StatusCompliance.NAO_APLICAVEL,
            detalhes=(
                "Empresa executora não identificada em um ou ambos documentos "
                "— subcontratação não detectada"
            ),
        ))
        return verificacoes, exigencias, False, False

    # Mesma empresa → sem subcontratação (D-11)
    if empresa_art == empresa_atestado:
        verificacoes.append(VerificacaoItem(
            requisito="CDOC-03",
            descricao="Verificação de Anuência para subcontratação",
            status=StatusCompliance.NAO_APLICAVEL,
            detalhes=f"Mesma empresa executora em ART e Atestado: {empresa_art}",
        ))
        return verificacoes, exigencias, False, False

    # D-08: Subcontratação detectada — empresas diferentes
    doc_anuencia = next(
        (d for d in pacote.complementares if d.tipo == TipoDocumento.ANUENCIA),
        None,
    )
    anuencia_encontrada = doc_anuencia is not None

    if not anuencia_encontrada:
        # D-09: Exigência quando subcontratação sem Anuência
        exigencia = (
            "APRESENTAR ANUENCIA DA CONTRATANTE PARA SUBCONTRATACAO, "
            "CONFORME RESOLUCAO 1137 DO CONFEA"
        )
        exigencias.append(exigencia)
        verificacoes.append(VerificacaoItem(
            requisito="CDOC-03",
            descricao="Verificação de Anuência para subcontratação",
            status=StatusCompliance.NAO_CONFORME,
            detalhes=(
                f"Subcontratação detectada: empresa ART '{empresa_art}' difere de "
                f"'{empresa_atestado}' no Atestado. Anuência obrigatória mas não encontrada."
            ),
        ))
    else:
        # D-10: Anuência presente → CONFORME (verificação estrutural)
        verificacoes.append(VerificacaoItem(
            requisito="CDOC-03",
            descricao="Verificação de Anuência para subcontratação",
            status=StatusCompliance.CONFORME,
            detalhes="Anuência encontrada no pacote para subcontratação",
        ))

    return verificacoes, exigencias, True, anuencia_encontrada


def verificar_anexo_iv(
    resultados_analise: dict[str, ResultadoAnalise],
) -> tuple[list[VerificacaoItem], list[str], bool]:
    """
    Verifica conformidade do Atestado com o Anexo IV da Resolução 1.137/2023.

    Aplica os 6 critérios obrigatórios de forma determinística (Python puro, D-13)
    e os overrides da Resolução 1.160/2025 (D-16, atualmente vazia).

    Args:
        resultados_analise: Dict tipo.value -> ResultadoAnalise

    Returns:
        Tupla: (verificacoes, exigencias, anexo_iv_completo)
    """
    verificacoes: list[VerificacaoItem] = []
    exigencias: list[str] = []

    atestado_analise = resultados_analise.get(TipoDocumento.ATESTADO.value)
    if atestado_analise is None:
        verificacoes.append(VerificacaoItem(
            requisito="COMP-01",
            descricao="Conformidade com Anexo IV da Resolução 1.137/2023",
            status=StatusCompliance.NAO_APLICAVEL,
            detalhes="Atestado não encontrado — verificação de Anexo IV não aplicável",
        ))
        return verificacoes, exigencias, False

    # D-13: Verificações determinísticas (Python puro)
    verificacoes_1137 = _verificacoes_1137(atestado_analise)
    verificacoes.extend(verificacoes_1137)

    # D-16: Overrides da Res. 1.160/2025 (estruturalmente separados)
    verificacoes_1160 = _verificacoes_1160_overrides(atestado_analise)
    verificacoes.extend(verificacoes_1160)

    # Gerar exigências para categorias não conformes (D-14)
    for i, verif in enumerate(verificacoes_1137):
        if verif.status == StatusCompliance.NAO_CONFORME:
            if i < len(CATEGORIAS_ANEXO_IV):
                exigencias.append(CATEGORIAS_ANEXO_IV[i]["exigencia"])

    # D-14: anexo_iv_completo = True somente se TODAS as 6 categorias passarem
    todas_conformes = all(
        v.status == StatusCompliance.CONFORME
        for v in verificacoes_1137
    )

    return verificacoes, exigencias, todas_conformes


def verificar_compliance(
    pacote: PacoteDocumentos,
    resultados_analise: dict[str, ResultadoAnalise],
    resultado_cruzamento: ResultadoCruzamento | None,
) -> ResultadoCompliance:
    """
    Orquestra todas as verificações de conformidade regulatória.

    Executa em sequência (D-18, D-19):
    1. Declaração (Art. 59 §1º) — trigger + verificação + cross-reference
    2. Anuência — detecção de subcontratação + verificação de presença
    3. Anexo IV — 6 categorias obrigatórias da Res. 1.137/2023 + overrides 1.160

    Args:
        pacote: Pacote de documentos carregados (ART + Atestado + complementares)
        resultados_analise: Dict tipo.value -> ResultadoAnalise (da Phase 3)
        resultado_cruzamento: Resultado do cruzamento ART x Atestado (da Phase 5)

    Returns:
        ResultadoCompliance com status de todas as verificações e lista de exigências
    """
    todas_verificacoes: list[VerificacaoItem] = []
    todas_exigencias: list[str] = []

    # 1. Verificação de Declaração (CDOC-01 a CDOC-04, COMP-03)
    verif_decl, exig_decl, decl_necessaria, decl_encontrada = verificar_declaracao(
        pacote, resultados_analise, resultado_cruzamento
    )
    todas_verificacoes.extend(verif_decl)
    todas_exigencias.extend(exig_decl)

    # 2. Verificação de Anuência (CDOC-03)
    verif_anuen, exig_anuen, anuen_necessaria, anuen_encontrada = verificar_anuencia(
        pacote, resultados_analise
    )
    todas_verificacoes.extend(verif_anuen)
    todas_exigencias.extend(exig_anuen)

    # 3. Verificação de Anexo IV (COMP-01, COMP-02)
    verif_iv, exig_iv, iv_completo = verificar_anexo_iv(resultados_analise)
    todas_verificacoes.extend(verif_iv)
    todas_exigencias.extend(exig_iv)

    return ResultadoCompliance(
        verificacoes=todas_verificacoes,
        exigencias=todas_exigencias,
        declaracao_necessaria=decl_necessaria,
        declaracao_encontrada=decl_encontrada,
        anuencia_necessaria=anuen_necessaria,
        anuencia_encontrada=anuen_encontrada,
        anexo_iv_completo=iv_completo,
    )
