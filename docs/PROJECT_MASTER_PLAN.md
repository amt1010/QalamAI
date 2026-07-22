# Project Master Plan

**Status:** living document · last updated 2026-07-22

---

## Vision

QalamAI is a Heritage Intelligence Platform: a system for understanding,
preserving, explaining, and connecting historical inscriptions through computer
vision, AI, knowledge graphs, and retrieval-augmented generation.

The first supported civilization is Islamic epigraphy. The architecture is
plugin-based so further traditions — Sanskrit, Brahmi, Persian, Ottoman Turkish,
Hebrew, Greek, Latin, Tamil, Pali, Egyptian hieroglyphs, Cuneiform — can be
added without modifying the platform core.

OCR is one subsystem. It is not the product.

---

## Non-negotiable principles

These are constraints, not preferences. Each is enforced by code or CI, not by
convention.

| Principle | Enforcement |
|-----------|-------------|
| The platform never fabricates a reading, translation, or historical claim | `adapters/unavailable.py`, 503 on no reading (ADR-0004) |
| Every historical claim carries verifiable evidence | `HeritageClaim` raises without it (ADR-0005) |
| AI components are replaceable | `application` cannot import `adapters`; import-linter (ADR-0001) |
| Civilizations are plugins | Plugin independence contract; adding one touches no core file |
| Scholarly fidelity beats matching convenience | Canonicalization separate from folding (ADR-0008) |
| Configuration over hardcoding | `core/config.py`, `extra="forbid"` |
| Strong typing | `mypy --strict`, zero errors, CI-gated |

---

## Milestones

A milestone is complete only when it satisfies the Definition of Done below.
Work does not begin on the next milestone until the current one is reviewed.

### M1 — Architecture and contracts ✅ **complete** (2026-07-22)

Establish the foundation the platform is built on.

- Layered modular monolith with machine-enforced boundaries
- Domain model: entities, value objects, ports
- Plugin contract and registry; Islamic epigraphy plugin with real Arabic
  orthographic handling
- Analysis pipeline with graceful, honest degradation
- HTTP contract v1: health, readiness, civilizations, analyze
- Version control, dependency manifest, environment parity with CI
- Tooling gate: ruff, `mypy --strict`, import-linter, pytest
- Governance documents

**Delivered:** 80 tests passing, 3 architecture contracts holding, 0 lint
errors, 0 type errors.

**Deliberately not delivered:** any trained model. Every capability reports
itself unavailable. This is the honest state and is visible at `/readiness`.

---

### M2 — Image ingestion and preprocessing

**Objective.** Turn `image_url` from an accepted string into a fetched,
validated, enhanced image.

**Scope.** Ingestion adapter (fetch, content-type and size validation, SHA-256
hashing, storage abstraction). Preprocessing: denoising, contrast enhancement,
perspective correction. `ImagePreprocessor` adapter replacing the unavailable
one.

**Risks.**
- *SSRF.* Accepting a URL and fetching it server-side is a textbook SSRF vector
  — internal metadata endpoints, localhost services, redirect chains. Requires
  an allowlist and blocked private ranges before this ships. Blocking; see
  `SECURITY.md`.
- *Decompression bombs and malformed images.* Size and dimension caps required.
- Weathered stone with low contrast is the actual hard case; synthetic test
  images will overstate quality.

**Also in scope.** Dependency lock file (ADR-0002 gap).

**Definition of Done additions.** Benchmark: enhancement quality on a held-out
set of real monument photographs, not synthetic ones.

---

### M3 — Script classification and Arabic OCR

**Objective.** Produce a real transcription.

**Scope.** `ScriptClassifier` and `OcrEngine` adapters. Engine evaluation and
selection, recorded with accept/reject reasoning in `RESEARCH_LOG.md`.
Evaluation harness with CER/WER against a held-out benchmark set.

**Risks.**
- Monumental Arabic epigraphy is far from printed-text OCR: carved relief,
  weathering, extreme calligraphic styles, curved baselines, no clean
  background. Off-the-shelf engines will underperform badly, and the gap must be
  measured rather than assumed.
- Benchmark data does not exist yet and is the true bottleneck. Dataset work is
  the critical path, not model selection.
- Calliar is a research resource for calligraphy understanding, annotation
  methodology, stroke modelling, and script classification — **not** a monument
  OCR dataset. It must not be used as a benchmark for this task.

**Definition of Done additions.** Published CER/WER baseline; a documented
decision on whether off-the-shelf OCR is viable or fine-tuning is required.

---

### M4 — Translation and diacritic restoration

**Objective.** Turn a transcription into meaning.

**Scope.** `Translator` adapter (offline / hosted / hybrid trade-off documented).
Diacritic restoration model — `strip_diacritics` already produces the
undiacritized side of training pairs. Authentication and rate limiting, without
which the platform cannot be publicly exposed.

