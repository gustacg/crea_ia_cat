"""
CREA CAT AI - Análise de Documento e Extração de Entidades

Responsável por:
- GPT-4.1 Vision: extrair entidades estruturadas (CPF, CNPJ, CREA, RNP, nomes, datas, escopo)
- Verificar ortografia do atestado via GPT-4.1 (somente Atestados)
- Detectar timbre/logo e assinatura visual via GPT-4.1 Vision
- Identificar cargo do assinante e habilitação como engenheiro
"""

import re
from typing import Optional

from pydantic import BaseModel, Field
from openai import OpenAI

import config
from crea_cat_ai.ingestion import (
    DocumentoCarregado,
    PaginaDocumento,
    TipoDocumento,
    PacoteDocumentos,
)


# ---------------------------------------------------------------------------
# Modelos Pydantic para structured output do GPT-4.1
# ---------------------------------------------------------------------------

class EntidadesProfissional(BaseModel):
    """Dados do profissional responsável técnico."""
    nome: str                           # Nome completo
    titulo: str                         # Título profissional (ex: "Engenheiro Eletricista")
    crea_rnp: Optional[str] = None      # CREA ou RNP — tratados como equivalentes
    cpf: Optional[str] = None           # CPF (pode estar mascarado com ***)
    registro: Optional[str] = None      # Registro completo (ex: "1120893194MA")


class EntidadesOrganizacao(BaseModel):
    """Dados de empresa ou órgão."""
    nome: str
    cnpj: Optional[str] = None
    cpf: Optional[str] = None           # Para contratantes pessoa física


class EntidadesEndereco(BaseModel):
    """Endereço da obra ou serviço."""
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    uf: Optional[str] = None
    cep: Optional[str] = None


class EntidadesData(BaseModel):
    """Datas relevantes do documento."""
    data_inicio: Optional[str] = None    # DD/MM/YYYY ou ISO
    data_termino: Optional[str] = None   # DD/MM/YYYY ou ISO
    data_emissao: Optional[str] = None


class AssinanteInfo(BaseModel):
    """Informações de um assinante do documento."""
    nome: str
    cargo: str                           # Cargo exato conforme documento
    crea_rnp: Optional[str] = None
    cpf: Optional[str] = None
    engenheiro_habilitado: bool          # True apenas se cargo é título de engenharia


class AnaliseVisual(BaseModel):
    """Resultado da análise visual de timbre e assinaturas."""
    tem_timbre: bool
    descricao_timbre: Optional[str] = None
    tem_assinatura_visual: bool
    assinantes: list[AssinanteInfo] = Field(default_factory=list)


class ErroOrtografico(BaseModel):
    """Erro ortográfico encontrado no documento."""
    trecho: str       # Trecho incorreto
    sugestao: str     # Sugestão de correção


class ResultadoAnalise(BaseModel):
    """
    Resultado completo da análise de um documento.
    Modelo central consumido pelas fases 5 (matching) e 6 (compliance).
    """
    # Entidades principais (ANAL-01)
    numero_documento: Optional[str] = None   # Número da ART ou contrato
    profissional: Optional[EntidadesProfissional] = None
    contratante: Optional[EntidadesOrganizacao] = None
    empresa_executora: Optional[EntidadesOrganizacao] = None
    endereco_obra: Optional[EntidadesEndereco] = None
    datas: EntidadesData = Field(default_factory=EntidadesData)
    escopo: Optional[str] = None             # Descrição do serviço/obra
    contrato_numero: Optional[str] = None
    art_referenciada: Optional[str] = None   # ART citada em Atestado/Declaração
    valor_contrato: Optional[str] = None

    # Análise visual (ANAL-04, ANAL-05, ANAL-06)
    visual: AnaliseVisual = Field(
        default_factory=lambda: AnaliseVisual(
            tem_timbre=False,
            tem_assinatura_visual=False,
        )
    )

    # Verificação ortográfica (ANAL-03) — apenas para Atestados
    erros_ortograficos: list[ErroOrtografico] = Field(default_factory=list)

    # Confiança e observações
    confianca: float = 1.0
    observacoes: Optional[str] = None


