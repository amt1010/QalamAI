# Research Log

**Status:** living document · last updated 2026-07-22

Every technology evaluation is recorded here with the reason it was accepted or
rejected. A rejection with a recorded reason is more valuable than an
acceptance without one — it stops the same option being relitigated every year.

---

## Format

```
### YYYY-MM-DD · <topic>
**Question.** What was being decided.
**Findings.** What was learned.
**Decision.** Accepted / Rejected / Deferred, and why.
**Follow-up.** What remains open.
```

---

## Entries

### 2026-07-22 · Calliar — scope of use

**Question.** Can Calliar serve as a dataset for monument inscription OCR?

**Findings.** Calliar is a dataset of online (stroke-sequence) Arabic
calligraphy, annotated at stroke, character, and word level. Its value is in
annotation methodology, stroke modelling, and script/style classification. It is
digital-pen data, not photographs of carved stone. It shares nothing with the
monument OCR task's actual difficulties: relief carving, weathering, uncontrolled
lighting, perspective distortion, and unconstrained backgrounds.

**Decision.** **Accepted as a research resource** for calligraphy understanding,
annotation methodology, stroke modelling, and script classification.
**Rejected as a monument OCR dataset or benchmark.** Using it to report OCR
accuracy would produce a number that looks like progress and measures nothing
relevant.

**Follow-up.** Its annotation schema is worth studying before designing our own
inscription annotation format (M3).

---

### 2026-07-22 · Service decomposition strategy

**Question.** Split into services now, or modular monolith first?

**Findings.** The platform must eventually support independently deployable
services, especially the HKG. But with no models, no dataset, and no users,
splitting now means freezing interfaces into network contracts before they are
understood. The failure mode worth preventing is boundary rot, not co-location.

**Decision.** **Modular monolith with machine-enforced layering.** Full
reasoning, alternatives, and reversal triggers in ADR-0001.

**Follow-up.** Revisit at the first GPU-resident model or when the HKG acquires
external consumers.

---

### 2026-07-22 · Boundary enforcement mechanism

**Question.** How do layer boundaries survive years of contributors?

**Findings.** Options were code review discipline, package separation, and
static import analysis. Review discipline demonstrably does not survive team
turnover. Package separation works but adds per-package build and release
ceremony. `import-linter` declares contracts in `pyproject.toml` and checks them
in seconds.

**Decision.** **Accepted: import-linter**, with contracts run both in CI and
from pytest so violations fail the command developers already run.

The key insight applied: ordering `application` *below* `adapters` in the layer
stack converts "the orchestrator must not depend on a concrete engine" from a
convention into a build failure.

**Follow-up.** Add a contract per civilization plugin as each is added.

---

### 2026-07-22 · Arabic normalization for epigraphy

**Question.** Should the platform apply standard Arabic NLP normalization?

**Findings.** Conventional Arabic normalization strips diacritics, unifies alef
variants, and folds ta marbuta to ha, raising corpus-matching recall. Applied
here it is actively harmful: vocalization is meaningful in Quranic and
monumental text; `ة`/`ه` and `ى`/`ي` are real orthographic distinctions; and
diacritic restoration is itself a planned capability, so a canonical form that
discards harakat destroys its own ground truth.

Separately, OCR engines frequently emit Arabic Presentation Forms (U+FB50–FDFF,
U+FE70–FEFF). NFKC resolves these and expands ligatures such as U+FDF2 `ﷲ` to
`الله`, which is desirable.

**Decision.** **Rejected: single-function normalization.** **Accepted: two
separate operations** — conservative `canonicalize` (artefacts only, diacritics
preserved) and lossy `fold` (matching key only). See ADR-0008.

**Follow-up.** **The folding rules have not been reviewed by an epigrapher.**
They are a defensible starting point, not a validated one. Review is required
before any corpus matching ships, and the outcome must be recorded here.

---

