# API Specification

**Version:** v1 · **Status:** living document · last updated 2026-07-22
**Base path:** `/api/v1` · **OpenAPI:** `GET /openapi.json` (generated, authoritative)

This document explains the contract's *intent*. The generated OpenAPI schema is
authoritative for exact field types.

---

## Principles

**Versioned by URL prefix.** Breaking changes ship as `/api/v2` alongside a
still-running v1. Museum kiosks and third-party integrations cannot be expected
to upgrade in step with the platform.

**Errors have stable codes.** Every error is `{code, message, details}`. Clients
branch on `code`; `message` is free to change without breaking compatibility.

**Absence means absence.** A field that is `null` or missing means the stage
produced nothing. Fields are never populated with defaults or plausible
substitutes (ADR-0004).

**Modes govern disclosure, not substance.** `tourist`, `research`, and
`developer` change how much is surfaced, never what the platform concluded.

---

## Authentication

**None.** *(planned: M4)*

The API is currently unauthenticated and unrate-limited, and must not be
exposed publicly. See `SECURITY.md`.

---

## `GET /api/v1/health`

Liveness probe.

```json
{ "status": "ok" }
```

Always `200` while the process is running. **Deliberately dependency-free** — it
does not check models, the knowledge graph, or any downstream service. A
liveness probe that fails because a model is missing causes orchestrators to
restart healthy processes they cannot fix.

For capability status, use `/readiness`.

---

## `GET /api/v1/readiness`

Reports which pipeline capabilities this deployment can actually serve.
`/health` answers "is the process up?"; this answers "can it read an
inscription?" — different questions with different responses.

**200**

```json
{
  "ready": false,
  "environment": "local",
  "version": "0.1.0",
  "capabilities": [
    {
      "name": "ocr",
      "available": false,
      "implementation_id": "unavailable:ocr",
      "reason": "No OCR engine is configured; set QALAM_OCR__DEFAULT_ENGINE. (scheduled: M3)"
    }
  ]
}
```

`ready` is true only when every capability is available. Each `reason` is
written to be actionable by an operator.

**Current state:** every capability reports `available: false`. No models have
been trained or shipped.

---

## `GET /api/v1/civilizations`

Registered civilization plugins. Clients should populate selectors from this
rather than hardcoding a list that goes stale when a new tradition ships.

**200**

```json
[
  {
    "id": "islamic_epigraphy",
    "display_name": "Islamic Epigraphy",
    "supported_scripts": ["arabic", "ottoman_turkish", "persian"],
    "default_script": "arabic",
    "default_target_language": "en"
  }
]
```

---

## `POST /api/v1/analyze`

Analyze one inscription image.

### Request