# ---------------------------------------------------------------------------
# Cliente OpenAI (módulo-level — reutilizado entre chamadas)
# ---------------------------------------------------------------------------

client = OpenAI(api_key=config.OPENAI_API_KEY)


# ---------------------------------------------------------------------------
# Prompt de análise
# ---------------------------------------------------------------------------

PROMPT_ANALISE_BASE = """Você é um especialista em análise de documentos técnicos do CREA (Conselho Regional de Engenharia e Agronomia do Brasil).

Analise o documento e extraia TODAS as informações estruturadas a seguir.

REGRA CRÍTICA — RNP e CREA são EQUIVALENTES:
- No formulário da ART, o número do registro profissional aparece com o rótulo "RNP:"
- Em atestados e declarações, o mesmo número aparece como "CREA:" ou "Registro CREA:"
- São o MESMO identificador. Sempre preencha o campo `crea_rnp` com este número.

EXTRAÇÃO DE ENTIDADES (campos obrigatórios se presentes no documento):
- profissional: nome completo, título profissional, número CREA/RNP, CPF (pode estar mascarado como ***), registro completo
- contratante: nome da empresa/órgão, CNPJ ou CPF
- empresa_executora: empresa que prestou o serviço (pode ser diferente da contratante)
- endereco_obra: endereço onde o serviço foi executado (logradouro, número, bairro, cidade, UF, CEP)
- datas: data de início, data de término/previsão, data de emissão do documento
- escopo: descrição do serviço/obra executado (texto livre, resumido em até 200 caracteres)
- contrato_numero: número do contrato
- art_referenciada: número da ART citada no documento (se for Atestado ou Declaração)
- valor_contrato: valor em R$

ANÁLISE VISUAL (examinar as imagens):
- tem_timbre: True se há logomarca, timbre ou papel timbrado identificável da contratante
- descricao_timbre: descrição breve do timbre/logo se presente
- tem_assinatura_visual: True se há assinatura manuscrita ou digital visível
- assinantes: lista de assinantes identificados. Para cada assinante:
  * nome: nome completo
  * cargo: cargo exato conforme aparece no documento (ex: "ADMINISTRADOR", "Engenheiro Civil de Saúde Indígena")
  * crea_rnp: número CREA ou RNP se presente abaixo da assinatura
  * cpf: CPF se presente
  * engenheiro_habilitado: true SOMENTE se o cargo for explicitamente um título de engenheiro, arquiteto, agrônomo ou similar. "ADMINISTRADOR", "Coordenador", "Diretor", etc. = false.

VERIFICAÇÃO ORTOGRÁFICA (apenas para Atestados):
- Identifique erros ortográficos em português — erros de digitação, acentuação incorreta, concordância verbal/nominal
- IGNORE: siglas técnicas (ART, CREA, RNP, ABNT, NBR), nomes próprios, endereços, termos técnicos de engenharia (ex: "fcK", "CA-50", "CHP"), nomes de equipamentos
- Para cada erro encontrado: informe o trecho incorreto e a sugestão correta
"""


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def normalizar_crea_rnp(valor: str | None) -> str | None:
    """
    Normaliza identificador CREA/RNP para comparação numérica.

    Remove todos os caracteres não-numéricos:
    - "1120893194MA" → "1120893194"
    - "CREA MA 1015902979" → "1015902979"
    - "4388D/GO" → "4388"
    - None → None

    Args:
        valor: String com o identificador CREA ou RNP a normalizar.

    Returns:
        String com apenas os dígitos, ou None se não houver dígitos.
    """
    if valor is None:
        return None
    digitos = re.sub(r"\D", "", valor)
    return digitos if digitos else None


def _selecionar_paginas_analise(doc: DocumentoCarregado) -> list[PaginaDocumento]:
    """
    Seleciona as páginas relevantes para extração de entidades.

    Estratégia:
    - Documentos com até 3 páginas: enviar todas
    - Documentos com mais de 3 páginas: página 1 + última página
      (página 1 tem cabeçalho/contratante; última página tem assinante)

    Esta estratégia evita enviar as 32 páginas do atestado saude indigena.pdf
    para o GPT, economizando tokens sem perder informações relevantes.

    Args:
        doc: Documento carregado com lista de páginas.

    Returns:
        Lista de PaginaDocumento selecionadas.
    """
    paginas = doc.paginas
    if len(paginas) <= 3:
        return list(paginas)
    return [paginas[0], paginas[-1]]


