# Heritage Knowledge Graph — Schema Design

**Status:** design proposal · **awaiting domain expert review** · 2026-07-23
**Milestone:** M5 (pulled forward ahead of M2 — see `PROJECT_MASTER_PLAN.md`)

> ⚠️ **Not reviewed by a domain expert.** Every modelling decision below is
> made against published scholarly practice by an engineer, not an epigrapher.
> Expert review is a **blocking gate before any data is loaded** — not before
> design proceeds. Questions for that review are in
> [`EXPERT_REVIEW_BRIEF.md`](EXPERT_REVIEW_BRIEF.md).

---

## 1. Competency questions

A schema is only evaluable against the questions it must answer. These are the
acceptance criteria for everything below; each is tagged with the traversal it
requires.

| # | Question | Traversal | Depth |
|---|----------|-----------|-------|
| CQ1 | What monument is this? | `InscriptionInstance → Monument` | 1 |
| CQ2 | Who commissioned it? | `Monument →(commissioned_by) Person` | 1 |
| CQ3 | Which dynasty built it? | `Monument →(patron) Person →(member_of) Dynasty` | 2 |
| CQ4 | Which calligraphy style is used? | `InscriptionInstance →(style) CalligraphyStyle` | 1 |
| CQ5 | What does this inscription mean? | `InscriptionText →(translation)` | 1 |
| CQ6 | Which Surah contains this verse? | `InscriptionText →(quotes) Ayah →(part_of) Surah` | 2 |
| CQ7 | Where else is this inscription found? | `InscriptionText ←(text_of) Instances →(on) Monuments` | 2 |
| CQ8 | Which monuments share this inscription? | same as CQ7 | 2 |
| CQ9 | Show similar inscriptions | vector similarity over embeddings | **0** |
| CQ10 | Explain this monument like a curator | fan-out of CQ2–CQ8 plus references | ≤3 |

### The finding that drives store selection

**Maximum traversal depth is 3. Every path is schema-known. None of the ten
questions requires variable-depth traversal or a graph algorithm.**

This matters because it contradicts the reflex — mine included, in the previous
draft of this document — that "knowledge graph" implies "graph database". Graph
databases earn their complexity on *unbounded* traversal: shortest path,
community detection, PageRank, "find any connection between A and B". QalamAI
asks none of those. It asks a fixed set of bounded, known-shape questions, which
in relational terms are joins.

Meanwhile CQ9 — arguably the platform's most distinctive capability — is not a
graph query at all. It is vector similarity.

See **ADR-0009** for what this implies.

### Questions deliberately out of scope for v1

Recorded so their absence is a decision rather than an oversight:

- "Which calligraphers influenced whom?" — an influence network, genuinely
  variable-depth. Plausible research-mode feature; a reversal trigger in
  ADR-0009.
- "Which dynasties share architectural vocabulary?" — clustering.
- "What connects these two monuments?" — arbitrary path finding.

---

## 2. The two modelling decisions that shape everything

### 2.1 `InscriptionText` is separate from `InscriptionInstance`

An inscription is two different things, and conflating them makes CQ7 and CQ8
unanswerable.

- **`InscriptionText`** — the *content*. The Basmala is one text. Al-Fatiha is
  one text. A foundation inscription's wording is one text.
- **`InscriptionInstance`** — one *physical carving* on one monument. Its own
  condition, calligrapher, style, date, position, and state of preservation.

The Basmala appears on thousands of monuments. That is one `InscriptionText`
and thousands of `InscriptionInstance`s. "Where else is this inscription found?"
is: read an instance → resolve its text → find the text's other instances.

Collapsing these into one entity would force either duplicate text rows per
monument (breaking CQ7 entirely) or losing per-carving attributes such as
calligrapher and condition.

### 2.2 Relationships are reified as `Claim`s

Relationships are **not** edges with attributes. Every assertion is a
first-class `Claim` row:

```
Claim(subject, predicate, object, source, confidence, asserted_by, recorded_at)
```

The reason is the requirement that most constrains this schema: **the platform
must represent scholarly disagreement without resolving it.**

