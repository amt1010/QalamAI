# M2 — Image Ingestion and Preprocessing: Design

**Status:** approved · 2026-07-25
**Milestone:** M2 (see `PROJECT_MASTER_PLAN.md`)

---

## 1. Scope and non-goals

**In scope for this slice:**

- Direct multipart image upload (camera capture or gallery pick from the
  eventual mobile client) as the ingestion path.
- Validation: magic-byte content-type check, size and dimension caps,
  decompression-bomb defense.
- EXIF stripping (`SECURITY.md` T5).
- Local-filesystem storage behind a new `ImageStore` port, content-addressed
  by SHA-256.
- Preprocessing: denoising and contrast enhancement (unconditional),
  perspective correction only when the caller supplies corner points.
- Dependency lock file, closing the gap named in ADR-0002.

**Explicitly not in this slice:**

- Server-side URL fetch (`image_url`). The original M2 scope in
  `PROJECT_MASTER_PLAN.md` assumed fetching `image_url`; that assumption is
  superseded by this design. The real input source is a device camera or
  gallery picker, which uploads bytes directly — there is no product need to
  fetch third-party URLs yet. Because no server-side fetch exists, `SECURITY.md`
  T1 (SSRF via `image_url`) stays genuinely unexploitable, not merely
  mitigated, and none of the allowlist/redirect/DNS-rebinding machinery it
  requires needs to be built this milestone.
- Object storage (S3-compatible). Local filesystem matches the current
  self-host/local-dev deployment stage.
- Automatic perspective correction (corner/quadrilateral auto-detection).
  Unreliable on weathered, irregular stone with no clean rectangular boundary;
  deferred until real benchmark photography exists to validate it against.

**Reversal trigger:** revisit URL-fetch ingestion if an institutional-archive
import use case materializes (a museum or archive wants to hand the platform
a list of URLs rather than uploading files).

---

## 2. API contract

Additive only — no field is removed or renamed, per the v1 compatibility
policy in `API_SPECIFICATION.md`.

### `POST /api/v1/images` (new)

Multipart upload.

| Field | Required | Notes |
|-------|----------|-------|
| `file` | yes | The image bytes. |
| `corners` | no | Four x/y pixel pairs, caller-supplied, for perspective correction. |

**200**

```json
{
  "image_id": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "content_type": "image/jpeg",
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "width": 3024,
  "height": 4032
}
```

`image_id` **is** the SHA-256 hex digest of the stripped, stored bytes —
there is no separate identifier scheme. Re-uploading identical visual content
(even with different EXIF, since EXIF is stripped before hashing) resolves to
the same `image_id`, giving deduplication for free.

**Errors:** `415 unsupported_input` for a well-formed-but-rejected upload
(oversized, disallowed type, fails the magic-byte check, decompression-bomb
guard trips); `422 validation_error` if the multipart body itself doesn't
parse.

### `POST /api/v1/analyze` (existing endpoint, extended)

`AnalyzeRequestSchema` gains one new optional field:

| Field | Required | Notes |
|-------|----------|-------|
| `image_id` | no | References a previously uploaded image via `POST /api/v1/images`. |

Exactly one of `image_url` or `image_id` must be present. This milestone:

- `image_id` present, `image_url` absent → proceeds (the supported path).
- `image_url` present, `image_id` absent → `415 unsupported_input`. This is a
  behavior change from today (silently accepted, never fetched) to an honest
  rejection, consistent with ADR-0004's "fail loudly, never plausibly."
- Neither present, or both present → `422 validation_error`. Both present is
  rejected rather than one silently taking precedence, matching the existing
  `extra="forbid"` philosophy of failing loud on ambiguous input.
- `image_id` referencing nothing stored → `404 image_not_found` (new error
  code, parallel to `plugin_not_found`).

Two-step (upload, then analyze-by-id) rather than one combined
multipart-analyze request, because `ImageReference.sha256` already exists in
the domain specifically for caching, dedup, and reproducibility, and the
two-step shape lets a client re-analyze the same image (different mode,
different civilization) without re-uploading.

