# Datasets

**No datasets have been acquired.** These directories are the pipeline
structure only.

Policy, required provenance fields, licensing rules, and benchmark discipline
are in [`docs/DATASET_MANIFEST.md`](../docs/DATASET_MANIFEST.md) — read it
before adding anything here.

## Stages

| Directory | Contents | Entry criteria |
|-----------|----------|----------------|
| `raw/` | Original acquisitions, never modified | Provenance and licence recorded |
| `clean/` | Normalized format, colour space, EXIF stripped | Passes validation |
| `augmented/` | Synthetic variants | Parameters recorded and reproducible |
| `validated/` | Human-reviewed | Annotation reviewed, agreement measured |
| `benchmark/` | Held-out evaluation sets | **Never** used for training or tuning |
| `production/` | Curated and released | All of the above |

## Rules

- **Data is not committed to git.** Only manifests, checksums, and scripts are
  versioned. See `.gitignore`.
- **Split by monument, not by image.** Multiple photographs of the same
  inscription across splits leaks and makes reported accuracy meaningless.
- **The benchmark split is defined before any model is trained** and is never
  used for training, hyperparameter selection, or early stopping.
- **Record provenance and licence at acquisition time.** Cultural heritage
  imagery carries copyright, institutional agreements, and sometimes
  redistribution restrictions. Reconstructing terms later is not reliable.

## Planned scripts

None written yet. Scheduled for M3 alongside the evaluation harness:
`clean_images.py`, `augment_dataset.py`, `validate_dataset.py`,
`duplicate_detection.py`, `dataset_stats.py`, `generate_quality_report.py`.