Consider:

> The Taj Mahal's principal calligrapher is attributed to Amanat Khan on the
> basis of his signature — well supported. Its chief architect is disputed
> across sources, with several named candidates and no consensus.

A model storing `monument --architect--> person` as an edge can hold *one*
answer. Storing it as an edge with a confidence property can hold one answer
with a caveat. Neither can represent "Source A says Ustad Ahmad Lahauri, Source
B says Ustad Isa, and the field has not settled it."

Reified claims can:

| subject | predicate | object | source | confidence |
|---------|-----------|--------|--------|-----------|
| Taj Mahal | `chief_architect` | Ustad Ahmad Lahauri | Ref-1 | 0.55 |
| Taj Mahal | `chief_architect` | Ustad Isa | Ref-2 | 0.35 |
| Taj Mahal | `principal_calligrapher` | Amanat Khan | Ref-3 | 0.95 |

The platform returns **all** competing claims with their sources. Presenting a
live scholarly dispute as settled fact is a subtler cousin of the failure
ADR-0004 and ADR-0005 exist to prevent — and more dangerous, because each
individual statement still traces to a real citation.

Formalized as **ADR-0011**.

---

## 3. Entity model

Entities carry only **intrinsic, uncontested** attributes — identity, and
properties that are definitional rather than interpretive. Everything
interpretive is a `Claim`.

That line is the schema's main discipline. A monument's `id` is intrinsic. Its
construction date is *interpretive* and belongs in a claim, because dating is
frequently disputed.

### Core entities

| Entity | Intrinsic attributes | Notes |
|--------|---------------------|-------|
| `Monument` | `id`, `preferred_name`, `names[]` (multilingual, transliterations) | Location and dates are claims — both are contested for many sites |
| `InscriptionText` | `id`, `canonical_text`, `search_key`, `script`, `language` | `canonical_text` and `search_key` come from the civilization plugin (ADR-0008) |
| `InscriptionInstance` | `id`, `monument_id`, `position_description` | The physical carving |
| `TextualSource` | `id`, `kind` (`quran` \| `hadith` \| `poetry` \| `other`), `reference` | Canonical religious/literary text |
| `Ayah` | `id`, `surah_number`, `ayah_number`, `text` | Subtype of `TextualSource`; stable identity |
| `Hadith` | `id`, `collection`, `number`, `text` | Grading is **contested** → claim, not attribute |
| `Person` | `id`, `preferred_name`, `names[]` | Roles (calligrapher, patron, architect) are claims, not types — the same person may hold several |
| `Dynasty` | `id`, `name` | Reign span is a claim |
| `Polity` | `id`, `name`, `kind` (empire \| sultanate \| …) | |
| `Place` | `id`, `name`, `kind`, `parent_id` | Hierarchical: city → region → country |
| `CalligraphyStyle` | `id`, `name` | Kufic, Thuluth, Naskh, Nastaliq, Muhaqqaq, Rayhani, … |
| `ArchitecturalStyle` | `id`, `name` | |
| `HistoricalEvent` | `id`, `name` | Dating is a claim |
| `ReligiousTheme` | `id`, `name` | |
| `ConservationEvent` | `id`, `instance_id` or `monument_id`, `kind` | Restoration, damage, relocation |
| `Reference` | `id`, `citation_type`, `title`, `identifier`, `authors[]`, `year`, `url` | The source of claims; maps to `domain.Citation` |

### Why `Person` has no `role` column

A calligrapher who was also a patron would need two rows, or a multi-valued type
that queries poorly. More importantly, "X was the calligrapher of Y" is exactly
the kind of statement that gets disputed — so it is a claim about a
relationship, not a property of a person.

---

## 4. The claim model

```
Claim
├── id
├── subject_type, subject_id      polymorphic reference
├── predicate                     controlled vocabulary
├── object_type, object_id        for entity-valued claims
├── object_literal                for value-valued claims (dates, text)
├── source_id            → Reference        (required)
├── confidence           0.0–1.0            (required)
├── asserted_by                   who recorded it: ingestion run, curator
├── recorded_at
├── status               active | superseded | retracted
├── supersedes_id        → Claim            (nullable)
└── note                          free text shown as the claim statement
```

