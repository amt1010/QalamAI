# Architecture

**Status:** living document · last updated 2026-07-22 (M1)

This describes what exists and what is designed. Sections marked **[planned]**
are not implemented; the distinction is maintained deliberately so this document
can be trusted.

---

## 1. What the platform is

QalamAI understands, preserves, explains, and connects historical inscriptions.
OCR is one subsystem among many, not the product.

The system takes a photograph of a monument and returns: located inscriptions, a
transcription, a translation, and — grounded in a knowledge graph with citations
— an explanation of what the inscription is, who made it, and where else it
appears.

Two properties constrain every decision below:

1. **The platform must never fabricate.** Not a reading, not a translation, not
   a historical claim. (ADR-0004, ADR-0005)
2. **Civilizations are plugins.** Adding Brahmi or Cuneiform must not modify the
   core.

---

## 2. Layered structure

One deployable process, seven layers, checked by `lint-imports` (ADR-0001):

```
┌──────────────────────────────────────────────────────────┐
│ api           HTTP contract, routing, error translation  │
├──────────────────────────────────────────────────────────┤
│ composition   the object graph; the only place where     │
│               interfaces meet implementations            │
├──────────────────────────────────────────────────────────┤
│ adapters      concrete engines, clients, model runtimes  │
├──────────────────────────────────────────────────────────┤
│ application   use cases; orchestrates ports              │
├──────────────────────────────────────────────────────────┤
│ plugins       civilization-specific knowledge            │
├──────────────────────────────────────────────────────────┤
│ domain        entities, value objects, ports             │
├──────────────────────────────────────────────────────────┤
│ core          config, logging, error taxonomy            │
└──────────────────────────────────────────────────────────┘
              imports may only point downward
```

Two placements carry most of the architectural weight:

- **`application` is below `adapters`.** An orchestrator therefore cannot import
  a concrete engine — attempting it fails the build. This is what makes
  "replaceable AI components" a guarantee rather than an intention.
- **`domain` may not import a web framework.** It remains importable from a
  training notebook or a batch job.

### Source map

| Path | Responsibility |
|------|----------------|
| `backend/src/qalam/core/` | `config.py` (typed settings), `logging.py` (structlog), `errors.py` (error taxonomy with stable codes) |
| `backend/src/qalam/domain/` | `value_objects.py`, `entities.py`, `ports.py` |
| `backend/src/qalam/plugins/` | `base.py` (contract + registry), `islamic_epigraphy/` |
| `backend/src/qalam/application/` | `pipeline.py` (the analysis use case), `stage.py` (timing, availability, failure containment) |
| `backend/src/qalam/adapters/` | `unavailable.py` today; real engines land here |
| `backend/src/qalam/composition/` | `container.py` — the whole object graph |
| `backend/src/qalam/api/` | `app.py`, `dependencies.py`, `errors.py`, `v1/` |

---

## 3. Ports — the replaceable components

Declared in `qalam/domain/ports.py` as `Protocol`s. Every one extends
`Capability`, which requires `id`, `is_available`, and `availability_reason` —
so an unconfigured deployment can explain itself precisely.

| Port | Responsibility | Status |
|------|----------------|--------|
| `ImagePreprocessor` | Enhancement, restoration, perspective correction | **[planned]** M2 |
| `InscriptionDetector` | Locate inscription regions | **[planned]** M2 |
| `ScriptClassifier` | Identify writing system, route OCR | **[planned]** M3 |
| `OcrEngine` | Transcribe located regions | **[planned]** M3 |
| `Translator` | Offline / hosted / hybrid translation | **[planned]** M4 |
| `KnowledgeGraphClient` | Retrieve cited evidence from the HKG | **[planned]** M5 |
| `Explainer` | Ground narrative in retrieved evidence | **[planned]** M6 |

All ports are `async` (ADR-0006). CPU-bound adapters must wrap synchronous work
in `asyncio.to_thread`.

**Every one currently resolves to an adapter that declares itself unavailable.**
That is the honest state of the platform, not a gap in the documentation.

---

## 4. The analysis pipeline

`AnalysisPipeline.run` in `application/pipeline.py`:

```
ImageReference
     │
     ├─ preprocess ──────── unavailable? → continue with the original image
     ├─ detect ──────────── none found?  → treat the frame as one region
     ├─ classify_script ─── caller hint wins; else classifier; else plugin default
     ├─ ocr ─────────────── none? → no reading; downstream stages do not run
     │      └─ plugin.normalize_text, drop lines below min_confidence
     ├─ translate
     └─ knowledge_graph ─── evidence → HeritageClaims (never the reverse)
                                  │
                            AnalysisResult
```

Each stage runs through `run_stage`, which records timing and distinguishes four
outcomes:

| Status | Meaning | Operator action |
|--------|---------|-----------------|
| `COMPLETED` | Produced a value | — |
| `SKIPPED` | No component wired; not deployed by design | none |
| `UNAVAILABLE` | Wired but cannot serve — missing weights, unreachable dependency | **actionable** |
| `FAILED` | The component raised; contained and reported | investigate |

Keeping `SKIPPED` and `UNAVAILABLE` distinct matters: "we did not deploy this"
and "this is broken" require different responses, and collapsing them hides
outages.

**No path substitutes a fabricated value for a missing one.**

### Degradation, concretely

- Preprocessing unavailable → analysis proceeds on the unenhanced image.
- Detection unavailable → OCR is still attempted over the whole frame, so
  already-cropped curated material stays analyzable.
- OCR unavailable → no reading. Translation and HKG lookup do not run, because
  there is nothing to translate or look up. `/analyze` returns 503.
