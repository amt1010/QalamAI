# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

While the platform is pre-1.0, breaking changes may occur in minor releases.

---

## [Unreleased]

### Added — M5 Heritage Knowledge Graph design (2026-07-23)

Design only. **No implementation**, pending domain expert review.

- `KNOWLEDGE_GRAPH_SCHEMA.md` rewritten from a list of open questions into a
  design: ten formalized competency questions, entity model, claim model,
  physical schema, and three-tier inscription matching
- `EXPERT_REVIEW_BRIEF.md` — fourteen questions for a domain expert, written
  without technical jargon
- **ADR-0009** — PostgreSQL + pgvector + pg_trgm as the HKG store
- **ADR-0010** — borrow from CIDOC CRM without adopting it
- **ADR-0011** — reified claims instead of attributed relationships

### Changed

- M5 pulled forward ahead of M2. M2 is well-understood engineering; M5 holds the
  project's only near-irreversible decision and its hardest modelling problem
- `InscriptionText` separated from `InscriptionInstance` — the Basmala is one
  text with thousands of physical carvings, and conflating them makes "where
  else does this inscription appear?" unanswerable
- Research questions #4 and #5 closed; #5a (consensus scoring) opened in their
  place and flagged as blocking

### Notable

The design **corrected an assumption in its own first draft.** That draft framed
store selection as a three-way choice and described the relational option as
"awkward for deep traversal". Formalizing the competency questions showed
maximum traversal depth is 3, every path is schema-known, and none of the ten
questions needs a graph algorithm — while the most distinctive one ("show
similar inscriptions") is vector similarity, not a graph query at all. A graph
database would have been selected for traversal the platform never performs.

Recorded in `RESEARCH_LOG.md` 2026-07-23 and ADR-0009.

---

## [0.1.0] — 2026-07-22 — M1: Architecture and contracts

First milestone. Establishes the foundation: layered architecture, domain
model, plugin system, HTTP contract, and the tooling gate.

**No trained models are included.** Every AI capability reports itself
unavailable, and `POST /analyze` returns 503. This is the honest state of the
platform, visible at `GET /api/v1/readiness`.

### Added

**Architecture**
- Layered modular monolith: `api > composition > adapters > application >
  plugins > domain > core`, enforced by import-linter with 3 contracts
  (ADR-0001)
- Domain layer of frozen stdlib dataclasses, importable without a web framework
- Seven ports as `Protocol`s, all async (ADR-0006)
- Explicit composition root; no DI framework (ADR-0007)

**Grounding**
- `HeritageClaim` cannot be constructed without `Evidence`, making an
  unsupported historical claim unrepresentable (ADR-0005)
- `Evidence` carries a `Citation` with a stable identifier and kind, plus
  calibrated `Confidence`

**Honest degradation**
- `qalam.adapters.unavailable` — adapters that declare gaps with actionable
  reasons and milestone references instead of returning plausible output
  (ADR-0004)
- Pipeline distinguishes `COMPLETED` / `SKIPPED` / `UNAVAILABLE` / `FAILED`, so
  "not deployed" and "broken" stay separable
- `GET /api/v1/readiness` reports per-capability availability, separate from
  the dependency-free `/health`

**Plugins**
- `CivilizationPlugin` contract and explicit `PluginRegistry`
- Islamic epigraphy plugin covering Arabic, Persian, Ottoman Turkish
- Arabic orthographic handling: NFKC-based canonicalization preserving
  diacritics, separate lossy fold for corpus matching, and `strip_diacritics`
  for building diacritic-restoration training pairs (ADR-0008)

**API v1**
- `GET /health`, `GET /readiness`, `GET /civilizations`, `POST /analyze`
- Wire schemas separate from domain entities, with explicit mapping (ADR-0003)
- Uniform error shape `{code, message, details}` with stable codes
- `tourist` / `research` / `developer` modes governing disclosure only

**Engineering**
- Git repository, `.gitignore`, `.gitattributes` for cross-platform line endings
- `pyproject.toml` with bounded dependency pins; Python 3.12 matching CI
  (ADR-0002)
- `ruff`, `mypy --strict`, `import-linter`, `pytest` — all CI-gated
- 80 tests across unit, integration, and architecture suites
- Typed configuration via `pydantic-settings` with `extra="forbid"`
- Structured logging via `structlog`

**Documentation**
- `PROJECT_MASTER_PLAN.md`, `ARCHITECTURE.md`, `ARCHITECTURE_DECISIONS.md`
  (ADR-0001 through ADR-0008), `API_SPECIFICATION.md`, `TEST_PLAN.md`,
  `RESEARCH_LOG.md`, `DATASET_MANIFEST.md`, `MODEL_REGISTRY.md`,
  `KNOWLEDGE_GRAPH_SCHEMA.md`, `SECURITY.md`, `PERFORMANCE.md`

### Removed

- **Placeholder inference pipeline.** The previous `InferencePipeline` returned
  a fixed Arabic string, an English translation, `confidence: 0.91`, and the
  category "Quran" for every input. In a heritage context that output is
  indistinguishable from a genuine reading and could propagate into the
  historical record. Replaced by adapters that state what is missing and return
  nothing (ADR-0004).
- Module-level pipeline instantiation at import time, which made the API
  untestable without monkeypatching.
- `backend/conftest.py` `sys.path` manipulation, obsolete under the src-layout.

### Known gaps

Tracked in `ARCHITECTURE.md` § Known gaps. The significant ones: no lock file,
no authentication, `image_url` is accepted but never fetched, no benchmarks,
Arabic folding rules not yet reviewed by an epigrapher, and the HKG is entirely
undesigned.
