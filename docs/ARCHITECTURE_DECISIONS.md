# Architecture Decision Records

Each record states a decision, the forces behind it, and — most importantly —
what would make us revisit it. A decision without a stated reversal trigger is
a decision nobody will ever dare to change.

Status values: `Proposed` · `Accepted` · `Superseded by ADR-XXXX` · `Deprecated`

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0001](#adr-0001-modular-monolith-with-machine-enforced-layering) | Modular monolith with machine-enforced layering | Accepted | 2026-07-22 |
| [0002](#adr-0002-python-312-with-bounded-dependency-pins) | Python 3.12 with bounded dependency pins | Accepted | 2026-07-22 |
| [0003](#adr-0003-separate-domain-entities-from-wire-schemas) | Separate domain entities from wire schemas | Accepted | 2026-07-22 |
| [0004](#adr-0004-unavailable-capabilities-fail-loudly-never-plausibly) | Unavailable capabilities fail loudly, never plausibly | Accepted | 2026-07-22 |
| [0005](#adr-0005-evidence-is-structurally-required-for-every-historical-claim) | Evidence is structurally required for every historical claim | Accepted | 2026-07-22 |
| [0006](#adr-0006-asynchronous-ports-with-threaded-cpu-bound-adapters) | Asynchronous ports with threaded CPU-bound adapters | Accepted | 2026-07-22 |
| [0007](#adr-0007-explicit-composition-root-instead-of-a-di-framework) | Explicit composition root instead of a DI framework | Accepted | 2026-07-22 |
| [0008](#adr-0008-conservative-canonicalization-separate-from-lossy-folding) | Conservative canonicalization separate from lossy folding | Accepted | 2026-07-22 |

---

## ADR-0001: Modular monolith with machine-enforced layering

**Status:** Accepted · 2026-07-22

### Context

The platform must eventually run as independently deployable services — the
Heritage Knowledge Graph in particular is specified as its own service with its
own API, deployment, and lifecycle. Clients will include mobile, web, AR/VR,
museum kiosks, and third-party APIs.

Against that, the project today has no trained models, no dataset, no users, and
one developer. Splitting into three or four deployables now would buy real
independence at the cost of network contracts between components whose
interfaces are still being discovered, three CI/CD pipelines, and a
docker-compose dance before anyone can run a test.

The failure mode we actually need to prevent is not "we deployed as one
process". It is "the boundaries rotted, so splitting later means a rewrite."

### Decision

Build one deployable FastAPI application with hard internal boundaries, layered:

```
api  >  composition  >  adapters  >  application  >  plugins  >  domain  >  core
```

A layer may import only from layers below it. The stack is declared in
`pyproject.toml` under `[tool.importlinter]` and checked by `lint-imports` in
CI and in the test suite.

Two placements are deliberate and worth calling out:

- **`application` sits below `adapters`.** The orchestrator therefore *cannot*
  import a concrete engine. "Replaceable AI components" stops being an
  aspiration and becomes a build failure.
- **`domain` may not import any web framework.** It stays usable from a
  training notebook or a batch job, which is where most of this platform's
  real work will eventually happen.

The HKG is accessed exclusively through the `KnowledgeGraphClient` port, so
extracting it into a separate service is an adapter swap plus a deployment
change — not a domain change.

### Consequences

Positive: one process to run, one test command, refactoring across boundaries
is a compile-time concern rather than a versioned API migration. Extraction
later is mechanical because the seams already exist and are verified.

Negative: one scaling unit and one blast radius. A memory-hungry CV model and a
latency-sensitive API share a process. Accepted for now — no such model exists
yet.

Discipline is not assumed. It is checked; see `backend/tests/architecture/`.

### Revisit when

- Any single subsystem needs independent scaling or independent hardware (the
  first GPU-resident model is the likely trigger).
- The HKG acquires write traffic or consumers outside this platform.
- Team size exceeds roughly six engineers, where merge contention on one
  deployable starts to cost more than network contracts would.

### Alternatives rejected

**Separate services immediately.** Most faithful to the long-term target, and
rejected on sequencing: we would be freezing interfaces into network contracts
before we understand them. Interface mistakes are cheap to fix inside a process
and expensive to fix across a version boundary.

**Multi-package monorepo, single deploy.** Boundaries enforced by packaging
rather than by lint. Sound, but it adds per-package build config and release
ceremony to buy an enforcement guarantee that import-linter already provides at
a fraction of the cost.

---

## ADR-0002: Python 3.12 with bounded dependency pins

**Status:** Accepted · 2026-07-22

### Context

The repository previously had no dependency manifest at all. Dependencies were
duplicated as a loose `pip install` line in CI and in a README. The local
virtualenv was Python 3.14 while CI pinned 3.11, so "works locally" and "passes
CI" were unrelated claims.

For a platform whose stated goals include reproducible experiments and
versioned datasets, an unpinned, undeclared, environment-divergent dependency
setup is a foundational defect.

### Decision

Single `pyproject.toml` at the repository root, hatchling build backend,
src-layout package at `backend/src/qalam`. `requires-python = ">=3.12,<3.13"`,
matched exactly by CI.

Python 3.12 rather than 3.11 or 3.13/3.14: 3.12 has the broadest wheel
availability across the CV/ML ecosystem this platform will depend on
(PyTorch, ONNX Runtime, OpenCV), while 3.13+ still has gaps in that ecosystem
and 3.11 reaches end of life sooner. Availability of pre-built ML wheels is the
binding constraint, not language features.

All dependencies carry both lower and upper bounds. Unbounded ranges make
builds non-reproducible, which matters more here than staying current.

The src-layout removes the previous `conftest.py` `sys.path` manipulation:
tests run against the installed package.

### Consequences

Positive: one declaration of truth, identical environments locally and in CI,
`pip install -e '.[dev]'` is the whole setup.

Negative: upper bounds require periodic deliberate maintenance. That is the
intent — upgrades become decisions rather than accidents.

### Revisit when

- A required ML dependency ships only for a newer Python.
- Dependency resolution becomes slow or conflicted enough to justify a proper
  lock file (`uv.lock` or pip-tools). Bounded pins are *not* a lock file; they
  constrain direct dependencies but leave transitive resolution free. This is a
  known gap, accepted for now and scheduled for M2.

---

## ADR-0003: Separate domain entities from wire schemas

**Status:** Accepted · 2026-07-22

### Context

The obvious economy is to expose Pydantic domain models directly as the HTTP
contract. It removes a mapping layer and keeps one definition per concept.

The cost appears later. Once a mobile app is deployed to museum visitors' phones
and a kiosk vendor has integrated the API, every internal refactor becomes a
public contract change. Field renames, restructuring, and splitting an entity
all turn into API migrations. In practice the domain then stops being refactored
at all.

### Decision

`qalam.domain.entities` uses frozen stdlib dataclasses. `qalam.api.v1.schemas`
defines Pydantic models for the wire, plus explicit mapping functions.

This keeps the domain importable without Pydantic (relevant for training and
batch code), and gives one obvious place — `to_response` — for
audience-dependent disclosure, such as omitting stage diagnostics outside
developer mode.

### Consequences

Positive: internal and external evolution are decoupled. Redaction has a single
site rather than being scattered through handlers.

Negative: two definitions per concept and a mapping function to maintain. Real,
and accepted; the mapping layer is mechanical and covered by the API tests.

### Revisit when

The mapping becomes a meaningful share of maintenance without having prevented
a single breaking change — reassess after v2 of the API exists.

---

## ADR-0004: Unavailable capabilities fail loudly, never plausibly

**Status:** Accepted · 2026-07-22

### Context

The prior skeleton's pipeline returned a fixed response: the Arabic string
`القرآن الكريم`, the translation "The Holy Quran", confidence `0.91`, and
category "Quran" — for any input whatsoever.

As scaffolding this is unremarkable. In this domain it is dangerous. That output
is indistinguishable from a genuine result to every consumer: the mobile client,
a screenshot, a museum label, a student's citation. A confidence of 0.91 is an
explicit assertion of reliability. Fabricated readings of historical
inscriptions can propagate into the record and cannot be recalled.

### Decision

No component ever returns invented output. Where a capability is not
implemented, the deployment wires an adapter from `qalam.adapters.unavailable`
that reports `is_available = False` with a specific reason and a milestone
reference.

The pipeline records such a stage as `UNAVAILABLE` (distinct from `SKIPPED`,
meaning not deployed, and `FAILED`, meaning it raised) and continues, so stages
that *can* contribute still do. `POST /analyze` returns **503** with the missing
capabilities named whenever no transcription was produced, because an endpoint
whose purpose is to read an inscription has not succeeded if there is no
reading — and an uptime dashboard should say so.

`GET /readiness` reports per-capability availability, separately from
`/health`, which stays dependency-free so orchestrators do not restart healthy
processes over model gaps.

### Consequences

Positive: an unfinished platform is honest about being unfinished. Operators
get an exact list of what to fix. Test doubles used for development live under
`tests/` and can never be imported by production code.

Negative: the API is not "demoable" without real models. This is the intended
trade — a demo built on fabricated heritage data is a liability, not an asset.

### Revisit when

Never for the fabrication rule. The *transport* of unavailability (503 versus a
200 carrying a status field) may be revisited if clients need partial results
more than they need honest uptime metrics.

---

## ADR-0005: Evidence is structurally required for every historical claim

**Status:** Accepted · 2026-07-22

### Context

The platform's central requirement is that the LLM never hallucinates
historical facts, and that every answer is grounded in the Knowledge Graph with
supporting evidence.

Prompt instructions do not achieve this. Post-hoc validation does not either —
it runs after the claim exists, and every validator eventually has a bypass.

### Decision

Make an unsupported claim *unrepresentable*.

`HeritageClaim` requires a non-empty `tuple[Evidence, ...]` and raises at
construction otherwise. `Evidence` requires a `Citation` (title, stable
identifier, kind) and a `Confidence`. The wire schema mirrors this with
`Field(min_length=1)` on `evidence`.

The pipeline builds claims *from* retrieved evidence rather than generating
statements and attaching citations afterwards. With no evidence there are no
claims, and the platform stays silent about history it cannot source.

The `Explainer` port receives evidence as an argument; an implementation that
can generate without it violates this ADR.

`KnowledgeGraphSettings.require_evidence` defaults to true and must remain true
in production.

### Consequences

Positive: no code path can emit an unsourced historical statement. The
guarantee is a type invariant, tested in
`tests/unit/test_value_objects.py::TestHeritageClaim`.

Negative: the platform will often be able to transcribe and translate an
inscription while saying nothing about its history, until the HKG is populated.
Correct behaviour, and it should be communicated as such in the UI rather than
papered over.

### Revisit when

Never for the invariant itself. The *shape* of `Evidence` will evolve as the
HKG schema matures (see `KNOWLEDGE_GRAPH_SCHEMA.md`).

---

## ADR-0006: Asynchronous ports with threaded CPU-bound adapters

**Status:** Accepted · 2026-07-22

### Context

Pipeline stages divide into two kinds. HKG queries, hosted translation, and
remote inference are I/O-bound. Local CV, OCR, and image enhancement are
CPU-bound. A single interface style has to serve both.

### Decision

All ports are `async def`. CPU-bound adapters wrap their synchronous work in
`asyncio.to_thread` rather than blocking the event loop.

Async is chosen as the common style because most stages are I/O-bound, and
because a synchronous interface cannot host an async implementation without an
event loop hack, whereas the reverse direction is a one-line wrapper.

### Consequences

Positive: I/O-bound stages get concurrency for free; the API layer is async
throughout with no bridging.

Negative: `asyncio.to_thread` is a discipline adapters must remember, and a
forgotten wrapper stalls the whole loop. Mitigation: this belongs in the adapter
review checklist, and event-loop lag should be a monitored metric once real
models land (tracked in `PERFORMANCE.md`).

### Revisit when

Threading proves insufficient for GPU inference — at which point the answer is
likely a separate inference service (see ADR-0001's revisit triggers) rather
than a different concurrency model.

---

## ADR-0007: Explicit composition root instead of a DI framework

**Status:** Accepted · 2026-07-22

### Context

The platform requires dependency injection. The usual options are a container
library (`dependency-injector`, `punq`, `wired`) or explicit construction in
one place.

### Decision

Explicit construction in `qalam.composition.container`. FastAPI's `Depends`
carries the container into handlers.

At the current graph size — one pipeline, six components, one plugin registry —
a container library would add a runtime dependency, a configuration DSL, and
runtime-resolved wiring, while removing the single readable file that answers
"what is actually running in production?". `build_components` is the complete
answer to that question and is roughly fifteen lines.

Note what this replaces: the previous skeleton instantiated its pipeline as a
module-level global at import time, which made it untestable without
monkeypatching. Dependencies now arrive through `Depends` and can be overridden
per-test via `app.dependency_overrides`.

### Consequences

Positive: no magic, no extra dependency, trivially debuggable, and enabling a
capability as models land is a one-line change in one file.

Negative: the container is manually maintained and will grow. If it reaches a
few hundred lines or acquires conditional wiring logic, that is the signal.

### Revisit when

The composition root exceeds ~200 lines, or wiring becomes conditional on
runtime state rather than static configuration.

---

## ADR-0008: Conservative canonicalization separate from lossy folding

**Status:** Accepted · 2026-07-22

### Context

Arabic normalization pipelines conventionally strip diacritics, unify alef
variants, and fold ta marbuta to ha. This raises recall when matching text
against a corpus.

Applied to epigraphy, that convention destroys the product. Vocalization is
meaningful in Quranic and monumental text; `ة` versus `ه` and `ى` versus `ي`
are real orthographic distinctions a scholar will not accept being silently
erased. Worse, *diacritic restoration* is itself a planned platform capability —
a canonical form that discards harakat would be destroying its own training
signal and its own ground truth.

### Decision

Two separate operations on the `CivilizationPlugin` contract:

- **`normalize_text`** (`arabic.canonicalize`) — removes only recognition
  artefacts: presentation forms via NFKC (which also expands ligatures such as
  U+FDF2 `ﷲ` to `الله`), kashida elongation, zero-width and bidi controls, and
  irregular whitespace. **Diacritics are preserved.** This is what is stored,
  displayed, and treated as the reading.
- **`search_key`** (`arabic.fold`) — additionally strips all vocalization,
  unifies alef and hamza seats, folds ta marbuta, and converts Arabic-Indic
  digits. Lossy by design, used only as a corpus-matching key. Never displayed,
  never stored as the reading.

`strip_diacritics` is exposed separately because it produces the undiacritized
side of a diacritic-restoration training pair.

### Consequences

Positive: scholarly fidelity and matching recall are both served, without one
compromising the other. Two texts folding to the same key are *candidates* for
being the same inscription — the platform treats that as a hypothesis to
support with evidence, not a conclusion.

Negative: two functions where most Arabic NLP pipelines have one, and callers
must choose correctly. Enforced by the plugin contract and by
`tests/unit/test_arabic.py`.

### Revisit when

Epigraphers review the folding rules. The current rules are a defensible
starting point, not a validated one — this must be reviewed with a domain
expert before any corpus matching ships, and the outcome recorded in
`RESEARCH_LOG.md`.
