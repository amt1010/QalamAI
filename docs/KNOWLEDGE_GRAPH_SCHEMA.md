# Heritage Knowledge Graph — Schema

**Status:** living document · **DESIGN NOT STARTED** · last updated 2026-07-22
**Scheduled:** M5

---

## Current state

**The HKG is not designed and not implemented.** This document records what it
must do and the questions that must be answered first. Nothing below is a
decision.

What *does* exist is the seam. `KnowledgeGraphClient` in `qalam/domain/ports.py`
is the only way the platform reaches heritage knowledge; the domain never
touches a graph driver. Extracting the HKG into its own deployable service is
therefore an adapter swap plus a deployment change, not a domain change
(ADR-0001).

```python
class KnowledgeGraphClient(Capability, Protocol):
    async def find_evidence(
        self, *, text: str, script: Script, civilization: str, limit: int = 10
    ) -> tuple[Evidence, ...]: ...
```

Note the return type: **`Evidence`, not claims.** The pipeline builds
`HeritageClaim`s *from* returned evidence. The graph supplies sourced facts; it
never supplies conclusions (ADR-0005).

---

## What it must do

Answer these, always with supporting evidence:

- What monument is this?
- Who commissioned it?
- Which dynasty built it?
- Which calligraphy style is used?
- What does this inscription mean?
- Which Surah contains this verse?
- Where else is this inscription found?
- Which monuments share this inscription?
- Show similar inscriptions.
- Explain this monument like a museum curator.

The last is the hardest. It requires traversing from an inscription to its
monument, patron, dynasty, period, architectural context, and scholarly
literature, then assembling a narrative in which **every statement remains
traceable to a citation**.

---

## Entities to model

Monuments · Inscriptions · Quranic verses · Hadith · Historical figures ·
Dynasties · Empires · Cities · Countries · Calligraphy styles · Calligraphers ·
Religious themes · Historical events · Architectural styles · Conservation
history · Academic references

---

## Non-negotiable: provenance on every relationship

Every relationship carries provenance, confidence, and citation. Not the nodes —
the **edges**.

This is the single most consequential schema requirement, and the one most
likely to be compromised for convenience. It exists because the domain is
genuinely contested:

> The Taj Mahal's principal calligrapher is attributed to Amanat Khan on the
> basis of a signature. That attribution is well supported. The identity of its
> chief architect is disputed across sources, with several candidates and no
> consensus.

A schema storing `monument --architect--> person` as a bare edge cannot
represent that difference. It flattens "well-attested" and "contested" into the
same confident assertion — and the platform would then present a scholarly
dispute as settled fact. That is a subtler form of the failure ADR-0004 and
ADR-0005 exist to prevent, and it is harder to detect because every individual
statement traces to *a* source.

**The schema must represent disagreement between sources, not resolve it.**

---

## Open questions

These must be answered before implementation. Questions 1 and 2 are close to
irreversible once data is loaded.

### 1. Store selection *(highest priority)*

| Option | For | Against |
|--------|-----|---------|
| Labelled property graph (Neo4j, Memgraph) | Natural traversal; properties on edges suit provenance directly | Weaker standards story; less natural fit with existing heritage vocabularies |
| RDF / SPARQL (triple or quad store) | Aligns with CIDOC CRM and existing cultural-heritage linked data; named graphs give provenance a principled home | Reification for edge-level provenance is verbose; steeper learning curve |
| Relational + `pgvector` | One store for graph, relational, and embedding search; operationally simple; already-known technology | Deep traversal is awkward; multi-hop reasoning becomes painful as depth grows |

The decision hinges on question 3 below. If interoperability with existing
heritage linked data matters, RDF's ecosystem advantage may outweigh its
ergonomics.

### 2. Provenance representation

How is edge-level provenance, confidence, and citation modelled — and how are
*competing* claims from different sources represented on the same relationship?
Options include RDF named graphs, RDF-star, edge properties, or reified claim
nodes. This must be settled together with question 1.

### 3. CIDOC CRM

Should the schema build on CIDOC CRM, the ISO standard ontology for cultural
heritage? Adopting it buys interoperability with museum and archive systems and
decades of modelling experience; it costs significant complexity and constrains
the model. Requires evaluation, not assumption.

### 4. Sourcing and licensing

Which sources are authoritative *and* licensable? This is a research and legal
problem likely to dominate M5, and it should start well before the milestone
does.

### 5. Quranic and hadith corpora

Which editions? Quranic text is stable but orthographic conventions vary across
editions, which directly affects matching against `search_key` output (ADR-0008).
Hadith collections vary in both text and grading, and grading is itself
contested — which must be represented, not flattened.

### 6. Inscription matching

Given a folded transcription, how are candidate matches retrieved? Exact key
match, fuzzy string match, embedding similarity, or a combination. What
confidence does a match carry, and how does partial or weathered text affect it?

### 7. Identity and deduplication

The same monument appears under different names, transliterations, and scripts
across sources. What is the entity-resolution strategy, and how are merge
decisions recorded so they can be audited and reversed?

### 8. Temporal modelling

Historical dates are frequently ranges, approximations, or disputed, and may be
recorded in Hijri or Gregorian calendars. Point-in-time modelling is
insufficient.

### 9. Ingestion and update

How is data ingested, validated, and updated? What happens when a source is
corrected or retracted — do dependent claims update, and is there an audit
trail?

### 10. Write access and governance

Who may write to the graph? Is there a curation workflow, and how are
corrections from domain experts incorporated?

---

## Constraints already fixed

Regardless of how the questions above resolve:

- The graph returns **evidence**, never conclusions.
- Every relationship carries provenance, confidence, and citation.
- Contested claims are representable as contested.
- Access is exclusively through `KnowledgeGraphClient`; no other layer touches
  a graph driver.
- The subsystem is independently deployable, with its own schema
  documentation, API specification, tests, and deployment.

---

## Next step

Before any implementation: answer questions 1, 2, and 3 and record the outcome
as an ADR, then review the schema with a domain expert in Islamic epigraphy and
heritage informatics. Store selection made without that review is the highest
irreversible risk in the project.
