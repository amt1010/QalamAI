# Dataset Manifest

**Status:** living document · last updated 2026-07-22

---

## Current state

**No datasets have been acquired, built, or licensed.**

`datasets/` contains directory documentation only. Stating this plainly because
dataset availability — not model architecture — is this platform's critical
path (see `PROJECT_MASTER_PLAN.md` § Critical path).

---

## Why this document exists before any data

Reproducible experiments and versioned datasets are stated platform principles.
Both require that provenance and licensing be recorded *at acquisition time*.
Data whose origin and licence are reconstructed months later is data that cannot
be safely published, and results computed on it cannot be defended.

For cultural heritage material this is sharper than usual: images of monuments
and inscriptions carry copyright, institutional access agreements, and sometimes
cultural-sensitivity constraints on redistribution. Recording licence terms is
not administrative overhead here.

---

## Required fields per dataset

Every dataset entered below must carry all of these. A dataset missing any of
them may not be used for a published result.

| Field | Why |
|-------|-----|
| `id` | Stable identifier used in `MODEL_REGISTRY.md` |
| `version` | Datasets change; results are meaningless without a version |
| `source` | Where it came from, with URL or institutional contact |
| `licence` | Exact terms, including redistribution and commercial use |
| `acquired` | Date, and by whom |
| `size` | Item count and byte size |
| `content` | What it actually contains |
| `splits` | Train/validation/test with the split *rule*, not just counts |
| `annotation` | Schema, tooling, who annotated, inter-annotator agreement |
| `known_biases` | Geographic, temporal, dynastic, condition, photographic |
| `sensitivity` | Cultural or institutional constraints on use |
| `checksum` | SHA-256 manifest for integrity |

---

## Pipeline stages

The directory structure under `datasets/`:

| Stage | Contents | Entry criteria |
|-------|----------|----------------|
| `raw/` | Original acquisitions, never modified | Provenance and licence recorded |
| `clean/` | Normalized: format, colour space, EXIF stripped | Passes validation |
| `augmented/` | Synthetic variants | Augmentation parameters recorded and reproducible |
| `validated/` | Human-reviewed | Annotation reviewed; agreement measured |
| `benchmark/` | Held-out evaluation sets | **Never** used for training or tuning |
| `production/` | Curated, released | All of the above |

Data is not committed to git (see `.gitignore`). Only manifests, checksums, and
scripts are versioned here. Binary storage will need a decision — DVC,
git-annex, or object storage with a checksum manifest — scheduled for M3.

---

## Benchmark discipline

The benchmark split is the one thing that cannot be recovered once compromised.

- It is defined **before** any model is trained.
- It is **never** used for training, hyperparameter selection, or early stopping.
- Splitting is by **monument**, not by image. Multiple photographs of the same
  inscription across splits leaks, and would make reported accuracy meaningless.
- It must cover the hard cases deliberately: weathered surfaces, oblique angles,
  low contrast, partial occlusion, and multiple calligraphic styles. A benchmark
  of clean, well-lit, frontal photographs will report excellent numbers and
  predict nothing about field performance.

---

## Datasets

*(none yet)*

### Under consideration

| Candidate | Purpose | Status |
|-----------|---------|--------|
| Calliar | Calligraphy understanding, annotation methodology, script classification | **Research resource only.** Explicitly rejected as a monument OCR dataset or benchmark — see `RESEARCH_LOG.md` 2026-07-22 |
| — | Arabic monumental epigraphy benchmark | **Does not exist to our knowledge.** Whether one can be sourced or must be built is open research question #1 and the highest-priority unknown in the project |

---

## Open questions

1. Does any public benchmark exist for Arabic monumental inscription OCR? If
   not, building one becomes a milestone in its own right and should be
   scheduled explicitly rather than absorbed into M3.
2. Which institutions hold licensable photographic archives of Islamic
   monuments, and on what terms?
3. What annotation schema should be used? Calliar's is worth studying as prior
   art (research question #10).
4. Who performs annotation? Arabic epigraphy requires genuine expertise —
   crowdsourcing is not viable for transcription of weathered monumental script.
5. How is versioned binary storage handled — DVC, git-annex, or object storage
   plus checksum manifests?
6. What is the policy for culturally sensitive material that may be licensed for
   research but not for redistribution or public display?
