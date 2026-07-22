# Backend

FastAPI service implementing the QalamAI platform. See
[`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) for the full design.

---

## Setup

Requires Python 3.12 (matched exactly by CI — see
[ADR-0002](../docs/ARCHITECTURE_DECISIONS.md#adr-0002-python-312-with-bounded-dependency-pins)).

```bash
# from the repository root
python -m venv .venv
.venv/Scripts/activate        # Windows;  source .venv/bin/activate on Unix
pip install -e '.[dev]'
```

All configuration lives in the root `pyproject.toml`. There is no separate
`requirements.txt`.

## Run

```bash
uvicorn qalam.api.app:app --reload
```

Interactive docs at `http://127.0.0.1:8000/docs`.

## Verify

```bash
ruff check .          # lint
ruff format --check . # formatting
mypy                  # strict type check
lint-imports          # architectural boundaries
pytest                # 80 tests
```

Run one test category: `pytest -m unit` (also `integration`, `architecture`).

---

## Layout

```
backend/src/qalam/
├── core/          config, logging, error taxonomy — knows nothing about heritage
├── domain/        entities, value objects, ports — no web framework
├── plugins/       civilization knowledge; base contract + islamic_epigraphy/
├── application/   the analysis use case; orchestrates ports
├── adapters/      concrete engines — currently only unavailable.py
├── composition/   the object graph; where interfaces meet implementations
└── api/           HTTP contract, routing, error translation
```

Imports may only point **downward** through:

```
api > composition > adapters > application > plugins > domain > core
```

Enforced by `lint-imports` in CI and by `tests/architecture/`.

---

## Things that will surprise you

**`/analyze` always returns 503.** No OCR engine exists. Every capability
resolves to an adapter from `adapters/unavailable.py` that declares the gap
rather than returning plausible output. This is intentional and load-bearing —
see [ADR-0004](../docs/ARCHITECTURE_DECISIONS.md#adr-0004-unavailable-capabilities-fail-loudly-never-plausibly).
Check `GET /api/v1/readiness` for exactly what is missing.

**`application` sits *below* `adapters` in the layer order.** This looks
inverted, and it is deliberate: it makes it impossible for an orchestrator to
import a concrete engine.

**The domain uses stdlib dataclasses, not Pydantic.** Pydantic lives only at the
API boundary and in config, with explicit mapping between them
([ADR-0003](../docs/ARCHITECTURE_DECISIONS.md#adr-0003-separate-domain-entities-from-wire-schemas)).

**`HeritageClaim` raises if constructed without evidence.** That is the
anti-hallucination guarantee, and it is a type invariant rather than a runtime
check
([ADR-0005](../docs/ARCHITECTURE_DECISIONS.md#adr-0005-evidence-is-structurally-required-for-every-historical-claim)).

**Arabic canonicalization keeps diacritics.** Use `plugin.search_key()` for
corpus matching, never `normalize_text()`
([ADR-0008](../docs/ARCHITECTURE_DECISIONS.md#adr-0008-conservative-canonicalization-separate-from-lossy-folding)).

**`RUF001`–`RUF003` are disabled.** The ambiguous-Unicode checks fire on
essentially every Arabic literal in the normalization tables and tests.

---

## Adding a capability

Replacing an unavailable adapter with a real engine:

1. Implement the port from `domain/ports.py` in `adapters/`.
2. If CPU-bound, wrap synchronous work in `asyncio.to_thread`
   ([ADR-0006](../docs/ARCHITECTURE_DECISIONS.md#adr-0006-asynchronous-ports-with-threaded-cpu-bound-adapters)).
   Forgetting this blocks the event loop and only shows up under load.
3. Change one line in `composition/container.py::build_components`.
4. Add tests; update `MODEL_REGISTRY.md` and `PERFORMANCE.md`.

Nothing else changes.

## Adding a civilization

1. Add scripts to the `Script` enum if absent.
2. Create `plugins/<civilization>/` implementing `CivilizationPlugin`.
3. Add one line to `composition/container.py::build_plugin_registry`.
4. Add the plugin to the independence contract in `pyproject.toml`.

No change to `domain`, `application`, `api`, or any other plugin.

---

## Configuration

Environment variables, prefix `QALAM_`, nested with `__`:

```bash
QALAM_ENVIRONMENT=local
QALAM_LOG_LEVEL=INFO
QALAM_LOG_FORMAT=console          # 'json' in deployment
QALAM_DEFAULT_CIVILIZATION=islamic_epigraphy
QALAM_OCR__MIN_CONFIDENCE=0.5
QALAM_OCR__DEFAULT_ENGINE=unavailable
QALAM_KNOWLEDGE_GRAPH__ENDPOINT=
```

Unknown variables are **rejected** at startup rather than silently ignored, so a
typo fails loudly instead of taking a default. Defaults are fail-closed: an
unconfigured deployment serves nothing rather than something wrong.
