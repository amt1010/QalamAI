# Security

**Status:** living document · last updated 2026-07-22

---

## ⚠️ Current posture

**This platform must not be exposed to a public network.**

It has no authentication, no authorization, and no rate limiting. It is
suitable for local development only. Everything below documents both what is
already in place and what is missing.

---

## Assets worth protecting

| Asset | Concern |
|-------|---------|
| Heritage data integrity | **The primary asset.** Corrupted or fabricated readings can propagate into the historical record and cannot be recalled |
| Licensed source material | Institutional archives carry redistribution restrictions; a leak is a breach of agreement |
| Model artefacts | Represent substantial training investment |
| User-submitted images | May carry location metadata and reveal a user's movements |
| Service availability | Museum kiosks and on-site use depend on it |

Heritage data integrity is listed first deliberately. For most systems the worst
outcome is a data breach; here, silent corruption of what the platform asserts
about history is worse, because it is durable and hard to detect.

---

## Controls in place

| Control | Where | Protects against |
|---------|-------|------------------|
| Input validation | `AnalyzeRequestSchema` with `extra="forbid"`, length caps, `sha256` pattern | Malformed input, parameter smuggling, silent client typos |
| Generic 500 responses | `api/errors.py::unhandled_error_handler` | Information disclosure — tracebacks leak paths, config, dependency versions. Detail goes to the structured log instead |
| Stable error codes without internals | `core/errors.py` | Fingerprinting |
| Config rejects unknown variables | `Settings(extra="forbid")` | Silent misconfiguration where a typo'd variable takes a default |
| Fail-closed defaults | `ocr.default_engine="unavailable"` | An unconfigured deployment serving nothing rather than something wrong |
| No fabricated output | ADR-0004 | Integrity — the platform cannot assert what it does not know |
| Evidence required for claims | ADR-0005 | Integrity — no unsourced historical assertion is representable |
| Secrets excluded from git | `.gitignore`: `.env`, `*.pem`, `*.key`, `secrets/` | Credential leakage |
| Dependencies bounded | `pyproject.toml` (ADR-0002) | Unreviewed transitive upgrades |

Note that ADR-0004 and ADR-0005 are load-bearing security controls, not only
architectural ones. They protect the asset ranked first.

---

## Threats and status

### T1 — SSRF via `image_url` · **HIGH** · *unmitigated, blocks M2*

The API accepts a URL. Once M2 implements fetching, the server will make
outbound requests to caller-controlled addresses — a textbook SSRF vector
reaching cloud metadata endpoints (`169.254.169.254`), localhost services, and
internal networks.

Currently **not exploitable**, because the URL is validated but never fetched.

Required before fetching ships:
- Scheme allowlist (`https` only)
- Block private, loopback, link-local, and reserved ranges — resolved, not just
  as written, to defeat DNS rebinding
- Re-validate after every redirect; cap redirect depth
- Request timeouts and response size caps
- Egress from a network segment with no access to internal services
- Prefer direct upload over URL fetch where the client allows it

### T2 — Malicious image payloads · **HIGH** · *unmitigated, blocks M2*

Decompression bombs, malformed files targeting image-library CVEs, and
pixel-dimension attacks causing OOM. Image parsers are a historically rich
source of memory-safety bugs.

Required: size and dimension caps before decode, content-type verification by
magic bytes rather than the declared header, decoding in a resource-limited
context, and keeping image libraries patched.

### T3 — No authentication or rate limiting · **HIGH** · *unmitigated, M4*

Anyone reaching the service can consume unbounded compute. With models loaded,
inference is expensive and trivially abused for denial of service.

Required: authentication, per-principal rate limiting, request size limits, and
quotas on expensive operations.

### T4 — Prompt injection through inscription text · **MEDIUM** · *design required, M6*

Once an LLM explains inscriptions, recognized text becomes untrusted input to a
prompt. An adversary could photograph crafted text designed to manipulate the
explainer.

ADR-0005 limits the blast radius — claims require evidence from the graph, so
injected text cannot manufacture a sourced historical claim. But it does **not**
protect the surrounding narrative prose. This needs an explicit design, not an
assumption that grounding covers it.

### T5 — EXIF and location metadata · **MEDIUM** · *unmitigated, M2*

Uploaded photographs commonly carry GPS coordinates and device identifiers.
Retaining them creates a privacy liability; for monuments in sensitive
locations, publishing them may create a physical one.

Required: strip EXIF on ingestion; retain location only with explicit consent
and a documented purpose.

### T6 — Knowledge graph poisoning · **MEDIUM** · *design required, M5*

The HKG is the platform's source of truth. A bad write corrupts every downstream
claim — and because output would still carry citations, the corruption would
look authoritative.

Required: authenticated writes, a curation workflow, an audit trail, and the
ability to trace and revert any claim to its ingestion event.

### T7 — Supply chain · **MEDIUM** · *partially mitigated*

Bounded pins prevent unreviewed upgrades of direct dependencies, but there is no
lock file, so transitive resolution is unconstrained (ADR-0002 gap, M2). No
dependency vulnerability scanning is configured.

Required: lock file, automated vulnerability scanning in CI, and review of model
weights and datasets as supply-chain artefacts — a poisoned model or dataset is
as dangerous as a poisoned package.

### T8 — Denial of service through expensive inference · **MEDIUM** · *M8*

CV and OCR inference is expensive. Without queue limits and per-request
timeouts, a small volume of large images can exhaust capacity.

---

## Practices

- **Never commit secrets.** Configuration comes from the environment; `.env` is
  git-ignored.
- **Fail closed.** Defaults must produce no output rather than wrong output.
- **Log events, not payloads.** Structured logs must not contain image content,
  credentials, or personal data.
- **Errors are generic to clients, detailed in logs.**
- **Every dependency addition is a supply-chain decision** and needs a reason.

---

## Not yet done

| Item | Scheduled |
|------|-----------|
| Formal threat model (STRIDE or equivalent) covering the full pipeline | M2 |
| Dependency vulnerability scanning in CI | M2 |
| Secret scanning in CI | M2 |
| Lock file | M2 |
| Authentication and authorization design | M4 |
| Rate limiting and quotas | M4 |
| Security headers, CORS policy, TLS termination design | M8 |
| Audit logging for HKG writes | M5 |
| Penetration test before any public exposure | pre-launch |
| Vulnerability disclosure policy | pre-launch |
| Data retention and deletion policy for user-submitted images | M4 |

---

## Reporting a vulnerability

No disclosure process is established yet — the platform is not deployed. One
must exist before any public exposure.