---

## 3. Domain and ports

New port in `qalam/domain/ports.py`, alongside the existing six, extending
`Capability` like every other port:

```python
class ImageStore(Capability, Protocol):
    """Content-addressed storage for validated image bytes."""

    async def put(self, data: bytes, *, content_type: str) -> ImageReference:
        """Store bytes, returning a reference addressed by their SHA-256."""
        ...

    async def get(self, image_id: str) -> bytes:
        """Retrieve previously stored bytes, or raise if unknown."""
        ...
```

Kept separate from `ImagePreprocessor`: storage and enhancement are different
concerns, and the separation means a future S3 adapter swap touches nothing
about preprocessing. `UnavailableImageStore` joins `adapters/unavailable.py`
for parity with every other capability when unconfigured.

`ImageReference` (in `domain/entities.py`) is unchanged in shape but gains a
new optional carrier for corner hints, needed so the preprocessing stage can
receive them:

```python
@dataclass(frozen=True, slots=True)
class Point:
    x: int
    y: int

# ImageReference gains:
corners: tuple[Point, Point, Point, Point] | None = None
```

---

## 4. Validation pipeline

Runs inside the ingestion adapter (`adapters` layer — it performs real I/O
and decoding), in this order:

1. **Size cap on the raw upload**, enforced before decode. Starlette/FastAPI
   can reject an oversized body before it's fully buffered.
2. **Magic-byte content-type sniff** — not the client-declared `Content-Type`
   header. Reject anything that isn't JPEG, PNG, or WebP.
3. **Decode via Pillow** with `Image.MAX_IMAGE_PIXELS` set from
   `IngestionSettings.max_dimension_px`-derived area, so Pillow raises
   `DecompressionBombError` rather than allocating.
4. **Post-decode dimension cap check.**
5. **EXIF strip** — rebuild the image without the EXIF chunk entirely, rather
   than selectively removing GPS tags. Simpler, and matches "strip on
   ingestion" from `SECURITY.md` T5.
6. **SHA-256 over the stripped bytes** — stable regardless of source EXIF,
   which is what makes the dedup-by-hash behavior in §2 correct.
7. **Store**, content-addressed by that hash, via `ImageStore.put`.

All of this lives in one new adapter
(`adapters/local_image_store.py`, implementing `ImageStore`), separate from
the `ImagePreprocessor` adapter: ingestion validates and stores; preprocessing
enhances.

---

## 5. Preprocessing adapter

New adapter `adapters/opencv_preprocessor.py`, implementing `ImagePreprocessor`:

- **Denoising:** `cv2.fastNlMeansDenoisingColored` — a reasonable default for
  photographic sensor noise (not synthetic-image noise).
- **Contrast enhancement:** CLAHE (contrast-limited adaptive histogram
  equalization) on the luminance channel. Better than global histogram
  equalization for unevenly lit stone relief — shadow on one side, glare on
  the other is the common case for monument photography.
- **Perspective correction:** applied only when `ImageReference.corners` is
  present. `cv2.getPerspectiveTransform` + `cv2.warpPerspective`. No
  auto-detection (see §1 non-goals).
- Output: a new `ImageReference` for the enhanced derivative, stored via the
  same `ImageStore` port used by ingestion — the pipeline's existing
  "unavailable preprocessor → fall back to the original image" behavior in
  `application/pipeline.py` needs no change.

**Known gap this creates:** corner hints must be collected by a client UI
(drag corners over the inscription before upload), which is M7 (mobile
client) scope and doesn't exist yet. Until M7, the `corners` field exists and
the correction path works, but nothing populates it in practice — the same
honest-gap pattern the rest of the platform already uses for unimplemented
capabilities. Recorded in `ARCHITECTURE.md`'s Known Gaps table.

Library choice: **OpenCV** (`opencv-python-headless`, to avoid pulling in
GUI/Qt bindings a server process never uses). ADR-0002 already named OpenCV
as one reason Python 3.12 was chosen for wheel availability, so this is an
anticipated dependency, not a surprise one.

---