### 2026-07-22 · Dependency injection approach

**Question.** DI container library, or explicit composition root?

**Findings.** At the current graph size — one pipeline, six components, one
registry — a container library adds a runtime dependency and a configuration DSL
while removing the single readable file answering "what is running in
production?".

**Decision.** **Rejected: `dependency-injector` and similar.** **Accepted:
explicit construction** in `qalam.composition.container`, with FastAPI `Depends`
carrying it to handlers. See ADR-0007.

**Follow-up.** Revisit if the composition root exceeds ~200 lines or wiring
becomes conditional on runtime state.

---

### 2026-07-22 · Python version selection

**Question.** Which Python version, given a future heavy CV/ML dependency tree?

**Findings.** Pre-built wheel availability across PyTorch, ONNX Runtime, and
OpenCV is the binding constraint, not language features. 3.12 has the broadest
coverage; 3.13+ still has ecosystem gaps; 3.11 reaches end of life sooner.

**Decision.** **Accepted: 3.12**, pinned identically in `pyproject.toml` and CI.
See ADR-0002.

**Follow-up.** Re-evaluate when a required ML dependency ships only for a newer
version.

---

### 2026-07-23 · HKG store selection — and a corrected assumption

**Question.** Which store for the Heritage Knowledge Graph: labelled property
graph, RDF/SPARQL, or relational + pgvector?

**Findings.** The previous framing of this question — written by me in the first
draft of `KNOWLEDGE_GRAPH_SCHEMA.md` — listed relational last and described it
as "awkward for deep traversal". Formalizing the ten competency questions and
measuring what each actually requires showed that framing to be wrong:

- **Maximum traversal depth is 3**, and every path is schema-known.
- **Not one of the ten questions requires variable-depth traversal or a graph
  algorithm.** Bounded, known-shape traversals are joins.
- **CQ9 ("show similar inscriptions") is not a graph query at all** — it is
  vector similarity, and it is one of the platform's most distinctive
  capabilities.
- Inscription matching needs three tiers — exact fold, fuzzy string, embedding
  similarity. A graph store natively serves the first two and none of the third.

So a graph database would have been selected for traversal the platform does not
perform, while requiring a second system for the search it does perform.

Separately: reified claims, required for representing scholarly disagreement,
are more natural relationally than in either alternative. In RDF they need
reification or RDF-star; in a property graph, competing claims require parallel
edges or reified nodes anyway — abandoning the graph model in all but name.

**Decision.** **Rejected: Neo4j / property graph** (traversal analysis does not
support it; separate vector store required; Community licensing constraints).
**Rejected: RDF/SPARQL** — a close second, and its named-graph provenance model
is genuinely principled, but its decisive advantage is interoperability, and the
platform is self-contained. **Accepted: PostgreSQL + pgvector + pg_trgm.** See
ADR-0009.

**Follow-up.** The decision is reversible at bounded cost — the reified claim
model is a superset of an attributed edge, and access is confined to one
adapter. Apache AGE is worth evaluating specifically if the variable-depth
trigger fires. **Revisit immediately if the self-contained decision reverses.**

---

### 2026-07-23 · CIDOC CRM

**Question.** Should the HKG be built on CIDOC CRM (ISO 21127)?

**Findings.** CIDOC CRM's central value is a *shared* vocabulary for exchange
between institutions. Its complexity is deliberate and earned at museum scale:
"a monument was built in 1632" requires an `E12 Production` event, `P108 has
produced`, `P4 has time-span`, an `E52 Time-Span`, and `P82 at some time
within`. Without a federation requirement, that cost buys little.

Several of its modelling insights are nonetheless correct and worth taking:
event-centric modelling of construction and conservation; separating a
conceptual work from its physical carriers (`E73` / `E24`), which is
independent prior art for our `InscriptionText` / `InscriptionInstance` split;
time-spans as first-class imprecise objects; attribution as an event with an
actor.