**Risks.** General-purpose translation models are trained on modern prose and
will mistranslate Quranic, formulaic, and archaic monumental register. A hosted
model creates a data-residency question for material that may be culturally
sensitive.

---

### M5 — Heritage Knowledge Graph

**Objective.** The platform's highest-risk and highest-value subsystem.

**Scope.** Entity and relationship model; store selection (labelled property
graph vs. RDF/SPARQL vs. relational + pgvector) as an ADR; provenance,
confidence, and citation on every relationship; ingestion pipeline; query API;
`KnowledgeGraphClient` adapter. Independently deployable per ADR-0001.

Entities to model: monuments, inscriptions, Quranic verses, hadith, historical
figures, dynasties, empires, cities, countries, calligraphy styles,
calligraphers, religious themes, historical events, architectural styles,
conservation history, academic references.

**Risks.**
- Sourcing authoritative, licensable heritage data is a research and legal
  problem, not an engineering one. It is likely to dominate this milestone.
- Contested history: attribution, dating, and provenance are frequently disputed
  in the literature. The schema must represent *disagreement between sources*,
  not collapse it into a single confident answer.
- Store selection is close to irreversible once data is loaded.

**Definition of Done additions.** Schema review with a domain expert; a
documented answer for how conflicting scholarly claims are represented.

---

### M6 — Grounded explanation (RAG)

**Objective.** Museum-curator-quality explanation that cannot hallucinate.

**Scope.** `Explainer` adapter over HKG retrieval. Explainability surfaces —
every statement traceable to its evidence. Research, tourist, and developer
presentation.

**Risks.** This is where hallucination pressure is highest. ADR-0005 makes an
unsupported claim unrepresentable in the domain, but the *narrative text* an LLM
produces around sourced claims still needs its own verification strategy —
grounding the claims does not automatically ground the prose that connects them.
This needs to be designed, not assumed.

**Definition of Done additions.** An adversarial evaluation set specifically
probing for unsupported assertions in generated narrative.

---

### M7 — Mobile client

**Objective.** Replace the Flutter shell with a real client.

**Scope.** Client architecture, camera capture, offline mode, translation
overlay, history, the three user modes. Must communicate unavailable
capabilities honestly rather than hiding them.

---

### M8 — Deployment, observability, and scale

**Objective.** Run it for real.

**Scope.** Containerization, deployment pipeline, metrics and tracing, alerting,
performance baselines in `PERFORMANCE.md`, load testing. Extraction of the HKG
and inference into separate services if ADR-0001's revisit triggers have fired.

---

## Definition of Done

A milestone is complete only when **all** of the following hold:

- [ ] Production code implemented — no placeholders, no stubs returning
      plausible data
- [ ] Unit, integration, and regression tests pass
- [ ] `ruff check`, `ruff format --check`, `mypy --strict`, and `lint-imports`
      all pass
- [ ] Benchmarks run and recorded in `PERFORMANCE.md`
- [ ] Documentation updated, including the **Known gaps** table in
      `ARCHITECTURE.md`
- [ ] ADRs written for every significant decision, including rejected
      alternatives and reversal triggers
- [ ] Security implications documented in `SECURITY.md`
- [ ] Research findings and technology accept/reject reasoning recorded in
      `RESEARCH_LOG.md`
- [ ] `CHANGELOG.md` updated
- [ ] Future improvements recorded rather than silently dropped

---

## Critical path

The bottleneck is **not** model architecture. It is data:

```
benchmark dataset  →  measurable OCR quality  →  everything downstream
authoritative HKG sources  →  grounded claims  →  the platform's actual value
```

Both are sourcing, licensing, and annotation problems. They should start well
before the milestone that formally depends on them. Dataset work for M3 and
source identification for M5 are the two things most worth starting early.

---

## Living documents

| Document | Purpose |
|----------|---------|
| `PROJECT_MASTER_PLAN.md` | This file — vision, milestones, definition of done |
| `ARCHITECTURE.md` | Current system design, with planned work marked |
| `ARCHITECTURE_DECISIONS.md` | ADRs with rationale and reversal triggers |
| `RESEARCH_LOG.md` | Papers, benchmarks, technologies — accepted and rejected |
| `DATASET_MANIFEST.md` | Dataset provenance, licensing, versions, splits |
| `MODEL_REGISTRY.md` | Model versions, training runs, metrics, lineage |
| `KNOWLEDGE_GRAPH_SCHEMA.md` | HKG entities, relationships, provenance model |
| `API_SPECIFICATION.md` | HTTP contract |
| `SECURITY.md` | Threat model, controls, open risks |
| `PERFORMANCE.md` | Benchmarks, budgets, measurements |
| `TEST_PLAN.md` | Test strategy and coverage policy |
| `CHANGELOG.md` | Notable changes per release |
