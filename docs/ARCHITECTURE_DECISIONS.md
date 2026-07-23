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
| [0009](#adr-0009-postgresql-with-pgvector-as-the-hkg-store) | PostgreSQL with pgvector as the HKG store | Proposed | 2026-07-23 |
| [0010](#adr-0010-borrow-from-cidoc-crm-without-adopting-it) | Borrow from CIDOC CRM without adopting it | Proposed | 2026-07-23 |
| [0011](#adr-0011-reified-claims-instead-of-attributed-relationships) | Reified claims instead of attributed relationships | Proposed | 2026-07-23 |

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

---

## ADR-0009: PostgreSQL with pgvector as the HKG store

**Status:** Proposed · 2026-07-23 · *blocked on domain expert review before
implementation*

### Context

Store selection for the Heritage Knowledge Graph is the closest thing to an
irreversible decision in this project: once data is loaded and ingestion is
built, migration is expensive and risky.

The platform is **self-contained** — it owns its model and does not need to
federate with institutional linked data (decision recorded 2026-07-23). That
removes the strongest argument for RDF.

The previous draft of `KNOWLEDGE_GRAPH_SCHEMA.md` — written by me — framed this
as a three-way choice between a labelled property graph, RDF/SPARQL, and
"relational + pgvector", with the relational option listed last and described as
"awkward for deep traversal". That framing carried an unexamined assumption.

### The assumption, examined

Formalizing the ten competency questions and measuring what each actually
requires produced a result that contradicts the framing:

**Maximum traversal depth is 3. Every path is schema-known. Not one of the ten
questions needs variable-depth traversal or a graph algorithm.**

Graph databases earn their operational complexity on *unbounded* traversal —
shortest path, community detection, "find any connection between A and B". A
bounded, known-shape traversal of depth 3 is a join.

Two further observations:

- **CQ9 ("show similar inscriptions") is not a graph query at all.** It is
  vector similarity, and it is among the platform's most distinctive
  capabilities.
- **Inscription matching needs three tiers in sequence** — exact key, fuzzy
  string, embedding similarity (`KNOWLEDGE_GRAPH_SCHEMA.md` §6). A graph store
  serves the first two; none serves the third natively.

So a graph database would be chosen for traversal the platform does not perform,
while requiring a second system for the search it does perform, plus consistency
between them.

### Decision

**PostgreSQL with `pgvector` and `pg_trgm`.**

- Entities as tables; relationships as reified `claim` rows (ADR-0011).
- Bounded traversals as joins; the deepest is three.
- All three matching tiers in one table, one index set, one round trip.
- `jsonb` for structured historical dates, which resist a `date` column.

### Consequences

Positive:

- One store for graph-shaped data, relational data, and vector search. No
  cross-system consistency problem.
- ACID transactions over claim ingestion and supersession, which matters for a
  corpus whose sources get corrected and retracted.
- Reified claims — the requirement that actually constrains this schema — are
  more natural in relational than in either alternative. In RDF they need
  reification or RDF-star; in a property graph, *competing* claims need parallel
  edges or reified nodes anyway, at which point the graph model has been
  abandoned in all but name.
- Operationally ordinary: backup, replication, monitoring, and hosting are
  solved problems. For a one-developer project this is not a small thing.
- No new query language to learn or to hire for.

Negative, stated plainly:

- **If the out-of-scope questions come into scope, this is the wrong store.**
  Calligrapher influence networks, architectural-vocabulary clustering, and
  arbitrary path-finding between monuments are all variable-depth. They are
  plausible research-mode features. Recursive CTEs can express them, but they
  become painful past a few hops and are hard to optimize.
- No graph algorithm library. Implementing PageRank or community detection over
  SQL is possible and unpleasant.
- Loses the "it's a real knowledge graph" signal that carries weight with some
  academic and institutional audiences. A presentational cost, not a technical
  one, but real if institutional partnerships are later pursued.

### Revisit when

- **Any competency question requiring variable-depth traversal is accepted into
  scope.** This is the primary trigger and should be checked whenever a new
  research-mode feature is proposed.
- Graph algorithms (centrality, clustering, path finding) become a product
  requirement rather than a research curiosity.
- The interoperability decision reverses — if museum or archive federation
  becomes a goal, revisit ADR-0010 and this ADR together.
- Claim-table query performance degrades beyond what indexing and partitioning
  fix at realistic corpus size.

Migration path if triggered: entities and claims export cleanly to nodes and
edges, since the reified claim model is already a superset of an attributed
edge. Access is confined to `KnowledgeGraphClient`, so the blast radius is one
adapter. This is bounded pain, not a rewrite — which is what makes the decision
safe to take now.

### Alternatives rejected

**Labelled property graph (Neo4j, Memgraph).** The reflexive choice, rejected
because the traversal analysis does not support it. Edge properties look like a
natural home for provenance until competing claims are required, at which point
parallel edges or reified nodes are needed anyway. Would additionally require a
second system for vector search. Neo4j Community licensing (GPLv3, no RBAC,
single database) is a further constraint for a platform intended to serve
institutions.

**RDF / SPARQL.** Its strongest argument is interoperability with heritage
linked data and CIDOC CRM — and the platform is self-contained, so that argument
does not apply here. Named graphs are a genuinely principled home for
provenance, which is a real point in its favour and the main reason this is a
close second rather than a clear third. Rejected on cost: reification for
statement-level provenance is verbose, the ecosystem is smaller, operational
maturity is lower, and one developer would be paying a steep learning cost for
interoperability that is not currently wanted. **Revisit immediately if the
interoperability decision reverses.**

**Multi-model (ArangoDB) or Apache AGE.** Considered. AGE adds openCypher to
PostgreSQL and would preserve the single-store advantage — worth revisiting
specifically if the variable-depth trigger fires, since it may make migration
cheaper than a move to Neo4j. Not adopted now because it adds an extension
dependency for traversal the platform does not yet perform.

---

## ADR-0010: Borrow from CIDOC CRM without adopting it

**Status:** Proposed · 2026-07-23

### Context

CIDOC CRM (ISO 21127) is the standard ontology for cultural heritage
information. It is the product of decades of modelling experience and is the
lingua franca for museum and archive data exchange.

The question is whether the HKG should be built on it.

### Decision

**Do not adopt CIDOC CRM as the schema. Borrow its modelling insights, and
maintain a documented mapping for future export.**

The decisive factor is the interoperability decision (2026-07-23): the platform
is self-contained. CIDOC CRM's central value is a *shared* vocabulary — it is
what makes your data legible to other institutions. Without a federation
requirement, adopting it means paying its complexity and receiving little of its
benefit.

Its complexity is not incidental. Modelling "a monument was built in 1632"
requires an `E12 Production` event, `P108 has produced`, `P4 has time-span`, an
`E52 Time-Span`, and `P82 at some time within`. That indirection exists for good
reasons at museum scale, and it would meaningfully slow a one-developer project
building its first schema.

**What is borrowed:**

- **Event-centric modelling.** CIDOC CRM models construction, damage, and
  restoration as events with participants and time-spans rather than as
  attributes of an object. `ConservationEvent` and `HistoricalEvent` follow
  this, and it is the right shape.
- **Separating a conceptual work from its physical carriers.** This is directly
  the `InscriptionText` / `InscriptionInstance` split, and CIDOC CRM's
  `E73 Information Object` / `E24 Physical Human-Made Thing` distinction is
  prior art confirming it.
- **Time-spans as first-class, imprecise things** rather than dates. Reflected
  in the `jsonb` temporal representation.
- **Attribution as an event with an actor**, which is close kin to ADR-0011's
  reified claims.

**What is maintained:** a mapping table from our entities and predicates to
CIDOC CRM classes and properties, kept current as the schema evolves. Cheap to
maintain incrementally; very expensive to reconstruct later.

### Consequences

Positive: a schema sized to the project, shaped by an ontology that has already
made the mistakes. Export to CIDOC CRM stays possible.

Negative: not natively interoperable. If an institutional partnership arrives,
an export layer must be built — the mapping table makes that a project rather
than an excavation. Some academic credibility cost from not using the standard.

### Revisit when

The interoperability decision reverses, an institutional partner requires CIDOC
CRM exchange, or publishing to a heritage linked-data ecosystem becomes a goal.
Revisit alongside ADR-0009.

---

## ADR-0011: Reified claims instead of attributed relationships

**Status:** Proposed · 2026-07-23

### Context

The platform must never present a contested historical attribution as settled
fact. This is a sharper problem than hallucination, and less obvious: every
individual statement can trace to a genuine citation while the *presentation*
still misrepresents the state of scholarship.

The Taj Mahal is the standard illustration. Its principal calligrapher is
attributed to Amanat Khan on the basis of a signature — well supported. Its
chief architect is disputed across sources with no consensus. A system that
renders both as a plain fact with a footnote has misled the reader about the
second.

### Decision

Relationships are not edges with attributes. Every assertion is a first-class
`Claim` row:

```
Claim(subject, predicate, object, source, confidence, asserted_by,
      recorded_at, status, supersedes)
```

with these invariants:

1. `source_id` is `NOT NULL` — a claim without a source cannot exist.
2. `confidence` is `NOT NULL`, constrained to `[0, 1]`.
3. **No unique constraint on `(subject, predicate)`.** Competing claims are
   permitted and expected. That absence is the design, not an oversight.
4. Claims are never deleted, only superseded or retracted.

Retrieval groups claims by predicate into a `ClaimSet` flagged `consensus`,
`disputed`, or `weak`. The API surfaces disputes as disputes.

### Why this rather than edge properties

An edge with a `confidence` property holds one answer with a caveat. It cannot
hold "Source A says X, Source B says Y, and the field has not settled it" —
that requires either parallel edges or reified nodes, which is this decision
arrived at by a longer route.

Note this is the database-level counterpart of `HeritageClaim` refusing
construction without `Evidence` (ADR-0005). The same guarantee is enforced at
both ends: `NOT NULL` in the store, a constructor invariant in the domain.

### Consequences

Positive: scholarly disagreement is representable and cannot be silently
resolved. Full audit trail. Retracted sources can be traced to every dependent
claim. Provenance is structural rather than a convention.

Negative:

- Queries are less direct — every relationship traversal goes through the claim
  table, and CQ10 fans out into several claim lookups. Indexed on
  `(subject_type, subject_id, predicate) WHERE status = 'active'`; batched by
  `monument_context()`.
- **Consensus scoring is a genuine unsolved problem.** A naive
  highest-confidence-wins rule silently resolves disputes, which is exactly the
  failure this ADR exists to prevent. Thresholds and source weighting are open
  questions for domain expert review, and this ADR is not safe to implement
  until they are answered.
- Ingestion is more demanding: every fact needs a source before it can be
  stored. This is intended.

### Revisit when

Never for the invariants. The consensus/dispute *scoring* will change after
expert review — that is expected, and the review outcome should be recorded here
and in `RESEARCH_LOG.md`.