**Decision.** **Rejected as the schema. Accepted as a source of modelling
insight**, with a maintained mapping table for future export. See ADR-0010.

**Follow-up.** Keep the mapping current as the schema evolves — cheap
incrementally, very expensive to reconstruct later.

---

### 2026-07-23 · Representing scholarly disagreement

**Question.** How should the schema represent contested attributions?

**Findings.** Edge properties can hold one answer with a confidence caveat. They
cannot hold "Source A says X, Source B says Y, and the field has not settled
it". Representing that requires either parallel edges or reified nodes.

This matters more than it first appears: presenting a live scholarly dispute as
settled fact is a failure mode that survives every check ADR-0004 and ADR-0005
impose, because each individual statement still traces to a genuine citation.

**Decision.** **Accepted: reified claims** with `source` NOT NULL, no unique
constraint on `(subject, predicate)`, and retrieval that groups competing claims
into a `ClaimSet` flagged consensus / disputed / weak. See ADR-0011.

**Follow-up.** **Consensus scoring is unsolved and blocking.** A naive
highest-confidence-wins rule silently resolves disputes — the exact failure the
model exists to prevent. Source weighting and dispute thresholds are questions
Q4 and Q5 in `EXPERT_REVIEW_BRIEF.md` and must be answered before
implementation.

---

## Open research questions

Not yet investigated. Listed so they are not forgotten.

| # | Question | Blocks | Priority |
|---|----------|--------|----------|
| 1 | What benchmark data exists for Arabic monumental epigraphy OCR? Does a public set exist, or must one be built? | M3 — this is the critical path | **highest** |
| 2 | How do scene-text recognition methods transfer to carved relief with no colour contrast? | M3 | high |
| 3 | Which architectures suit Arabic diacritic restoration, and what supervision do they need? | M4 | medium |
| 4 | ~~Store selection for the HKG~~ | — | **answered** 2026-07-23 → ADR-0009 |
| 5 | ~~How to represent scholarly disagreement~~ | — | **answered** 2026-07-23 → ADR-0011 |
| 5a | How should consensus vs. dispute be *scored* — source weighting and thresholds? Blocking for ADR-0011. | M5 | **highest** |
| 6 | Which heritage data sources are authoritative *and* licensable for this use? | M5 | **highest** |
| 7 | How is generated narrative verified, given ADR-0005 grounds claims but not the prose connecting them? | M6 | high |
| 8 | Offline, hosted, or hybrid translation — what are the accuracy, latency, and data-residency trade-offs for culturally sensitive material? | M4 | medium |
| 9 | Do monumental Arabic inscriptions need script-aware detection, or does generic text detection suffice? | M2 | medium |
| 10 | What annotation schema should inscription datasets use? (Study Calliar's as prior art.) | M3 | high |

Questions 1, 5a, and 6 are sourcing and expert-judgement problems rather than
engineering ones, and are likely to dominate their milestones. They should be
started well before the milestone that formally depends on them.

Questions 1, 5a, and 6 are all posed to a domain expert in
`EXPERT_REVIEW_BRIEF.md` (as Q13, Q4–Q5, and Q13 respectively). Finding a
reviewer is currently the highest-leverage unblocking action available.

---

## Papers and resources to review

Not yet assessed — listed as a reading queue, with no claim about relevance
until each is evaluated and given an entry above.

- Scene text detection and recognition surveys, with attention to non-Latin
  scripts
- Arabic OCR and handwriting recognition literature
- Computer vision applied to cultural heritage and archaeological documentation
- Ancient manuscript restoration and degraded-document enhancement
- Arabic NLP: diacritic restoration, normalization practice, morphology
- Knowledge graph construction for cultural heritage; CIDOC CRM as a possible
  schema foundation for question 4
- Retrieval-augmented generation with attribution and citation-faithfulness
  evaluation
- Graph reasoning over heterogeneous, provenance-annotated data
