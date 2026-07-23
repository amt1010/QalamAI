# Domain Expert Review Brief

**For:** a specialist in Islamic epigraphy, Islamic art and architectural
history, or heritage informatics
**Prepared:** 2026-07-23 · **Estimated time:** 60–90 minutes
**Status:** awaiting a reviewer

---

## What we are asking

We are building a database of historical inscriptions and the monuments that
carry them, which an AI system will query to explain inscriptions to users. We
have designed the data model. **We are not epigraphers, and we need to know
where the model is wrong before we load any data into it.**

This document contains no code and assumes no technical background. Every
question is about your field, not ours. Where a question rests on an assumption
we have made, we have said so explicitly — please attack those assumptions.

Answering "your question #4 is malformed, here is the real distinction" is the
most useful possible response.

---

## Background: what the system does

A user photographs an inscription on a monument. The system reads the Arabic
text, translates it, and explains what it is — which Quranic verse it quotes,
who commissioned the monument, which dynasty built it, which calligraphic style
was used, and where else the same inscription appears.

Two rules constrain the design absolutely:

1. **The system never states anything it cannot attribute to a source.** Every
   assertion it makes carries a citation. If it has no source, it says nothing.
2. **The system must not present disputed attributions as settled.** Where
   scholars disagree, it must show the disagreement rather than pick a winner.

The second rule is the reason for most of the questions below, and it is where
we most need your judgement.

---

## Our core modelling assumptions

### Assumption A — an inscription's *text* and its *carvings* are different things

We store the Basmala once, as a text. We separately store each physical carving
of it — on the Taj Mahal, on a Cairo mosque, on a Delhi tomb — as its own
record with its own calligrapher, style, date, and condition.

This lets us answer "where else does this inscription appear?"

### Assumption B — every relationship is a sourced statement, not a fact

We do not record "the Taj Mahal's architect was X". We record "*Source 1* says
the architect was X, with this degree of confidence" and, separately, "*Source
2* says it was Y". Both are kept. The system reports both and marks the
attribution as disputed.

Nothing enters the database without a source attached.

### Assumption C — only definitional attributes belong to an object

A monument's identity is a property of the monument. Its construction date is
not — dating is frequently argued, so it is recorded as a sourced statement like
any other attribution.

---

## Questions

### On inscription identity

**Q1.** Is Assumption A how epigraphers actually think about inscription
identity? Is "the same inscription text appearing on many monuments" a natural
category in your field, or does it obscure something important?

**Q2.** A weathered inscription is read as a partial match to a known formula —
say, a common foundation formula with several characters illegible. When is that
"the same inscription with damage", and when is it a distinct text that merely
resembles a formula? What evidence would settle it?

*Why we ask:* our matching produces candidates. We need to know what confidence
threshold makes a candidate an assertion, and whether that judgement can be
automated at all or must always be human.

**Q3.** Formulaic inscriptions — Basmala, common invocations, standard
foundation formulas — will appear thousands of times. Is treating them as one
shared text correct, or do epigraphers meaningfully distinguish variants that
we would wrongly merge?

### On sources and disagreement

**Q4.** What makes one source more authoritative than another in this field?
Recency, peer review, primary vs. secondary, the author's standing, the
institution? We need to weight sources, and we would rather use your criteria
than invent our own.

**Q5.** When is an attribution "disputed" versus "settled with a minority
view"? Is there a convention in the field, or is it judged case by case?

*Why we ask:* this is currently the weakest part of our design. If we set the
threshold wrongly in one direction, we present live arguments as facts. In the
other, we hedge on things the field settled a century ago. We do not know how to
set it and would rather ask than guess.

**Q6.** When a source is later corrected or retracted, what should happen to
conclusions previously drawn from it? Is there established practice?

### On the vocabulary

**Q7.** Below is our initial list of relationship types. Is anything **missing**
that matters, **named wrongly** for the field, or **conflating** distinctions
scholars keep separate?

> commissioned by · built by dynasty · located in · constructed during ·
> architectural style · chief architect · associated with event · text of ·
> carved on monument · calligrapher · calligraphic style · dated to ·
> condition · quotes · translation of · theme · genre · member of dynasty ·
> patron of · active during · born · died · graded as · part of place

**Q8.** We treat calligraphic style (Kufic, Thuluth, Naskh, Nastaliq,
Muhaqqaq, Rayhani, …) as a single label per carving. Is that adequate, or do
inscriptions routinely combine styles, or sit between them, in ways a single
label misrepresents?

### On dates

**Q9.** We store dates as a structured range with a calendar and a precision
marker — for example, "circa 1040–1045 AH, Hijri". Does that cover what you
need? Specifically:

- Are Hijri/Gregorian conversions ever contested in ways this hides?
- How are regnal dates, or dates given only by a ruler's reign, best recorded?
- Is "circa" sufficient, or are there finer gradations of uncertainty in use?

### On religious texts

**Q10.** Which edition or orthographic standard of the Quran should we use as
the reference text? Orthographic variation between editions directly affects
whether we correctly match an inscription to a verse.

**Q11.** Hadith gradings are themselves contested between scholars. Should we
record the grading as a sourced statement like any other attribution — meaning
we would show competing gradings side by side — or is there established practice
we should follow instead?

### On sensitivity and sources

**Q12.** Are there categories of material — particular sites, funerary
inscriptions, contested religious content, monuments in conflict zones — that
should not be stored, or should not be publicly displayed, for cultural,
ethical, or safety reasons?

*Why we ask:* we would rather design this constraint in now than discover it
after publication.

**Q13.** Which published corpora, catalogues, or institutional archives would
you consider authoritative for Islamic monumental epigraphy? And do you know
of any existing dataset of *photographs* of inscriptions that is available for
research use?

*Why we ask:* the second question is currently the largest unknown in the whole
project. We do not know whether a suitable image dataset exists or whether one
must be built from scratch, and the answer changes our plans substantially.

### Open floor

**Q14.** What have we not asked about that we should have? What is the mistake
non-specialists reliably make when modelling this material?

---

## What happens with your answers

They become recorded design input. Each is written into our decision records
with attribution, and the schema is revised before any data is loaded. Where an
answer contradicts a decision we have already made, the decision changes — that
is why we are asking before building rather than after.

We are happy to credit your contribution, or to keep it unattributed, as you
prefer.

---

## Reference material

The full technical design is in `KNOWLEDGE_GRAPH_SCHEMA.md` in this repository.
It is not necessary reading for these questions, and it is written for
engineers. If you would prefer a longer non-technical write-up of any section,
we will prepare one.