- HKG unavailable → transcription and translation are still returned; the
  response simply contains no claims.

---

## 5. The plugin architecture

A `CivilizationPlugin` contributes *knowledge*, not wiring:

```python
id                       # "islamic_epigraphy"
display_name
supported_scripts        # frozenset[Script]
default_script
default_target_language
normalize_text(raw)      # conservative canonical form  (ADR-0008)
search_key(text)         # lossy corpus-matching key    (ADR-0008)
```

Plugins deliberately do **not** construct engines. Wiring is the composition
root's job. That separation is what places `plugins` below `adapters` in the
layer stack, and it is why adding a civilization cannot reach into the core.

Registration is explicit in `build_plugin_registry()`, not discovered by
scanning the path. Explicit registration keeps startup deterministic and
prevents an unvetted package from silently contributing heritage claims.

**Adding a civilization** — the full procedure:

1. Add the scripts to the `Script` enum if absent.
2. Create `qalam/plugins/<civilization>/` implementing `CivilizationPlugin`.
3. Add one line to `build_plugin_registry()`.
4. Add the plugin to the import-linter independence contract.

No change to `domain`, `application`, `api`, or any other plugin. The
independence contract enforces that plugins never import each other.

---

## 6. Grounding: how hallucination is prevented

Not by prompting, and not by validating output after the fact. By making an
unsupported claim unrepresentable (ADR-0005):

```python
@dataclass(frozen=True, slots=True)
class HeritageClaim:
    statement: str
    evidence: tuple[Evidence, ...]   # construction raises if empty
```

`Evidence` carries a `Citation` (title, stable identifier — DOI, ISBN, accession
number, or HKG URI — and kind) plus a `Confidence`. The wire schema mirrors the
constraint with `Field(min_length=1)`.

The pipeline builds claims *from* retrieved evidence. It never generates a
statement and then looks for support. With no evidence there are no claims, and
the platform says nothing about history it cannot source.

---

## 7. HTTP contract (v1)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/health` | Liveness. Dependency-free by design — a model gap must not cause a restart loop. |
| `GET /api/v1/readiness` | Per-capability availability with reasons. Answers "can this deployment read an inscription?" |
| `GET /api/v1/civilizations` | Registered plugins, so clients never hardcode the list. |
| `POST /api/v1/analyze` | Analyze one image. |

Errors share one shape — `{code, message, details}` — with a stable
machine-readable `code`. Clients branch on the code, never the message.

Modes (`tourist`, `research`, `developer`) govern **disclosure only**. The
platform's conclusions are identical across modes; only the depth of surfaced
diagnostics differs. This is asserted by test, not just by convention.

Full detail in [`API_SPECIFICATION.md`](API_SPECIFICATION.md).

---

## 8. Heritage Knowledge Graph **[planned]**

The HKG is a first-class subsystem with its own schema, API, tests, and
deployment. Design work is scheduled for M5 and is the platform's highest-risk
component.

Its seam already exists: the `KnowledgeGraphClient` port. The domain depends on
that port and never on a graph driver, so extracting the HKG into its own
deployable service is an adapter swap plus a deployment change — no domain
change. See [`KNOWLEDGE_GRAPH_SCHEMA.md`](KNOWLEDGE_GRAPH_SCHEMA.md) for the
open questions, which include the store selection (labelled property graph vs.
RDF/SPARQL vs. relational + pgvector) and how provenance, confidence, and
citation are modelled on every relationship.

---

## 9. Mobile client

`mobile/` is a Flutter shell: one screen, no networking, no state management.
Architecture work is scheduled for M7 and is not designed yet. Recording this
plainly rather than describing an intended architecture as though it existed.

---

## 10. Cross-cutting concerns

**Configuration.** All tunables in `core/config.py`, typed, sourced from
`QALAM_`-prefixed environment variables with `__` nesting. `extra="forbid"`, so
a typo in a variable name fails startup rather than silently taking a default.
Notably, `ocr.default_engine` defaults to `"unavailable"` — an unconfigured
deployment fails loudly.

**Logging.** structlog. Every log line is a named event with typed fields
(`stage.completed`, `analysis.finished`, `script.outside_plugin_scope`), so
pipeline behaviour is measurable in aggregate rather than greppable. Console
renderer locally, JSON in deployment.

**Errors.** `QalamError` subclasses carry a stable `code` and HTTP status.
Handlers are registered centrally, so no route needs try/except. Unhandled
exceptions return a deliberately generic message — tracebacks disclose paths,
configuration, and dependency versions — with the detail going to the log.

**Testing.** 80 tests across `unit/`, `integration/`, and `architecture/`. The
architecture tests run import-linter from pytest, so a boundary violation fails
the command a developer already runs. See [`TEST_PLAN.md`](TEST_PLAN.md).

---

## 11. Known gaps

Recorded rather than deferred silently:

| Gap | Impact | Scheduled |
|-----|--------|-----------|
| No lock file; only bounded direct pins | Transitive deps unpinned; builds not bit-reproducible | M2 |
| No authentication or rate limiting | Cannot be exposed publicly | M4 (`SECURITY.md`) |
| No image ingestion — `image_url` is accepted but never fetched | End-to-end flow incomplete; SSRF surface once implemented | M2 |
| Arabic folding rules not reviewed by an epigrapher | Matching recall/precision unvalidated | before corpus matching (ADR-0008) |
| No benchmarks | Performance claims unfounded | M3 (`PERFORMANCE.md`) |
| Mobile app is a shell | No client architecture | M7 |
| HKG entirely undesigned | Highest-risk subsystem | M5 |
