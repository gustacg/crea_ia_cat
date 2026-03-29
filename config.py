"""
CREA CAT AI - Configuração do Pipeline
Edite os valores abaixo para ajustar o comportamento do pipeline.
NÃO é necessário alterar código em outros arquivos.
"""

import os
from pathlib import Path

# === OpenAI ===
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4.1"  # Modelo padrão para todas as chamadas

# === Paths ===
PROJECT_ROOT = Path(__file__).parent
INPUT_DIR = PROJECT_ROOT / "Documentos que crea recebe"
OUTPUT_DIR = PROJECT_ROOT / "output"
ICP_BRASIL_CA_BUNDLE = PROJECT_ROOT / "certs" / "icp-brasil-chain.pem"

# === Thresholds de Scoring ===
SCORE_ADERENTE = 0.80       # >= este valor = ADERENTE
SCORE_PENDENTE = 0.50       # >= este valor e < ADERENTE = PENDENTE
# abaixo de SCORE_PENDENTE = SUSPEITO

# === Pesos dos Campos (para cálculo do score) ===
PESO_CPF = 1.0              # Match exato de CPF
PESO_CNPJ = 1.0             # Match exato de CNPJ
PESO_CREA_RNP = 1.0         # Match exato de CREA/RNP (equivalentes)
PESO_NOME = 0.8             # Match fuzzy de nome
PESO_EMPRESA = 0.8          # Match fuzzy de empresa
PESO_ENDERECO = 0.6         # Match fuzzy de endereço
PESO_DATA = 0.9             # Data dentro do intervalo ART
PESO_ESCOPO = 0.7           # Comparação semântica do escopo
PESO_VALOR = 0.5            # Valor financeiro
PESO_CONTRATO = 0.5         # Número de contrato
PESO_ORTOGRAFIA = 0.3       # Erros ortográficos no atestado
PESO_ASSINATURA_VISUAL = 0.4  # Presença de assinatura visual
PESO_TIMBRE = 0.3           # Presença de timbre/logo

# === Limites de Processamento ===
MAX_PAGES_PER_PDF = 50      # Máximo de páginas por PDF
IMAGE_DPI = 200             # DPI para conversão de página em imagem
IMAGE_FORMAT = "png"        # Formato da imagem para Vision API

# === Metadados ===
SOFTWARE_SUSPEITO = [
    "Adobe Photoshop",
    "GIMP",
    "Paint.NET",
    "Inkscape",
]
