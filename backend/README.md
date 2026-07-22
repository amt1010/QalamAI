# Backend

## Overview

The backend is a FastAPI service that exposes ingestion, OCR, translation, and heritage understanding endpoints.

## Planned modules

- api/: route definitions
- core/: configuration, logging, settings
- models/: Pydantic request/response models
- services/: OCR, translation, knowledge, and pipeline orchestrators

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn pydantic httpx pytest
uvicorn app.main:app --reload
```