### Invariants

1. **`source_id` is NOT NULL.** A claim without a source cannot exist. This is
   the database-level counterpart of `HeritageClaim` refusing construction
   without `Evidence` (ADR-0005) — the guarantee holds at both ends.
2. **`confidence` is NOT NULL** and constrained to `[0, 1]`.
3. **Competing claims are permitted and expected.** No unique constraint on
   `(subject, predicate)`. That absence is the design.
4. **Claims are never deleted**, only superseded or retracted, preserving the
   audit trail a retracted source requires.

### Predicate vocabulary (initial)

Controlled, versioned, and extended only deliberately — a free-text predicate
column becomes unqueryable within a year.

```
Monument:     commissioned_by · built_by_dynasty · located_in · constructed_during
              · architectural_style · chief_architect · associated_event
Instance:     text_of · on_monument · calligrapher · style · dated_to · condition
Text:         quotes · translation_of · theme · genre
Person:       member_of · patron_of · active_during · born · died
Hadith:       graded_as
Place:        part_of
```

### Consensus vs. dispute

The API must distinguish "the field agrees" from "the field is split". A derived
view computes, per `(subject, predicate)`:

- `consensus` — a single claim clearly dominant on source weight and confidence
- `disputed` — multiple claims above a materiality threshold
- `weak` — only low-confidence support

**Tourist mode** surfaces consensus and says "attribution is disputed" where it
is not. **Research mode** returns every competing claim with sources. The
platform's *conclusions* are identical either way; only disclosure differs,
consistent with the existing mode contract.

The exact thresholds are a **question for expert review** — a naive
highest-confidence-wins rule would silently resolve disputes, which is the
failure this whole model exists to prevent.

---

## 5. Physical schema sketch

PostgreSQL, per ADR-0009.

```sql
CREATE TABLE reference (
    id            uuid PRIMARY KEY,
    citation_type text NOT NULL,           -- academic_publication | primary_source | …
    title         text NOT NULL,
    identifier    text NOT NULL UNIQUE,    -- DOI, ISBN, accession no., URI
    authors       text[] NOT NULL DEFAULT '{}',
    year          int,
    url           text
);

CREATE TABLE inscription_text (
    id             uuid PRIMARY KEY,
    canonical_text text NOT NULL,          -- diacritics preserved  (ADR-0008)
    search_key     text NOT NULL,          -- lossy fold            (ADR-0008)
    script         text NOT NULL,
    language       text,
    embedding      vector(768)             -- pgvector, for CQ9
);
CREATE INDEX ON inscription_text (search_key);
CREATE INDEX ON inscription_text USING hnsw (embedding vector_cosine_ops);

CREATE TABLE claim (
    id             uuid PRIMARY KEY,
    subject_type   text NOT NULL,
    subject_id     uuid NOT NULL,
    predicate      text NOT NULL REFERENCES predicate(name),
    object_type    text,
    object_id      uuid,
    object_literal jsonb,
    source_id      uuid NOT NULL REFERENCES reference(id),   -- ADR-0005
    confidence     real NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    asserted_by    text NOT NULL,
    recorded_at    timestamptz NOT NULL DEFAULT now(),
    status         text NOT NULL DEFAULT 'active',
    supersedes_id  uuid REFERENCES claim(id),
    note           text,

    CHECK (object_id IS NOT NULL OR object_literal IS NOT NULL)
);
CREATE INDEX ON claim (subject_type, subject_id, predicate) WHERE status = 'active';
```

Note there is **no unique constraint** on `(subject_type, subject_id,
predicate)`. Competing claims are the point.

`object_literal` as `jsonb` handles the temporal problem: historical dates are
ranges, approximations, disputed, and may be Hijri or Gregorian. A `date` column
cannot express "circa 1042 AH, disputed". Structured JSON can:

```json
{ "calendar": "hijri", "start": 1040, "end": 1045, "precision": "circa" }
```

