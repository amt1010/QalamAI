# Performance

**Status:** living document · last updated 2026-07-22

---

## Current state

**No benchmarks have been run. No performance claims are made.**

The measurement infrastructure exists — every pipeline stage is timed and
reported — but with no models wired, the only thing measurable today is
framework overhead, which predicts nothing about production behaviour.

The `benchmark` pytest marker is declared and currently unused.

---

## Measurement already in place

`run_stage` in `application/stage.py` times every stage and records a
`StageReport` with duration, status, and implementation id.

These surface in two places:

- **`analysis.finished` / `stage.completed` structured log events**, with typed
  fields, so latency can be aggregated by stage and by implementation rather
  than grepped.
- **`POST /analyze` in `developer` mode**, which returns `stages[]` with
  per-stage timing.

Because `implementation_id` is recorded alongside duration, engine A and engine
B can be compared directly from production traffic once both exist.

---

## Budgets — proposed, not yet validated

Targets to design against. Each must be confirmed or revised against real
measurements; none is currently met, because nothing is implemented.

| Stage | Target (p95) | Rationale |
|-------|--------------|-----------|
| Ingestion + validation | 200 ms | Excluding network transfer |
| Preprocessing | 500 ms | CPU-bound; the enhancement/latency trade-off is tunable |
| Detection | 300 ms | |
| Script classification | 100 ms | Small model over one region |
| OCR | 1500 ms | Expected to dominate; the primary optimization target |
| Translation | 500 ms offline / 2000 ms hosted | Hosted adds network variance outside our control |
| HKG lookup | 300 ms | Indexed retrieval; degrades with traversal depth |
| **End to end** | **< 5 s** | |

**Why 5 seconds.** The primary use case is a visitor standing in front of a
monument holding a phone. Beyond roughly five seconds the interaction stops
feeling like looking something up and starts feeling broken. This is a product
constraint driving an engineering budget, not the reverse.

The tourist path may need a tighter budget than the research path. Research mode
can reasonably take longer for a more thorough answer; that split should be
designed once real latencies are known.

---

## Concurrency model

All ports are async (ADR-0006). I/O-bound stages — HKG queries, hosted
translation, remote inference — get concurrency for free.

**CPU-bound adapters must wrap synchronous work in `asyncio.to_thread`.** A
forgotten wrapper blocks the event loop and stalls every concurrent request,
and it will not show up in single-request testing — the symptom appears only
under load.

Mitigation: event-loop lag must be an explicitly monitored metric, and this is
a mandatory item on the adapter review checklist. No test currently catches it
(recorded in `TEST_PLAN.md` § Gaps).

---

## Known and anticipated characteristics

**Current.** Framework overhead only. Every stage short-circuits on
unavailability, so a request completes in well under a millisecond and the
number is meaningless.

**Anticipated once models land:**

- OCR will dominate end-to-end latency.
- Preprocessing quality and speed trade directly against each other; the
  correct operating point depends on how much OCR accuracy improves per
  millisecond of enhancement — which is measurable and should be measured
  rather than guessed.
- Model loading will dominate cold start. Whether models stay resident, and
  therefore the memory floor per process, is an open capacity question.
- Batch throughput and interactive latency will conflict. ADR-0001's single
  deployable means a memory-hungry CV model shares a process with a
  latency-sensitive API — one of that ADR's explicit revisit triggers.

---

## Benchmark methodology *(to be established, M3)*

For results to mean anything:

- Fixed hardware, recorded with the result. A latency figure without hardware
  is not a measurement.
- Report p50, p95, and p99 — never the mean. Mean latency hides exactly the
  tail that users notice.
- Warm-up runs excluded; model loading measured separately from inference.
- Real monument photographs, not synthetic images. Synthetic data will
  understate both latency and difficulty.
- Report by condition — weathering, angle, contrast — for the same reason
  accuracy is reported that way (`MODEL_REGISTRY.md` § Metrics policy). An
  aggregate hides the hard cases.
- Benchmarks versioned alongside the code and dataset version they ran against.

---

## Results

*(none)*

---

## Not yet done

| Item | Scheduled |
|------|-----------|
| Benchmark harness and methodology | M3 |
| Baseline measurements per stage | M3 |
| Load and concurrency testing | M8 |
| Event-loop lag monitoring | M8 |
| Memory profiling with models resident | M3 |
| Cold-start measurement and mitigation | M8 |
| Metrics export and dashboards | M8 |
| Capacity model — requests per instance | M8 |
| Mobile-side performance budget | M7 |
