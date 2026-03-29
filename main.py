"""CREA CAT AI - Pipeline de Análise de CAT"""

from pathlib import Path
import sys

from crea_cat_ai import ingestion
from crea_cat_ai import analysis
from crea_cat_ai import metadata, signature
from crea_cat_ai import matching
from crea_cat_ai import compliance
from crea_cat_ai import verdict
from crea_cat_ai import report
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

    # Phase 7: Veredito, Exigencias e Relatorio
    print()
    print("--- Fase 6: Veredito, Exigencias e Relatorio ---")

    # D-20: Se ART ou Atestado ausente, nao gerar veredito
    if not pacote.art or not pacote.atestado:
        print("  ERRO: ART ou Atestado ausente — veredito nao gerado")
        return {
            "status": "error",
            "erro": "ART ou Atestado ausente — veredito nao pode ser gerado",
            "art": pacote.art.caminho.name if pacote.art else None,
            "atestado": pacote.atestado.caminho.name if pacote.atestado else None,
        }

    veredito_resultado = verdict.calcular_veredito(
        resultado_cruzamento=resultado_cruzamento,
        resultado_compliance=resultado_compliance,
        resultados_metadata=resultados_metadata,
        resultados_assinatura=resultados_assinatura,
    )
    print(f"  Veredito: {veredito_resultado.tipo.value}")
    print(f"  Score: {veredito_resultado.score:.2f}")
    print(f"  Itens verificados: {len(veredito_resultado.itens_verificados)}")
    print(f"  Exigencias: {len(veredito_resultado.exigencias)}")
    if veredito_resultado.exigencias:
        for exig in veredito_resultado.exigencias:
            print(f"    - {exig}")

    # Extract profissional/contratante names from ART analysis for report header
    art_analise = resultados_analise.get(TipoDocumento.ART.value)
    profissional_nome = art_analise.profissional.nome if art_analise and art_analise.profissional else None
    contratante_nome = art_analise.contratante.nome if art_analise and art_analise.contratante else None

    # D-18: par_name from input directory name
    par_name = input_dir.name

    relatorio_paths = report.gerar_relatorios(
        veredito=veredito_resultado,
        pacote=pacote,
        resultado_cruzamento=resultado_cruzamento,
        resultado_compliance=resultado_compliance,
        resultados_metadata=resultados_metadata,
        resultados_assinatura=resultados_assinatura,
        profissional_nome=profissional_nome,
        contratante_nome=contratante_nome,
        par_name=par_name,
    )

    return {
        "status": "complete",
        "veredito": veredito_resultado.tipo.value,
        "score": veredito_resultado.score,
        "exigencias": veredito_resultado.exigencias,
        "relatorio_json": str(relatorio_paths.get("json_path", "")),
        "relatorio_md": str(relatorio_paths.get("md_path", "")),
        "par_name": par_name,
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single directory mode
        input_path = Path(sys.argv[1])
        main(input_path)
    else:
        # Process all par subdirectories in INPUT_DIR (per D-19)
        input_base = config.INPUT_DIR
        par_dirs = sorted([d for d in input_base.iterdir() if d.is_dir()])
        if par_dirs:
            for par_dir in par_dirs:
                print(f"\n{'=' * 60}")
                print(f"Processando par: {par_dir.name}")
                print(f"{'=' * 60}")
                try:
                    resultado = main(par_dir)
                    print(f"\nResultado: {resultado.get('veredito', resultado.get('status', 'N/A'))}")
                except Exception as e:
                    print(f"\nERRO ao processar {par_dir.name}: {e}")
        else:
            # Fallback: process INPUT_DIR directly (flat structure)
            main(input_base)