def _construir_input_analise(
    doc: DocumentoCarregado,
    paginas: list[PaginaDocumento],
) -> list[dict]:
    """
    Constrói o input da Responses API para análise de entidades.

    Combina texto nativo das páginas selecionadas (até 6000 chars) com
    imagens em alta resolução ("detail": "high") para análise visual.

    Args:
        doc: Documento carregado (usado para tipo e texto nativo).
        paginas: Páginas selecionadas para envio.

    Returns:
        Lista de mensagens no formato da Responses API.
    """
    # Texto nativo combinado das páginas selecionadas
    texto_combinado = "\n\n---\n\n".join(
        f"[Página {p.numero}]\n{p.texto_nativo}"
        for p in paginas
        if p.texto_nativo.strip()
    )

    content = []

    # Texto (prioridade: texto nativo quando disponível — mais barato que Vision)
    if texto_combinado.strip():
        content.append({
            "type": "input_text",
            "text": (
                f"Tipo de documento: {doc.tipo.value}\n\n"
                f"Texto extraído:\n{texto_combinado[:6000]}"
            ),
        })
    else:
        content.append({
            "type": "input_text",
            "text": f"Tipo de documento: {doc.tipo.value}",
        })

    # Imagens com alta resolução para análise visual (timbre, assinatura)
    for pagina in paginas:
        content.append({
            "type": "input_image",
            "image_url": f"data:image/png;base64,{pagina.imagem_b64}",
            "detail": "high",  # Obrigatório para ANAL-04 e ANAL-05
        })

    return [{"role": "user", "content": content}]


# ---------------------------------------------------------------------------
# Funções públicas
# ---------------------------------------------------------------------------

def analisar_documento(doc: DocumentoCarregado) -> ResultadoAnalise:
    """
    Extrai entidades estruturadas, analisa visualmente e verifica ortografia.

    Faz uma única chamada ao GPT-4.1 Vision com as páginas selecionadas
    para cobrir todos os 6 requisitos ANAL de uma vez.

    Args:
        doc: Documento já carregado com páginas (PaginaDocumento com imagens).

    Returns:
        ResultadoAnalise com entidades, análise visual e erros ortográficos.
    """
    paginas = _selecionar_paginas_analise(doc)
    input_content = _construir_input_analise(doc, paginas)

    response = client.responses.parse(
        model=config.OPENAI_MODEL,
        instructions=PROMPT_ANALISE_BASE,
        input=input_content,
        text_format=ResultadoAnalise,
    )

    # Trata recusa do modelo (output_parsed=None em caso de safety filter)
    if response.output_parsed is None:
        return ResultadoAnalise(
            confianca=0.0,
            observacoes="Modelo recusou análise do documento",
        )

    return response.output_parsed


def analisar_pacote(pacote: PacoteDocumentos) -> dict[str, ResultadoAnalise]:
    """
    Analisa todos os documentos do pacote (ART, Atestado e complementares).

    Args:
        pacote: Pacote com documentos já carregados e classificados.

    Returns:
        Dict com chave = tipo_documento.value (ex: "ART", "Atestado")
        e valor = ResultadoAnalise correspondente.
    """
    resultados: dict[str, ResultadoAnalise] = {}

    documentos = []
    if pacote.art:
        documentos.append(pacote.art)
    if pacote.atestado:
        documentos.append(pacote.atestado)
    documentos.extend(pacote.complementares)

    for doc in documentos:
        print(f"  Analisando: {doc.caminho.name} ({doc.tipo.value})")
        resultado = analisar_documento(doc)
        resultados[doc.tipo.value] = resultado

        nome_profissional = (
            resultado.profissional.nome
            if resultado.profissional
            else "N/A"
        )
        print(f"    Profissional: {nome_profissional}")

    return resultados
