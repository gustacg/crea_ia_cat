"""
CREA CAT AI - Verificação de Setup

Verifica se todas as dependências estão instaladas e configuradas.
Output em português (pt-BR).
Uso: python setup_check.py
"""

import sys
import importlib


def check_python_version() -> bool:
    """Verifica versão do Python >= 3.10."""
    v = sys.version_info
    ok = v.major == 3 and v.minor >= 10
    status = "OK" if ok else "ERRO"
    print(f"  [{status}] Python {v.major}.{v.minor}.{v.micro}", end="")
    if not ok:
        print(" (requer >= 3.10)")
    else:
        print()
    return ok


def check_import(package: str, import_name: str | None = None) -> bool:
    """Tenta importar um pacote e reporta sucesso/falha."""
    name = import_name or package
    try:
        mod = importlib.import_module(name)
        version = getattr(mod, "__version__", getattr(mod, "VERSION", "?"))
        print(f"  [OK] {package} (versão: {version})")
        return True
    except ImportError as e:
        print(f"  [ERRO] {package} - não encontrado: {e}")
        return False


def check_openai_key() -> bool:
    """Verifica se a chave da API OpenAI está configurada."""
    import os
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        # Tenta carregar de .env se existir
        from pathlib import Path
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not key:
        print("  [ERRO] OPENAI_API_KEY não configurada")
        print("         Configure via variável de ambiente ou arquivo .env")
        return False

    # Verifica formato básico (sk-...)
    if not key.startswith("sk-"):
        print(f"  [AVISO] OPENAI_API_KEY não começa com 'sk-' (formato incomum)")
        return True  # Não bloqueia — pode ser project key

    masked = key[:7] + "..." + key[-4:]
    print(f"  [OK] OPENAI_API_KEY configurada ({masked})")
    return True


def check_openai_connection() -> bool:
    """Testa conexão real com a API OpenAI (chamada mínima)."""
    try:
        import os
        from openai import OpenAI

        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            from pathlib import Path
            env_file = Path(__file__).parent / ".env"
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.startswith("OPENAI_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break

        if not key:
            print("  [PULO] Teste de conexão OpenAI - sem chave configurada")
            return False

        client = OpenAI(api_key=key)
        models = client.models.list()
        print(f"  [OK] Conexão com OpenAI API funcionando")
        return True
    except Exception as e:
        print(f"  [ERRO] Conexão com OpenAI API falhou: {e}")
        return False


def check_project_structure() -> bool:
    """Verifica se a estrutura do projeto está correta."""
    from pathlib import Path
    root = Path(__file__).parent

    required = [
        "config.py",
        "main.py",
        "requirements.txt",
        "crea_cat_ai/__init__.py",
        "crea_cat_ai/ingestion.py",
        "crea_cat_ai/analysis.py",
        "crea_cat_ai/metadata.py",
        "crea_cat_ai/signature.py",
        "crea_cat_ai/matching.py",
        "crea_cat_ai/compliance.py",
        "crea_cat_ai/verdict.py",
        "crea_cat_ai/report.py",
    ]

    all_ok = True
    for f in required:
        path = root / f
        if path.exists():
            print(f"  [OK] {f}")
        else:
            print(f"  [ERRO] {f} - não encontrado")
            all_ok = False

    return all_ok


def main() -> int:
    """Executa todas as verificações."""
    print("=" * 60)
    print("  CREA CAT AI - Verificação de Setup")
    print("=" * 60)
    print()

    results = {}

    print("1. Versão do Python")
    results["python"] = check_python_version()
    print()

    print("2. Dependências Python")
    deps = [
        ("openai", "openai"),
        ("PyMuPDF", "pymupdf"),
        ("pikepdf", "pikepdf"),
        ("pyHanko", "pyhanko"),
        ("Pillow", "PIL"),
    ]
    results["deps"] = all(check_import(name, imp) for name, imp in deps)
    print()

    print("3. Chave da API OpenAI")
    results["api_key"] = check_openai_key()
    print()

    print("4. Conexão com OpenAI API")
    results["api_conn"] = check_openai_connection()
    print()

    print("5. Estrutura do Projeto")
    results["structure"] = check_project_structure()
    print()

    # Resumo
    print("=" * 60)
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    if failed == 0:
        print(f"  RESULTADO: Tudo OK! ({passed}/{total} verificações passaram)")
        print("  O pipeline está pronto para uso.")
    else:
        print(f"  RESULTADO: {failed} problema(s) encontrado(s) ({passed}/{total} OK)")
        if not results.get("deps"):
            print("  Execute: pip install -r requirements.txt")
        if not results.get("api_key"):
            print("  Configure: OPENAI_API_KEY como variável de ambiente")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
