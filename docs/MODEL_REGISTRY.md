# Model Registry

**Status:** living document · last updated 2026-07-22

---

## Current state

**No models have been trained, fine-tuned, or deployed.**

Every capability resolves to an adapter from `qalam.adapters.unavailable`, which
declares the gap rather than returning output (ADR-0004). Live status is at
`GET /api/v1/readiness`.

| Capability | Port | Implementation | Scheduled |
|------------|------|----------------|-----------|
| Image preprocessing | `ImagePreprocessor` | `unavailable:image_preprocessing` | M2 |
| Inscription detection | `InscriptionDetector` | `unavailable:inscription_detection` | M2 |
| Script classification | `ScriptClassifier` | `unavailable:script_classification` | M3 |
| OCR | `OcrEngine` | `unavailable:ocr` | M3 |
| Translation | `Translator` | `unavailable:translation` | M4 |
| Knowledge graph | `KnowledgeGraphClient` | `unavailable:knowledge_graph` | M5 |
| Explanation | `Explainer` | not wired | M6 |

---

## Required fields per model

Every registered model must carry all of these. A model missing any of them may
not be promoted beyond `experimental`.

| Field | Why |
|-------|-----|
| `id` | Matches the adapter's `Capability.id`, so a result traces to a model |
| `version` | Semantic; every retrain increments |
| `port` | Which interface it implements |
| `architecture` | Base model and modifications |
| `training_data` | Dataset `id` **and version** from `DATASET_MANIFEST.md` |
| `training_config` | Hyperparameters, seed, hardware, duration |
| `metrics` | Measured on the **benchmark** split, never on training or validation |
| `artefact` | Storage location and SHA-256 |
| `licence` | Base model licence and any usage restrictions |
| `evaluated` | Date and evaluator |
| `limitations` | Known failure modes, in plain language |
| `status` | `experimental` · `staging` · `production` · `deprecated` |

---

## Reproducibility requirements

A model may not reach `production` unless:

- The training run is reproducible from the recorded config, seed, and dataset
  version.
- The dataset version is pinned and its checksum verified.
- Metrics are computed on the benchmark split, which was never seen during
  training or tuning.
- The artefact checksum matches what is deployed.

Model weights are not committed to git (see `.gitignore`). Only this registry
and checksums are versioned.

---

## Promotion

| Transition | Requires |
|------------|----------|
| → `experimental` | Trained and recorded here |
| → `staging` | Benchmark metrics published; limitations documented |
| → `production` | Reproducibility requirements met; performance budget met (`PERFORMANCE.md`); security review if it consumes untrusted input |
| → `deprecated` | Superseded, with the replacement named |

---

## Metrics policy

**OCR.** Character Error Rate and Word Error Rate. Both must be reported broken
down by condition — surface weathering, viewing angle, calligraphic style —
because an aggregate figure hides exactly the cases that matter in the field.
An engine that reads clean museum plaques perfectly and weathered stone not at
all is a poor engine with a good average.

**Detection.** Precision, recall, and mAP at IoU thresholds. Recall matters more
than precision here: a missed inscription is invisible to the user, whereas a
false positive is discarded downstream by OCR.

**Classification.** Per-class precision and recall, plus the confusion matrix.
Accuracy alone is misleading with imbalanced script distributions.

**Translation.** Automatic metrics (BLEU, chrF) are necessary but insufficient —
they are calibrated on modern prose and will not capture correctness on
Quranic, formulaic, or archaic monumental register. Human evaluation by a
qualified reader is required before `production`.

**Confidence calibration.** Applies to every model. The platform surfaces
confidence to users and uses it to filter output (`ocr.min_confidence`).
Uncalibrated confidence is worse than none, because it invites misplaced trust.
Expected Calibration Error must be measured, not assumed.

---

## Registered models

*(none)*

---

## Open questions

1. Where are artefacts stored, and how are they versioned — MLflow, a model
   registry service, or object storage with checksum manifests?
2. Should experiment tracking be adopted now (MLflow, Weights & Biases) or
   deferred until there is something to track?
3. What is the retraining and re-evaluation cadence once models exist?
4. How is a production model rolled back, and what is the shadow-evaluation
   strategy for a replacement?
5. What is the licence compatibility policy for base models — does a
   non-commercial base model foreclose future platform options?
