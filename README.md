# QalamAI

An AI-powered **Heritage Intelligence Platform** for understanding, preserving,
explaining, and connecting historical inscriptions.

The first supported civilization is Islamic epigraphy. The architecture is
plugin-based so further traditions can be added without modifying the core.

OCR is one subsystem. It is not the product.

---

## Status: M1 complete — architecture and contracts

**No AI models are implemented yet.** Every capability reports itself
unavailable, and `POST /api/v1/analyze` returns `503` naming what is missing.

This is deliberate. The platform never returns a fabricated reading,
translation, or historical claim — in a heritage context, invented output is
indistinguishable from a real result and can propagate into the historical
record. See [ADR-0004](docs/ARCHITECTURE_DECISIONS.md#adr-0004-unavailable-capabilities-fail-loudly-never-plausibly).

Live capability status: `GET /api/v1/readiness`.

| Gate | State |
|------|-------|
| Tests | 80 passing |
| Types | `mypy --strict`, 0 errors |
| Lint | `ruff`, 0 errors |
| Architecture | 3 import-linter contracts kept |

---

## Quick start

Requires Python 3.12.

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows;  source .venv/bin/activate on Unix
pip install -e '.[dev]'

pytest                        # 80 tests
uvicorn qalam.api.app:app --reload
```

Then visit `http://127.0.0.1:8000/docs`, or:

```bash
curl http://127.0.0.1:8000/api/v1/readiness
```

---

## Architecture in one diagram

One deployable process, seven layers, boundaries checked by CI:

```
api  >  composition  >  adapters  >  application  >  plugins  >  domain  >  core
                    imports may only point downward
```

Two placements carry most of the weight:

- **`application` sits below `adapters`**, so an orchestrator *cannot* import a
  concrete engine. "Replaceable AI components" is a build failure, not a
  convention.
- **`domain` may not import a web framework**, so it stays usable from training
  notebooks and batch jobs.

Full detail: [ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Two guarantees, enforced by code

**1. The platform never fabricates.** Unimplemented capabilities resolve to
adapters that declare the gap and return nothing.
([ADR-0004](docs/ARCHITECTURE_DECISIONS.md#adr-0004-unavailable-capabilities-fail-loudly-never-plausibly))

**2. Every historical claim carries evidence.** Not by prompting, and not by
validating after the fact — `HeritageClaim` raises at construction without it,
so an unsupported claim has no representation for any generator to emit.
([ADR-0005](docs/ARCHITECTURE_DECISIONS.md#adr-0005-evidence-is-structurally-required-for-every-historical-claim))

---

## Repository layout

| Path | Contents |
|------|----------|
| `backend/src/qalam/` | The platform |
| `backend/tests/` | Unit, integration, and architecture tests |
| `mobile/` | Flutter shell (architecture work scheduled for M7) |
| `datasets/` | Dataset pipeline structure — no data acquired yet |
| `docs/` | Living documentation |

---

## Documentation

| Document | Purpose |
|----------|---------|
| [PROJECT_MASTER_PLAN.md](docs/PROJECT_MASTER_PLAN.md) | Vision, milestones, definition of done |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, with planned work marked and gaps listed |
| [ARCHITECTURE_DECISIONS.md](docs/ARCHITECTURE_DECISIONS.md) | ADRs — rationale, rejected alternatives, reversal triggers |
| [API_SPECIFICATION.md](docs/API_SPECIFICATION.md) | HTTP contract |
| [TEST_PLAN.md](docs/TEST_PLAN.md) | Test strategy and the properties that matter |
| [RESEARCH_LOG.md](docs/RESEARCH_LOG.md) | Technology evaluations and open research questions |
| [KNOWLEDGE_GRAPH_SCHEMA.md](docs/KNOWLEDGE_GRAPH_SCHEMA.md) | HKG requirements and open design questions |
| [DATASET_MANIFEST.md](docs/DATASET_MANIFEST.md) | Dataset provenance and licensing policy |
| [MODEL_REGISTRY.md](docs/MODEL_REGISTRY.md) | Model versions, metrics, and promotion policy |
| [SECURITY.md](docs/SECURITY.md) | Threat model and current posture |
| [PERFORMANCE.md](docs/PERFORMANCE.md) | Budgets and benchmark methodology |
| [CHANGELOG.md](docs/CHANGELOG.md) | Notable changes |

---

## Next milestone — M2: image ingestion and preprocessing

Turns `image_url` from an accepted string into a fetched, validated, enhanced
image. **Blocked on SSRF and image-payload mitigations** — see
[SECURITY.md](docs/SECURITY.md) T1 and T2.

The project's critical path is not model architecture. It is data: a benchmark
dataset for Arabic monumental epigraphy, and authoritative licensable sources
for the knowledge graph. Both are sourcing problems and should start early.

---

## Contributing

Every change must pass:

```bash
ruff check . && ruff format --check . && mypy && lint-imports && pytest
```

A feature is complete only when it meets the
[Definition of Done](docs/PROJECT_MASTER_PLAN.md#definition-of-done).
