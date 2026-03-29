---
phase: 01-environment-setup
plan: 01
subsystem: project-foundation
tags: [setup, dependencies, config, project-structure]
dependency_graph:
  requires: []
  provides: [requirements.txt, config.py, setup_check.py, crea_cat_ai-package]
  affects: [all-subsequent-phases]
tech_stack:
  added: [openai-2.30.0, pymupdf-1.27.2.2, pikepdf-10.5.1, pyhanko-0.34.1, Pillow-11.3.0]
  patterns: [flat-package-structure, pathlib-paths, env-var-api-key, placeholder-modules]
key_files:
  created:
    - requirements.txt
    - config.py
    - main.py
    - setup_check.py
    - crea_cat_ai/__init__.py
    - crea_cat_ai/ingestion.py
    - crea_cat_ai/analysis.py
    - crea_cat_ai/metadata.py
    - crea_cat_ai/signature.py
    - crea_cat_ai/matching.py
    - crea_cat_ai/compliance.py
    - crea_cat_ai/verdict.py
    - crea_cat_ai/report.py
    - tests/__init__.py
    - .gitignore
  modified: []
decisions:
  - "Stack simplificada: apenas 5 deps (openai, pymupdf, pikepdf, pyhanko, Pillow) — GPT-4.1 Vision faz o resto"
  - "Modelo padrão gpt-4.1 configurável em config.py via constante OPENAI_MODEL"
  - "Thresholds de scoring e pesos de campos todos em config.py — sem tocar no pipeline"
  - "Pacote crea_cat_ai/ flat (módulos diretos, não subpacotes) por simplicidade"
metrics:
  duration_seconds: 266
  completed_date: "2026-03-28"
  tasks_completed: 2
  files_created: 15
---

# Phase 01 Plan 01: Environment Setup Summary

## One-liner

Estrutura Python completa com 5 dependências pinadas (openai, pymupdf, pikepdf, pyhanko, Pillow), config.py com thresholds editáveis e setup_check.py de validação automatizada em pt-BR.

## What Was Built

### Task 1: Estrutura do projeto, requirements.txt e config.py

Criada a estrutura completa do projeto CREA CAT AI a partir do zero (após cleanup da stack overengineered anterior):

- **requirements.txt**: 5 dependências core pinadas por versão mínima
- **config.py**: Thresholds de scoring (SCORE_ADERENTE=0.80, SCORE_PENDENTE=0.50), pesos de campos (PESO_CPF, PESO_NOME, PESO_ESCOPO, etc.), modelo OpenAI (gpt-4.1), paths via pathlib, lista SOFTWARE_SUSPEITO para detecção de fraude
- **main.py**: Entry point placeholder — importa todos os módulos, aceita diretório de entrada via argumento, mensagens em pt-BR
- **crea_cat_ai/__init__.py**: Pacote principal com `__version__ = "0.1.0"`
- **8 módulos placeholder**: ingestion.py, analysis.py, metadata.py, signature.py, matching.py, compliance.py, verdict.py, report.py — cada um com docstring descrevendo responsabilidade e fase de implementação
- **tests/__init__.py**: Diretório de testes vazio
- **.gitignore**: Python padrão + project-specific (output/, certs/, .venv/, .env)

Commit: `bc76f32`

### Task 2: setup_check.py e instalação de dependências

- **pip install -r requirements.txt**: Instalação limpa no Python 3.13 Windows 11. Todas as 5 deps instaladas: openai 2.30.0, pymupdf 1.27.2.2, pikepdf 10.5.1, pyhanko 0.34.1, Pillow 11.3.0
- **setup_check.py**: Script de validação com 5 funções check_*:
  - `check_python_version()` — verifica Python >= 3.10
  - `check_import()` — importa e reporta versão de cada dep
  - `check_openai_key()` — verifica variável OPENAI_API_KEY (também lê .env se existir), suporta project keys (não sk-)
  - `check_openai_connection()` — teste real de conexão com a API (pulo gracioso se sem chave)
  - `check_project_structure()` — verifica existência de todos os 12 arquivos críticos
- Output 100% em pt-BR com status [OK]/[ERRO]/[AVISO]/[PULO] por verificação

Commit: `6e3834b`

## Deviations from Plan

### Auto-fixed Issues

Nenhum bug encontrado.

### Cleanup Realizado (não era desvio — era parte da transição de stack)

A execução encontrou vestígios da stack antiga (subpacotes em crea_cat_ai/compliance/, crea_cat_ai/metadata/, etc., pytest.ini, tests/test_config.py, tests/test_setup.py) que foram deletados como parte do commit da Task 1. Isso fazia parte do pivot de stack já documentado em STATE.md.

## Verification Results

Todos os critérios de sucesso atendidos:

| Critério | Status |
|----------|--------|
| `pip install -r requirements.txt` sem erros | OK |
| `python setup_check.py` sem exceções | OK (exit 1 esperado sem API key) |
| `python -c "import crea_cat_ai"` | OK (versão 0.1.0) |
| `python -c "import config; print(config.OPENAI_MODEL)"` | OK (gpt-4.1) |
| 8 módulos em crea_cat_ai/ | OK |
| config.py com thresholds editáveis | OK |
| SETUP-01: setup_check.py valida deps e API key | OK |
| SETUP-02: pip install limpo no Python 3.13 | OK |
| SETUP-03: thresholds configuráveis via config.py | OK |

## Known Stubs

Os módulos `ingestion.py`, `analysis.py`, `metadata.py`, `signature.py`, `matching.py`, `compliance.py`, `verdict.py`, `report.py` contêm apenas docstrings e `# TODO: Implementar na Phase X`. Esses são placeholders INTENCIONAIS — cada fase subsequente implementa o módulo correspondente. O objetivo desta fase era apenas criar a estrutura importável.

`main.py` retorna `{"status": "not_implemented"}` — igualmente intencional como placeholder para a Phase 7 que implementa o pipeline completo.

## Self-Check: PASSED

Arquivos verificados:
- requirements.txt: FOUND
- config.py: FOUND
- setup_check.py: FOUND
- main.py: FOUND
- crea_cat_ai/__init__.py: FOUND
- crea_cat_ai/ingestion.py: FOUND
- crea_cat_ai/analysis.py: FOUND
- crea_cat_ai/metadata.py: FOUND
- crea_cat_ai/signature.py: FOUND
- crea_cat_ai/matching.py: FOUND
- crea_cat_ai/compliance.py: FOUND
- crea_cat_ai/verdict.py: FOUND
- crea_cat_ai/report.py: FOUND

Commits verificados:
- bc76f32: FOUND (Task 1)
- 6e3834b: FOUND (Task 2)
