---
phase: 04-metadata-digital-signature
plan: "02"
subsystem: signature
tags: [pyhanko, icp-brasil, gov-br, digital-signature, tdd]
dependency_graph:
  requires:
    - 04-01 (metadata.py — parallel plan, same phase)
    - config.py (PROJECT_ROOT for certs/ path)
  provides:
    - crea_cat_ai/signature.py (ResultadoAssinatura, validar_assinaturas)
    - tests/test_signature.py (unit tests SIGN-01, SIGN-02, SIGN-03)
  affects:
    - main.py (Phase 4 integration — Phase 5 plan)
    - verdict.py (Phase 7 — confiavel flag from signatarios)
tech_stack:
  added: []
  patterns:
    - pyHanko PdfFileReader(strict=False) for hybrid-reference Gov-Br PDFs
    - KeyUsageConstraints(digital_signature) for Gov-Br cert compatibility
    - ValidationContext(moment=self_reported_timestamp) for expired-cert handling
    - asn1_cms.ContentInfo.load() for P7B chain parsing
key_files:
  created:
    - crea_cat_ai/signature.py
    - tests/test_signature.py
  modified: []
decisions:
  - "strict=False in PdfFileReader — Gov-Br PDFs are hybrid-reference and fail with strict=True"
  - "KeyUsageConstraints(digital_signature) — Gov-Br certs lack non_repudiation, pyHanko default rejects them"
  - "moment=self_reported_timestamp — validates expired certs that were valid at signing time"
  - "revocation_mode=soft-fail — offline validation without CRL download (MVP)"
  - "No anomalias field in ResultadoAssinatura — SIGN-03: absence of signature is valid state"
  - "Download failure falls back to ([], []) — pipeline continues with confiavel=False, not crashed"
  - "test_moment_self_reported uses timezone-aware datetime and ValidationContext.__init__ patch — naive datetime raises ValueError in ValidationContext"
metrics:
  duration_seconds: 164
  completed_date: "2026-03-29"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
  tests_added: 11
---

# Phase 04 Plan 02: Digital Signature Validation Summary

**One-liner:** pyHanko Gov-Br digital signature validation with strict=False, KeyUsageConstraints(digital_signature), moment=self_reported_timestamp, and soft-fail revocation — 11 unit tests all GREEN.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Create unit tests for signature detection and validation | f0e0eed | tests/test_signature.py |
| 2 (GREEN) | Implement signature.py with pyHanko validation and Gov-Br chain | 9e09747 | crea_cat_ai/signature.py, tests/test_signature.py (fix) |

## What Was Built

### `crea_cat_ai/signature.py`

Full implementation with three components:

**1. `ResultadoAssinatura` dataclass**
- Fields: `presente`, `quantidade`, `signatarios`
- NO `anomalias` field — absence of digital signature is valid state (SIGN-03)
- Each `signatarios` dict: `{nome, emissor, valido, integro, confiavel, sumario, erro}`

**2. `_carregar_govbr_chain() -> tuple[list, list]`**
- Downloads Gov-Br chain from `http://repo.iti.br/docs/Cadeia_GovBr-der.p7b`
- Caches to `certs/govbr-chain.p7b` (creates directory if absent)
- Parses P7B with `asn1_cms.ContentInfo.load()`
- Separates root certs (subject == issuer) from intermediates
- On download/parse failure: prints pt-BR warning, returns `([], [])` — pipeline continues

**3. `validar_assinaturas(caminho_pdf: Path) -> ResultadoAssinatura`**
- Opens PDF with `PdfFileReader(f, strict=False)` — required for Gov-Br hybrid-reference PDFs
- Gets `reader.embedded_regular_signatures`
- Returns `ResultadoAssinatura(presente=False)` cleanly when no sigs (SIGN-03)
- For each sig: builds `ValidationContext` with `moment=sig.self_reported_timestamp`
- Calls `validation.validate_pdf_signature(..., key_usage_settings=KeyUsageConstraints({"digital_signature"}))`
- Captures exceptions into `entry["erro"]` — never crashes pipeline

### `tests/test_signature.py`

11 unit tests (2 integration tests excluded from default run):

| Test | Requirement | What it verifies |
|------|-------------|-----------------|
| `test_resultado_sem_assinatura` | SIGN-01 | `presente=False` → `quantidade=0`, `signatarios=[]` |
| `test_resultado_com_assinatura` | SIGN-01 | Correct dataclass structure with signatario dict |
| `test_ausencia_nao_e_anomalia` | SIGN-03 | No `anomalias` field in `ResultadoAssinatura` |
| `test_validar_sem_assinatura` | SIGN-01 | Mock reader with no sigs → `presente=False` |
| `test_validar_com_assinatura_valida` | SIGN-02 | Mock valid sig → `signatarios[0]["valido"]==True` |
| `test_validar_com_assinatura_invalida` | SIGN-02 | Exception → captured in `signatarios[0]["erro"]` |
| `test_reader_strict_false` | anti-pattern | `PdfFileReader` called with `strict=False` |
| `test_key_usage_constraints` | anti-pattern | `KeyUsageConstraints({"digital_signature"})` passed |
| `test_moment_self_reported` | anti-pattern | `ValidationContext` receives `moment=timestamp` |
| `test_carregar_govbr_chain_cached` | SIGN-02 | `urlopen` NOT called when cache exists |
| `test_carregar_govbr_chain_download` | SIGN-02 | `urlopen` called with `GOVBR_CHAIN_URL` when no cache |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_moment_self_reported using naive datetime**
- **Found during:** Task 2 GREEN phase verification
- **Issue:** Test used `datetime.datetime(2026, 1, 20, 10, 0, 0)` (timezone-naive). `ValidationContext` raises `ValueError: moment is a naive datetime object` when passed a naive datetime. This caused `validate_pdf_signature` to never be called, making the assertion `len(captured_contexts) == 1` fail with `assert 0 == 1`.
- **Fix:** Changed test timestamp to timezone-aware (`datetime.timezone.utc`). Also changed assertion strategy: instead of capturing via `validate_pdf_signature` side_effect (unreachable when VC raises), patched `ValidationContext.__init__` directly to capture kwargs before the VC is constructed.
- **Files modified:** tests/test_signature.py
- **Commit:** 9e09747

## Known Stubs

None — `signature.py` is fully implemented with real logic. No hardcoded empty values or TODO placeholders flow to callers.

## Verification Results

```
python -m pytest tests/test_signature.py -v
11 passed, 2 deselected in 0.87s

python -c "from crea_cat_ai.signature import ResultadoAssinatura, validar_assinaturas"
Import OK
```

## Self-Check: PASSED

- crea_cat_ai/signature.py: FOUND
- tests/test_signature.py: FOUND
- Commit f0e0eed: FOUND (test: add failing tests)
- Commit 9e09747: FOUND (feat: implement signature.py)
