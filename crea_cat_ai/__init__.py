"""
CREA CAT AI - Pipeline de Análise de Certidão de Acervo Técnico

Módulos:
    ingestion   - Ingestão e classificação de documentos
    analysis    - Análise de documento e extração de entidades (GPT-4.1 Vision)
    metadata    - Extração de metadados PDF (pikepdf)
    signature   - Validação de assinatura digital ICP-Brasil (pyHanko)
    matching    - Cruzamento de campos entre documentos
    compliance  - Verificação de conformidade (Res. 1.137/2023, 1.160/2025)
    verdict     - Score de confiança e veredito
    report      - Geração de relatórios JSON e Markdown
"""

__version__ = "0.1.0"
