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

## Open research questions

Not yet investigated. Listed so they are not forgotten.

| # | Question | Blocks | Priority |
|---|----------|--------|----------|
| 1 | What benchmark data exists for Arabic monumental epigraphy OCR? Does a public set exist, or must one be built? | M3 — this is the critical path | **highest** |
| 2 | How do scene-text recognition methods transfer to carved relief with no colour contrast? | M3 | high |
| 3 | Which architectures suit Arabic diacritic restoration, and what supervision do they need? | M4 | medium |
| 4 | Labelled property graph vs. RDF/SPARQL vs. relational+pgvector for the HKG? Near-irreversible once data is loaded. | M5 | **highest** |
| 5 | How should the HKG represent *scholarly disagreement* — contested attribution, dating, provenance — without collapsing it into one confident answer? | M5 | **highest** |
| 6 | Which heritage data sources are authoritative *and* licensable for this use? | M5 | **highest** |
| 7 | How is generated narrative verified, given ADR-0005 grounds claims but not the prose connecting them? | M6 | high |
| 8 | Offline, hosted, or hybrid translation — what are the accuracy, latency, and data-residency trade-offs for culturally sensitive material? | M4 | medium |
| 9 | Do monumental Arabic inscriptions need script-aware detection, or does generic text detection suffice? | M2 | medium |
| 10 | What annotation schema should inscription datasets use? (Study Calliar's as prior art.) | M3 | high |

Questions 1, 4, 5, and 6 are sourcing and research problems rather than
engineering ones, and are likely to dominate their milestones. They should be
started well before the milestone that formally depends on them.

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
