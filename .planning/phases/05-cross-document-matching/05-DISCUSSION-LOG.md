# Phase 5: Cross-Document Matching - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 05-cross-document-matching
**Areas discussed:** Matching strategy, Result structure, Date interval logic, Semantic scope comparison
**Mode:** --auto (all decisions auto-selected from recommended defaults)

---

## Matching Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Single GPT call | Batch all fuzzy/semantic comparisons in one call — lower cost, context coherence | ✓ |
| Separate calls per field | Individual GPT call for each fuzzy field — more granular but costly | |
| Local fuzzy matching | Use difflib/fuzzywuzzy locally — no GPT cost but lower accuracy for Portuguese | |

**User's choice:** Single GPT call (auto-selected — recommended default, consistent with Phase 3 pattern)
**Notes:** Exact matching (CPF, CNPJ, CREA/RNP) and date interval validation done locally in Python.

---

## Result Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic with StatusCampo enum | Per-field MATCH/DIVERGENTE/AUSENTE — type-safe, consistent | ✓ |
| Plain dict | Simpler but no type safety | |
| Dataclass | Lightweight but less validation | |

**User's choice:** Pydantic with StatusCampo enum (auto-selected — matches analysis.py pattern)
**Notes:** Each field includes status, valor_art, valor_atestado, detalhes.

---

## Date Interval Logic

| Option | Description | Selected |
|--------|-------------|----------|
| Strict interval check | Atestado dates WITHIN ART range, missing → AUSENTE | ✓ |
| Fuzzy tolerance | Allow small overlap outside range | |
| Strict with warning | Flag near-misses as warning | |

**User's choice:** Strict interval check (auto-selected — matches CREA business rule)
**Notes:** Missing/malformed dates → AUSENTE, not DIVERGENTE.

---

## Semantic Scope Comparison

| Option | Description | Selected |
|--------|-------------|----------|
| GPT-4.1 semantic with confidence | Full semantic comparison with score and justification | ✓ |
| Keyword overlap | Count shared keywords — cheap but misses synonyms | |

**User's choice:** GPT-4.1 semantic with confidence (auto-selected — per XREF-06 requirement)
**Notes:** Known Par 2 divergence must be caught.

---

## Claude's Discretion

- GPT prompt internal design for fuzzy/semantic matching
- API pattern choice (follow Responses API from analysis.py)
- Both-fields-absent handling
- Config.py weight integration deferred to Phase 7

## Deferred Ideas

None — discussion stayed within phase scope