**Open question for review:** whether this is sufficient, or whether historical
dating needs its own table with explicit calendar conversion. Flagged in the
review brief.

---

## 6. Inscription matching (CQ7, CQ8, CQ9)

How a transcription becomes a graph entry point. Three tiers, in order:

1. **Exact `search_key` match** — the plugin's lossy fold (ADR-0008). Cheap,
   indexed, high precision. Handles the common case where a well-read
   inscription is a known formula.
2. **Trigram / fuzzy match on `search_key`** — for weathered or partial
   readings where OCR dropped characters. `pg_trgm`, same table.
3. **Embedding similarity** — semantic match for paraphrase and heavy damage,
   and the mechanism behind CQ9. `pgvector` HNSW index.

All three live in one table in one database, queried in one round trip. Under a
separate graph store, tier 3 would require a second system and a consistency
problem between them. This is a substantial part of ADR-0009's argument.

**A match is a hypothesis, not a conclusion.** Two texts folding to the same key
are *candidates* for being the same inscription. A match produces `Evidence`
with a confidence reflecting which tier matched — never an asserted identity.

---

## 7. What the port becomes

The current `KnowledgeGraphClient` has one method and will not survive contact
with these queries:

```python
async def find_evidence(self, *, text, script, civilization, limit) -> tuple[Evidence, ...]
```

Proposed (implementation deferred until this design is signed off):

```python
async def match_inscription(text, script, *, limit) -> tuple[InscriptionMatch, ...]
    """Tiered matching. Returns candidates with match tier and confidence."""

async def claims_about(subject_type, subject_id, *, predicates=None) -> tuple[ClaimSet, ...]
    """All active claims, grouped by predicate, each group flagged
    consensus | disputed | weak. Never collapses competing claims."""

async def monument_context(monument_id) -> MonumentContext
    """CQ10 in one call — the curator fan-out, batched rather than
    N round trips from the explainer."""

async def similar_inscriptions(text_id, *, limit) -> tuple[InscriptionMatch, ...]
    """CQ9."""
```

`ClaimSet` — a predicate plus its competing claims and a dispute flag — is the
type that carries scholarly disagreement into the domain. It needs to exist
before `Explainer` is built, or the explainer will flatten disputes by default.

---

## 8. Open questions for expert review

Blocking before data loading. Full context in
[`EXPERT_REVIEW_BRIEF.md`](EXPERT_REVIEW_BRIEF.md).

| # | Question |
|---|----------|
| 1 | Is the `InscriptionText` / `InscriptionInstance` split how epigraphers actually think about inscription identity? |
| 2 | When is a partially-weathered reading "the same inscription" as a known formula, and when is it a distinct text? |
| 3 | What determines source weight — recency, peer review, primary vs. secondary, author standing? |
| 4 | At what point is an attribution "disputed" rather than "settled with a minority view"? |
| 5 | Is the predicate vocabulary complete and correctly named for the field? |
| 6 | Is structured JSON adequate for historical dating, including Hijri/Gregorian and disputed ranges? |
| 7 | Which Quran edition, given orthographic variation affects `search_key` matching? |
| 8 | How should contested hadith gradings be represented? |
| 9 | Are there categories of culturally sensitive material that must not be stored or displayed at all? |
| 10 | Which sources are authoritative *and* licensable? |

---

## 9. Constraints that hold regardless of review

- The graph returns **evidence and claims, never conclusions**.
- Every claim carries provenance, confidence, and citation — enforced by
  `NOT NULL`, not by convention.
- Contested claims are representable as contested, and are never silently
  resolved.
- Access is exclusively through `KnowledgeGraphClient`.
- The subsystem is independently deployable (ADR-0001).

---

## 10. Status and next step

**Design proposal. Not approved. Not implemented.**

Sequence from here:

1. Domain expert review against `EXPERT_REVIEW_BRIEF.md` ← **blocking gate**
2. Revise this schema from review findings
3. Source identification and licensing (open research question #6)
4. Implement schema, ingestion, and adapter
5. Populate — *only* after 1–3

Implementation before step 1 would mean building on ten unvalidated assumptions
about a field neither of us is trained in.
