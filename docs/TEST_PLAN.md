# Test Plan

**Status:** living document · last updated 2026-07-22

---

## Strategy

Tests exist to protect specific properties. Each category below states what it
protects and what it deliberately does not.

| Category | Marker | Protects | Speed |
|----------|--------|----------|-------|
| Unit | `unit` | Domain invariants, orthographic rules, orchestration logic | <1s total |
| Integration | `integration` | The HTTP contract end to end through the real app | <1s total |
| Architecture | `architecture` | Layer boundaries, so the monolith stays modular | ~1s |
| Regression | `regression` | Previously-fixed behaviour | — |
| Benchmark | `benchmark` | Model quality and latency | excluded from default run |

Run everything: `pytest`. Run one category: `pytest -m unit`.

---

## Current state

**80 tests, all passing** (2026-07-22).

```
backend/tests/architecture/test_layering.py       3
backend/tests/integration/test_api.py            15
backend/tests/unit/test_arabic.py                18
backend/tests/unit/test_pipeline.py              18
backend/tests/unit/test_plugin_registry.py        9
backend/tests/unit/test_value_objects.py         17
```

---

## The properties that matter most

Ranked by consequence of failure. These are the tests to look at first if
anything is ever cut.

### 1. The platform cannot fabricate

The single most important property (ADR-0004, ADR-0005). If this breaks,
QalamAI produces fake history that is indistinguishable from real results.

| Test | Guards |
|------|--------|
| `TestHeritageClaim::test_rejects_a_claim_with_no_evidence` | An unsupported claim cannot be *constructed* |
| `TestAnalyzeWithoutModels::test_returns_503_rather_than_a_fabricated_reading` | No models → no reading, not a plausible one |
| `test_returns_a_reading_and_evidence_backed_claims` | Every claim on the wire carries evidence |
| `TestDegradation::test_missing_ocr_yields_no_reading_and_no_fabrication` | Downstream stages invent nothing |

### 2. Boundaries hold

If these break, the modular monolith silently becomes a big ball of mud and
ADR-0001's extraction path closes.

| Test | Guards |
|------|--------|
| `test_layering_contracts_hold` | All import-linter contracts |
| `test_application_layer_cannot_import_a_concrete_adapter` | "Replaceable AI components" is real |
| `test_domain_does_not_import_a_web_framework` | Domain stays usable from training code |

Running import-linter from pytest is deliberate: a boundary violation fails the
command a developer already runs, not only CI.

### 3. Scholarly fidelity

If these break, the platform corrupts the readings it exists to preserve.

| Test | Guards |
|------|--------|
| `TestCanonicalize::test_preserves_diacritics` | Vocalization is never silently destroyed |
| `TestFold::test_distinct_words_do_not_collide` | Lossy folding does not erase real lexical difference |
| `test_normalize_preserves_diacritics_but_search_key_does_not` | The two operations stay distinct (ADR-0008) |

### 4. Honest degradation

| Test | Guards |
|------|--------|
| `test_unavailable_component_is_reported_not_skipped` | "Broken" ≠ "not deployed" |
| `test_absent_component_is_skipped_not_unavailable` | The converse |
| `test_a_crashing_stage_is_contained_and_reported` | A failure is contained, not masked |
| `test_ocr_still_attempted_when_detection_is_unavailable` | Curated images stay analyzable |
| `test_names_every_missing_capability_with_a_reason` | Operators can act on `/readiness` |

---

## Test doubles

Fakes live in `backend/tests/conftest.py` and are importable only from tests.

They are **test doubles, not placeholders**. The distinction matters given
ADR-0004: a double lets pipeline behaviour be exercised deterministically
without model weights, and can never be reached by production code. A
placeholder ships to users. The layering makes the difference structural — the
`tests` package is not on the production import path.

`FakeOcrEngine` deliberately emits text with a kashida and a 0.12-confidence
fragment, so canonicalization and threshold filtering are exercised on realistic
artefacts rather than clean strings.

---

## Quality gates

All CI-enforced, all currently passing:

| Gate | Command | State |
|------|---------|-------|
| Lint | `ruff check .` | 0 errors |
| Format | `ruff format --check .` | clean |
| Types | `mypy` (strict) | 0 errors, 28 files |
| Boundaries | `lint-imports` | 3 contracts kept |
| Tests | `pytest` | 80 passed |

CI runs each gate with `if: '!cancelled()'` so one run reports every problem
rather than one problem per push.

`mypy` runs in strict mode with `disallow_any_unimported` and
`warn_unreachable`. Strong typing is a stated platform principle; strict mode is
what makes it more than an aspiration.

---

## Coverage policy

No numeric threshold is enforced, deliberately. A coverage percentage is a proxy
that is easy to satisfy without testing anything meaningful, and the four
property groups above are what actually protect the platform.

Coverage **is** measured and reported in CI, used as a diagnostic for finding
untested code paths rather than as a gate.

---

## Gaps

Recorded rather than left implicit:

| Gap | Risk | Scheduled |
|-----|------|-----------|
| No property-based tests on normalization | Hand-written cases may miss classes of input; Hypothesis fits idempotence and fold-stability well | M3 |
| No benchmark suite | No CER/WER, no latency baseline; the `benchmark` marker exists but is unused | M3 |
| No load or concurrency testing | Async correctness under load unverified; a forgotten `asyncio.to_thread` (ADR-0006) would not be caught | M8 |
| No mobile tests | The Flutter shell has no test suite | M7 |
| No contract tests between client and server | API drift would be caught late | M7 |
| No adversarial evaluation for generated narrative | ADR-0005 grounds claims, not the prose connecting them | M6 |
| No mutation testing | Test-suite effectiveness unmeasured | post-M3 |

---

## Conventions

- Test names state the property, not the mechanics:
  `test_returns_503_rather_than_a_fabricated_reading`, not `test_analyze_503`.
- Non-obvious assertions carry a docstring explaining *why* the property
  matters. A future maintainer must be able to tell whether a failing test found
  a bug or encoded an outdated assumption.
- Tests that guard an ADR reference it by number.
- One behaviour per test.