```json
{
  "image_url": "https://example.org/monument.jpg",
  "mode": "tourist",
  "civilization": "islamic_epigraphy",
  "script_hint": "arabic",
  "content_type": "image/jpeg",
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `image_url` | yes | 1–2048 chars. **[planned]** Not yet fetched — see Current limitations. |
| `mode` | no | `tourist` (default) · `research` · `developer` |
| `civilization` | no | Plugin id. Omit for the server default. `404` if unknown. |
| `script_hint` | no | Skips classification. A caller who knows the script — a museum importing a catalogued collection — should not be second-guessed by a probabilistic classifier. |
| `content_type` | no | MIME type hint. |
| `sha256` | no | Lowercase hex. For caching, deduplication, reproducibility. |

Unknown fields are **rejected** with `422`. A client typo like `"mdoe"` fails
loudly rather than being silently ignored.

### Response — 200

Returned when a transcription was produced, even if some stages could not run.

```json
{
  "request_id": "0f8fad5b-d9cb-469f-a165-70867728950e",
  "civilization": "islamic_epigraphy",
  "complete": true,
  "unavailable_capabilities": [],
  "regions": [
    { "box": {"x": 10, "y": 20, "width": 200, "height": 50},
      "confidence": 0.88, "label": "inscription" }
  ],
  "ocr": {
    "text": "بِسْمِ ٱللَّهِ",
    "lines": [{ "text": "بِسْمِ ٱللَّهِ", "confidence": 0.93, "script": "arabic", "box": null }],
    "engine_id": "...",
    "mean_confidence": 0.93
  },
  "translation": {
    "text": "In the name of God",
    "source_language": "arabic",
    "target_language": "en",
    "engine_id": "...",
    "confidence": 0.75
  },
  "claims": [
    {
      "statement": "The inscription opens with the Basmala.",
      "confidence": 0.97,
      "subject_uri": null,
      "evidence": [
        {
          "citation": {
            "title": "Quran 1:1",
            "identifier": "quran:1:1",
            "kind": "primary_source",
            "locator": "Surah al-Fatiha, ayah 1",
            "url": null
          },
          "confidence": 0.97,
          "note": "The inscription opens with the Basmala."
        }
      ]
    }
  ],
  "stages": null
}
```

Notes:

- **`claims[].evidence` is never empty.** An unsupported historical claim cannot
  be constructed in the domain, so it cannot reach the wire (ADR-0005).
- `mean_confidence` is length-weighted across lines, so a confidently-read long
  line is not dragged down by a short uncertain fragment.
- `ocr.text` is the plugin's canonical form: recognition artefacts removed,
  **diacritics preserved** (ADR-0008).
- `stages` is `null` outside `developer` mode.

### Response — 503

Returned when **no transcription could be produced**.

```json
{
  "code": "capability_unavailable",
  "message": "Capability 'ocr' is not available: No transcription could be produced. Unavailable stages: preprocess, detect, ocr, translate, knowledge_graph.",
  "details": {
    "capability": "ocr",
    "reason": "No transcription could be produced. Unavailable stages: ..."
  }
}
```

**Why 503 rather than 200 with an empty result.** This endpoint's purpose is to
read an inscription. Without a reading it has not succeeded, and reporting 200
would misrepresent the outcome to every client and to every uptime dashboard.
The response names exactly what is missing.

**This is the current behaviour for every request**, since no OCR engine exists.

### Errors

| Status | `code` | Cause |
|--------|--------|-------|
| 404 | `plugin_not_found` | Unknown `civilization`. `details.available` lists valid ids. |
| 415 | `unsupported_input` | Well-formed but outside current support. |
| 422 | `validation_error` | Malformed request, unknown field, bad `sha256`, invalid `mode`. |
| 500 | `internal_error` | Unexpected failure. Message is deliberately generic — tracebacks disclose paths, config, and dependency versions. Detail goes to the structured log. |
| 503 | `capability_unavailable` | No reading produced. |

---

## Modes

| Mode | Intent | Effect on the response |
|------|--------|------------------------|
| `tourist` | Plain-language narrative | `stages` omitted |
| `research` | Full evidence chains, alternative readings | `stages` omitted **[planned: alternative readings]** |
| `developer` | Everything plus diagnostics | `stages` populated with per-stage status, timing, and implementation id |

Modes never change the platform's conclusions — asserted by
`test_mode_does_not_change_conclusions`.

---

## Current limitations

Recorded plainly so no integrator is misled:

| Limitation | Consequence | Scheduled |
|------------|-------------|-----------|
| No authentication or rate limiting | Must not be publicly exposed | M4 |
| `image_url` is validated but never fetched | No end-to-end analysis is possible yet | M2 |
| All capabilities unavailable | `/analyze` always returns 503 | M2–M5 |
| No pagination, no batch endpoint | One image per request | M8 |
| No caching, though `sha256` is accepted for it | No dedup benefit yet | M8 |

---

## Compatibility policy

Within v1, these are **non-breaking** and may ship at any time:

- New optional request fields
- New response fields
- New enum values in `unavailable_capabilities`, `stages[].status`, or
  `Script` — clients must tolerate unknown values

These require **v2**:

- Removing or renaming a field
- Changing a field's type or making an optional field required
- Changing the meaning of an existing `code`
