# Architecture Overview

## System goals

Qalam AI is designed as a layered platform with clearly separated concerns:

- Camera and image intake
- Computer vision preprocessing and inscription detection
- OCR and language understanding
- Translation and heritage explanation
- User-facing mobile experience

## Proposed modules

1. Image intake and preprocessing
2. OCR pipeline with interchangeable engines
3. Translation and knowledge services
4. Mobile client with offline/online modes
5. Dataset and annotation pipeline

## Design principles

- Replaceable models behind interfaces
- Configuration over hardcoding
- Structured logging and benchmark tracking
- Strong typing and testability
- Incremental milestone delivery

## Milestone plan

- M1: API contracts, backend skeleton, mobile shell
- M2: image preprocessing and detection interfaces
- M3: OCR/translation engine abstractions
- M4: dataset pipeline and evaluation harness
- M5: deployment and observability