## 6. Configuration

New `IngestionSettings` in `core/config.py`, following the existing
`extra="forbid"` fail-loud pattern:

```python
class IngestionSettings(BaseSettings):
    max_upload_bytes: int = Field(default=20_000_000)
    max_dimension_px: int = Field(default=8000)
    allowed_content_types: frozenset[str] = frozenset(
        {"image/jpeg", "image/png", "image/webp"}
    )
    storage_dir: str = Field(default="./data/images")
```

---

## 7. Dependencies and lock file

New direct dependencies (bounded pins, per ADR-0002's convention):

- `opencv-python-headless` — preprocessing
- `Pillow` — decode, validate, EXIF-strip
- `python-multipart` — required by FastAPI/Starlette for multipart form
  parsing

**Lock file:** `uv.lock`, generated by `uv lock` from `pyproject.toml`,
committed to the repository. This is the exact mechanism ADR-0002 named as
its revisit trigger. CI switches to `uv sync --frozen` (or equivalent) so a
drifted lock file fails the build rather than silently re-resolving.

---

## 8. Error handling

New error class in `core/errors.py`, parallel to `PluginNotFoundError`:

```python
class ImageNotFoundError(QalamError):
    code = "image_not_found"
    http_status = 404
```

Upload validation failures (oversized, disallowed type, fails magic-byte
check, trips the decompression-bomb guard) map to the existing
`UnsupportedInputError` (415) — "well-formed but outside current support" is
exactly this case. A multipart body that fails to parse at all maps to the
existing `ValidationError` (422).

---

## 9. Testing and benchmarks

- **Unit:** validation edge cases — oversized upload, wrong magic bytes,
  decompression-bomb fixture, corrupt file, an EXIF-with-GPS fixture
  asserting the GPS tag is gone after storage.
- **Integration:** upload → analyze-by-id round trip through the real local
  `ImageStore`; SHA-256 stability across re-upload of visually-identical
  bytes with different EXIF; corner-hint homography against a synthetic
  skewed test image.
- **Architecture:** extend the existing import-linter fitness tests so the
  new `ImageStore` and preprocessor adapters are checked to stay below
  `application`, same as every other port.
- **Benchmark** (required by the Definition of Done): enhancement quality
  needs real monument photographs, not synthetic ones — `PROJECT_MASTER_PLAN.md`
  already flags this for M2 explicitly. This benchmark is blocked on sourcing
  sample images, the same critical-path dependency already named for M3's
  OCR benchmark.

---

## 10. Documentation to update

- `ARCHITECTURE.md` — ports table (`ImageStore` added, `ImagePreprocessor`
  moves from planned to implemented), Known Gaps table.
- `API_SPECIFICATION.md` — new `POST /api/v1/images` endpoint, `image_id`
  field on `/analyze`, updated Current Limitations table.
- `SECURITY.md` — T1 marked not-applicable this milestone with the reasoning
  from §1; T2 marked mitigated (validation pipeline, §4); T5 marked mitigated
  (EXIF strip, §4); T7 partially addressed (lock file, §7).
- `PERFORMANCE.md` — new benchmark section for enhancement quality (blocked
  per §9 until sample images exist).
- `RESEARCH_LOG.md` — OpenCV vs. alternatives for preprocessing; CLAHE vs.
  global histogram equalization, with reasoning.
- `CHANGELOG.md` — entry for the milestone.
- New ADR — "Direct upload instead of URL fetch for M2," recording the
  SSRF-driven scope decision from §1 and its reversal trigger.

---

## 11. Definition of Done mapping

Per `PROJECT_MASTER_PLAN.md`'s Definition of Done: production code with no
placeholders (§3–§5 adapters are real implementations, not stubs); unit,
integration, and architecture tests (§9); lint/type/import gates unchanged,
extended to new modules; benchmark recorded in `PERFORMANCE.md` (§9, with its
sourcing dependency named rather than skipped silently); documentation
updated (§10); new ADR written (§10); security implications documented
(§10); research findings recorded (§10); `CHANGELOG.md` updated (§10).
