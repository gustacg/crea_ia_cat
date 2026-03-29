"""CREA CAT AI - Pipeline de Análise de CAT"""

from pathlib import Path
import sys

from crea_cat_ai import ingestion
from crea_cat_ai import analysis
from crea_cat_ai import metadata, signature
from crea_cat_ai import matching
from crea_cat_ai import compliance
from crea_cat_ai.ingestion import TipoDocumento
import config


def main(input_dir: Path | None = None) -> dict:
    """
    Executa o pipeline completo de análise de CAT.

    Args:
        input_dir: Diretório com os documentos PDF. Default: config.INPUT_DIR

    Returns:
        dict com resultado do veredito e relatório
    """
    if input_dir is None:
        input_dir = config.INPUT_DIR

    if not input_dir.exists():
        print(f"ERRO: Diretório não encontrado: {input_dir}")
        sys.exit(1)

    print("=" * 60)
    print("CREA CAT AI - Análise de CAT")
    print("=" * 60)
    print(f"Diretório de entrada: {input_dir}")
    print()

    # Phase 2: Ingestão e Classificação
    print("--- Fase 1: Ingestão e Classificação de Documentos ---")
    pacote = ingestion.carregar_pacote(input_dir)

    print()
    print("--- Resumo do Pacote ---")
    print(f"  ART: {pacote.art.caminho.name if pacote.art else 'NÃO ENCONTRADA'}")
    print(f"  Atestado: {pacote.atestado.caminho.name if pacote.atestado else 'NÃO ENCONTRADO'}")
    print(f"  Complementares: {len(pacote.complementares)}")
    for doc in pacote.complementares:
        print(f"    - {doc.tipo.value}: {doc.caminho.name}")
    if pacote.nao_classificados:
        print(f"  Não classificados: {len(pacote.nao_classificados)}")
        for doc in pacote.nao_classificados:
            print(f"    - {doc.caminho.name}")

    # Phase 3: Análise e Extração de Entidades
    print()
    print("--- Fase 2: Analise e Extracao de Entidades ---")
    resultados_analise = analysis.analisar_pacote(pacote)

    print()
    print("--- Resumo da Analise ---")
    for tipo, resultado in resultados_analise.items():
        print(f"  [{tipo}]")
        if resultado.profissional:
            print(f"    Profissional: {resultado.profissional.nome}")
            print(f"    CREA/RNP: {resultado.profissional.crea_rnp or 'N/A'}")
        if resultado.contratante:
            print(f"    Contratante: {resultado.contratante.nome}")
            print(f"    CNPJ: {resultado.contratante.cnpj or 'N/A'}")
        if resultado.escopo:
            print(f"    Escopo: {resultado.escopo[:100]}")
        if resultado.visual.assinantes:
            for a in resultado.visual.assinantes:
                hab = "SIM" if a.engenheiro_habilitado else "NAO"
                print(f"    Assinante: {a.nome} ({a.cargo}) — Engenheiro: {hab}")
        if resultado.erros_ortograficos:
            print(f"    Erros ortograficos: {len(resultado.erros_ortograficos)}")
        print(f"    Timbre: {'SIM' if resultado.visual.tem_timbre else 'NAO'}")
        print(f"    Assinatura visual: {'SIM' if resultado.visual.tem_assinatura_visual else 'NAO'}")

    # Phase 4: Metadados e Assinatura Digital
    print()
    print("--- Fase 3: Metadados e Assinatura Digital ---")
    resultados_metadata = {}
    resultados_assinatura = {}
    todos_docs = []
    if pacote.art:
        todos_docs.append(pacote.art)
    if pacote.atestado:
        todos_docs.append(pacote.atestado)
    todos_docs.extend(pacote.complementares)

    for doc in todos_docs:
        tipo_key = doc.tipo.value
        print(f"  Processando metadados: {doc.caminho.name}")
        resultados_metadata[tipo_key] = metadata.processar_documento(doc.caminho)
        print(f"  Validando assinatura digital: {doc.caminho.name}")
        resultados_assinatura[tipo_key] = signature.validar_assinaturas(doc.caminho)

    print()
    print("--- Resumo Metadados e Assinaturas ---")
    for tipo_key in resultados_metadata:
        meta = resultados_metadata[tipo_key]
        assin = resultados_assinatura[tipo_key]
        print(f"  [{tipo_key}]")
        print(f"    Creator: {meta.creator or 'N/A'}")
        print(f"    Producer: {meta.producer or 'N/A'}")
        if meta.anomalias:
            for a in meta.anomalias:
                print(f"    ANOMALIA: {a}")
        print(f"    Assinatura digital: {'SIM' if assin.presente else 'NAO'}")
        if assin.presente:
            print(f"    Quantidade: {assin.quantidade}")
            for s in assin.signatarios:
                status = s.get("sumario", s.get("erro", "N/A"))
                print(f"      - {s['nome']}: {status}")

    # Phase 5: Cruzamento de Documentos
    print()
    print("--- Fase 4: Cruzamento de Documentos ---")
    resultado_cruzamento = None
    if pacote.art and pacote.atestado:
        art_analise = resultados_analise.get(TipoDocumento.ART.value)
        atestado_analise = resultados_analise.get(TipoDocumento.ATESTADO.value)
        if art_analise and atestado_analise:
            resultado_cruzamento = matching.cruzar_documentos(art_analise, atestado_analise)
            print(f"  Matches: {resultado_cruzamento.total_match}")
            print(f"  Divergencias: {resultado_cruzamento.total_divergente}")
            print(f"  Ausentes: {resultado_cruzamento.total_ausente}")
            for comp in resultado_cruzamento.comparacoes:
                if comp.status.value != "MATCH":
                    print(f"  [{comp.status.value}] {comp.campo}: {comp.detalhes}")
        else:
            print("  Dados de analise da ART ou Atestado nao encontrados")
    else:
        print("  ART ou Atestado ausente — cruzamento ignorado")

    # Phase 6: Documentos Complementares e Compliance
    print()
    print("--- Fase 5: Documentos Complementares e Compliance ---")
    resultado_compliance = compliance.verificar_compliance(
        pacote=pacote,
        resultados_analise=resultados_analise,
        resultado_cruzamento=resultado_cruzamento,
    )
    print(f"  Declaracao necessaria: {'SIM' if resultado_compliance.declaracao_necessaria else 'NAO'}")
    print(f"  Declaracao encontrada: {'SIM' if resultado_compliance.declaracao_encontrada else 'NAO'}")
    print(f"  Anuencia necessaria: {'SIM' if resultado_compliance.anuencia_necessaria else 'NAO'}")
    print(f"  Anuencia encontrada: {'SIM' if resultado_compliance.anuencia_encontrada else 'NAO'}")
    print(f"  Anexo IV completo: {'SIM' if resultado_compliance.anexo_iv_completo else 'NAO'}")
    if resultado_compliance.exigencias:
        print("  Exigencias:")
        for exig in resultado_compliance.exigencias:
            print(f"    - {exig}")
    for verif in resultado_compliance.verificacoes:
        if verif.status.value != "CONFORME":
            print(f"  [{verif.status.value}] {verif.requisito}: {verif.detalhes}")

    # Phase 7: placeholder
    print()
    print("--- Proximas fases (nao implementadas) ---")
    print("  Fase 6: Veredito, Exigencias e Relatorio")

    return {
        "status": "analysis_complete",
        "art": pacote.art.caminho.name if pacote.art else None,
        "atestado": pacote.atestado.caminho.name if pacote.atestado else None,
        "complementares": [d.caminho.name for d in pacote.complementares],
        "nao_classificados": [d.caminho.name for d in pacote.nao_classificados],
        "resultados_analise": {
            tipo: resultado.model_dump()
            for tipo, resultado in resultados_analise.items()
        },
        "resultados_metadata": {
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
        "resultados_assinatura": {
            tipo: {
                "presente": a.presente,
                "quantidade": a.quantidade,
                "signatarios": a.signatarios,
            }
            for tipo, a in resultados_assinatura.items()
        },
        "resultado_cruzamento": resultado_cruzamento.model_dump() if resultado_cruzamento else None,
        "resultado_compliance": resultado_compliance.model_dump(),
    }


if __name__ == "__main__":
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    main(input_path)
