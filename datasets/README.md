# Dataset pipeline

This folder contains the initial structure for dataset preparation, augmentation, validation, and benchmarking.

## Directories

- raw/: original images and metadata
- clean/: normalized images
- augmented/: synthetic variants and transformations
- validated/: reviewed and approved samples
- benchmark/: evaluation sets and metrics
- production/: curated production-ready data

## Planned scripts

- clean_images.py
- augment_dataset.py
- validate_dataset.py
- duplicate_detection.py
- dataset_stats.py
- generate_quality_report.py
