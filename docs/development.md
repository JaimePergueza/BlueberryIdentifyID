# Development guide

## Prerequisites

- Python 3.10+
- Docker + Docker Compose (for PostgreSQL/Redis; not required to run the test suite)
- **Recommended root folder name: `BlueberryMicroID`.** The repository was
  originally checked out at `D:\IndetificadorMicro`, a misspelling. The
  Python package itself is already correctly named `blueberry_microid`
  (`src/blueberry_microid/`) and no import, path, or test depends on the
  name of the repository's root folder — only on the editable install
  (`pip install -e .`) pointing at wherever the folder currently is. Renaming
  is a manual step (do it with the project closed in any active Claude Code
  session or editor, then reopen against the new path and re-run `pip
  install -e ".[dev]"` since the editable install records an absolute path):
  ```bash
  # from the parent directory, with nothing else open against the old path
  mv D:\IndetificadorMicro D:\BlueberryMicroID
  cd D:\BlueberryMicroID
  pip install -e ".[dev]"
  ```
  See ARCHITECTURE.md § 19 for why this was documented rather than executed
  automatically.

## 1. Create and activate a virtual environment

**Always install this project's dependencies into a dedicated virtual
environment — never into your system/global Python.** Installing directly
into a global interpreter can silently break unrelated tools that happen to
share it (this exact problem occurred during Fase 3: installing this
project's dependencies globally downgraded `starlette` and broke a
completely unrelated tool that depended on a newer version — see
ARCHITECTURE.md, "Fase 3", for the incident). A venv makes the project's
dependency set reproducible and isolated.

```bash
python -m venv .venv
```

Activate it — the command differs by shell:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS (or Git Bash on Windows)
source .venv/bin/activate
```

You should see `(.venv)` in your prompt once it's active. `.venv/` is
already listed in `.gitignore` — never commit it. `.gitignore` also covers
`*.egg-info/`, `__pycache__/`, `.pytest_cache/`, and `.env`.

## 2. Install dependencies

Dependencies are declared in `pyproject.toml` (chosen over a
`requirements.txt`/`requirements-dev.txt` pair so there is a single source of
truth — no risk of the two files drifting apart — and so the project is
installable as a normal editable package, which is what makes
`import blueberry_microid` work from anywhere without path hacks):

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

This installs the runtime dependencies (fastapi, uvicorn, sqlalchemy,
alembic, pydantic, pydantic-settings, pillow, python-multipart, psycopg) and
the `dev` extra (pytest, httpx) in one step, in editable mode, **inside the
active `.venv`** — confirm the venv is active (prompt shows `(.venv)`, or
`which python` / `where python` points inside `.venv`) before running this.
`httpx` is a dev-only dependency: it's what `fastapi.testclient.TestClient`
and `scripts/api_smoke_test.py` use, but the running API itself never
imports it.

## 3. Environment variables

```bash
cp .env.example .env
# edit .env if you need different local credentials/ports
```

See `.env.example` for the full list. Settings are loaded by
`blueberry_microid.infrastructure.config.get_settings()`:

| Variable | Default | Purpose |
|---|---|---|
| `ENVIRONMENT` | `development` | Free-form label, not yet used to branch behavior. |
| `DATABASE_URL` | local Postgres URL | SQLAlchemy connection string. Must be PostgreSQL for real use. |
| `STORAGE_ROOT` | `<repo>/storage` | Base directory for uploaded images. |
| `PETRI_IMAGE_DIR` / `MICRO_IMAGE_DIR` | `petri_images` / `micro_images` | Subdirectories under `STORAGE_ROOT`. |
| `MAX_UPLOAD_SIZE_MB` | `20` | Upload size ceiling for Petri/micro image endpoints (see § 8). |
| `LOG_LEVEL` | `INFO` | Standard library logging level for the root logger. |
| `LOG_FORMAT` | `console` | `console` (human-readable) or `json` (one JSON object per line). |

## 4. Start/stop backing services (PostgreSQL, Redis)

```bash
docker compose up -d       # start postgres + redis in the background
docker compose ps          # check status / wait for "healthy"
docker compose down        # stop and remove the containers
docker compose down -v     # also wipe the postgres data volume
```

Redis is provisioned now but not used by any code yet — it is reserved for
the future Celery-based asynchronous inference pipeline.

## 5. Run database migrations

Against the PostgreSQL started by Docker Compose:

```bash
export DATABASE_URL=postgresql+psycopg://blueberry:blueberry@localhost:5432/blueberry_microid
alembic upgrade head
alembic current
```

To sanity-check the migration files without a live database (generates the
DDL as text instead of executing it):

```bash
alembic upgrade head --sql
```

This offline mode is useful in environments without Docker access, but it is
**not** a substitute for actually running `alembic upgrade head` against a
real PostgreSQL instance. SQLite (used by this project's own test suite)
does **not** adequately exercise several things this schema relies on:
native PostgreSQL `ENUM` types, `JSONB`, partial indexes, `UUID` columns,
`CHECK`/`UNIQUE` constraints, and timezone-aware timestamps.

A convenience script automates the real check — connects to `DATABASE_URL`,
runs `alembic upgrade head`, prints `alembic current`, then verifies the
migrations are reversible (`alembic downgrade base` followed by `alembic
upgrade head` again):

```bash
python scripts/check_postgres_migrations.py
# or, to skip the downgrade/upgrade round-trip:
python scripts/check_postgres_migrations.py --skip-roundtrip
```

It refuses to report success unless every step actually succeeded, and
exits non-zero with a clear message otherwise (e.g. if Postgres isn't
reachable).

**Current status (carried through Fase 5): NOT validated against a real
PostgreSQL server.** The environment these phases were built in has no Docker
available (`docker: command not found`), so neither `docker compose up`
nor `scripts/check_postgres_migrations.py` could actually reach a
database — running the script there correctly fails fast with a connection
error, which is the honest and expected outcome, not a bug. What *has* been
done is: (1) `alembic upgrade head --sql` / `alembic downgrade head:base
--sql`, confirming migrations `0001` and `0002` produce syntactically valid,
reversible PostgreSQL DDL (including the `human_reviews` partial unique
index); (2) equivalent behavior re-verified against SQLite in
`tests/integration/db/` for everything SQLite *can* represent. Neither of
those is a substitute for a real run. Before trusting this schema in any
shared environment: start Docker Compose (§ 4) and run
`python scripts/check_postgres_migrations.py`, confirm it prints `SUCCESS`,
and update this note.

## 6. Run the API

```bash
uvicorn blueberry_microid.interfaces.api.app:create_app --factory --reload
```

Then visit `http://127.0.0.1:8000/health` (should return
`{"status": "ok", "service": "BlueberryMicroID"}`) or `http://127.0.0.1:8000/docs`
for interactive Swagger docs.

`POST /api/v1/analysis-runs/{id}/process` runs the **simulated** inference
pipeline synchronously (no Celery, nothing queued): it always uses
`MockInferenceEngine`, a deterministic simulation that never opens or
analyzes the actual image bytes, never identifies a species/genus, and
carries no diagnostic validity — see § 11 below. A given `AnalysisRun` can
only be processed once; a second call returns `409 Conflict`. If processing
fails after the run has been claimed, the run is persisted as `failed` and
the client receives a safe error response, not `200 OK`.

## 7. Run the operational smoke test

With the API running (previous step), in another terminal (same venv):

```bash
python scripts/api_smoke_test.py
# or against a non-default host/port:
python scripts/api_smoke_test.py http://127.0.0.1:8000
```

This drives the golden path end-to-end against the **live** server (not
`TestClient`): health check → create sample → create a `mock` model version
→ upload a Petri dish image → upload a microscopy image → create an
`AnalysisRun` → read it back → process it (simulated inference) → read the
resulting `Prediction`. Both images are tiny solid-color JPEG/PNG files
generated in memory with Pillow — no external files or datasets are used.
It prints one line per step and exits with status 1 on the first failure,
so it's suitable for a CI health-check step or a manual sanity check after
deploying.

## 8. Upload limits and image validation

- `MAX_UPLOAD_SIZE_MB` (default 20) caps Petri/micro image uploads. The API
  reads the full request body and computes the real size (`len(content)`)
  before comparing it to the configured limit — a request over the limit
  gets `413 Payload Too Large` with the standard `{"error": {...}}` shape,
  before the file ever reaches the image validator or storage. The limit is
  read from `Settings`, never hardcoded in a router.
- Every uploaded file must pass strict validation
  (`PillowImageValidator`, wired in by `ImageIntakeService`): non-empty,
  an allowed MIME type (`image/jpeg`, `image/png`, `image/tiff`), an
  allowed extension (`.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`), decodable by
  Pillow without corruption, **and** the format Pillow actually detects must
  match both the declared MIME type and the file extension. A `.png`-named
  file that's really a JPEG, or a request declaring `image/png` for JPEG
  bytes, is rejected even though the MIME/extension are each individually
  "allowed" — `UploadFile.content_type` and the client-supplied file name
  are just claims, not proof.
- No upload's file content is ever written to a log line — logs only ever
  reference size, filename, and outcome, never raw bytes.

## 9. Logging and request tracing

- `blueberry_microid.infrastructure.logging.configure_logging(settings)` is
  called once in `create_app()`; it points the root logger at a single
  stdout stream handler formatted per `LOG_FORMAT` (`console` or `json`,
  see `infrastructure/logging/formatters.py`) at `LOG_LEVEL`. No external
  logging service is used.
- `RequestLoggingMiddleware` assigns a `request_id` to every request
  (reusing the client's `X-Request-ID` header if present, generating a
  `uuid4().hex` otherwise) and logs one structured line per request:
  timestamp, level, `request_id`, `method`, `path`, `status_code`,
  `duration_ms`. Every response — success or error — echoes the id back in
  an `X-Request-ID` header.
- Any error that resolves to a 5xx status is logged server-side with its
  full stack trace (`interfaces/api/error_handlers.py`); the client only
  ever receives a fixed generic message, never the exception text or a
  traceback.

## 10. Simulated inference engine and Prediction lifecycle

- `POST /api/v1/analysis-runs/{id}/process` is the only way a `Prediction`
  gets created. It moves the `AnalysisRun` through `pending` → `processing`
  → `completed` or `needs_review` (or `failed`, with `error_message`, if the
  processing step fails). A failed processing attempt returns a controlled
  HTTP error (`500 analysis_processing_failed`, or `409 duplicate_prediction`
  for an existing Prediction), not `200 OK`. Reprocessing an
  already-processed `AnalysisRun` returns `409 Conflict`; create a new
  `AnalysisRun` instead.
- The only `InferenceEnginePort` implementation today is
  `MockInferenceEngine` (`ml/inference_engine/`): a **deterministic
  simulation** based on a hash of `analysis_run.id`, not randomness. It
  never opens, decodes, or otherwise looks at the actual Petri dish or
  microscopy image bytes, never uses PyTorch/OpenCV/Cellpose, and never
  produces a species/genus name — only one of five broad, preliminary
  categories (`no_evident_growth`, `suspicious_growth`,
  `probable_fungal_growth`, `probable_bacterial_growth`, `inconclusive`).
  Its `confidence_score` is always moderate (≤ 0.75), by design — never a
  falsely high number meant to look authoritative.
- `POST /process`'s response always includes a `disclaimer` field stating,
  in the response body itself (not only in this document), that the result
  is simulated and has no diagnostic validity.
- `GET /api/v1/analysis-runs/{id}/prediction` is read-only and returns
  `404 Not Found` if the run hasn't been processed yet.
- **None of this is a real diagnosis.** No dataset was used to build
  `MockInferenceEngine`, no accuracy/precision/recall number is real or
  implied, and no microorganism species or genus is ever identified by this
  system.

## 11. Idempotency, anti-double-processing, and crash recovery (Fase 4.5/4.6)

Fase 4 left `ProcessAnalysisRunUseCase` with three independent transactional
blocks; a failure between the first (marking `processing`) and the last
(creating the `Prediction` and the final status) could leave an
`AnalysisRun` stuck in `processing` forever, with no code path that ever
recovered it. Fase 4.5 closed that gap, and Fase 4.6 tightened the HTTP
semantics so failed processing is no longer reported as `200 OK`. This
section documents the resulting behavior — see `ARCHITECTURE.md` § 17 for
the full technical rationale.

- **Claiming is atomic, not a read-then-write.** The `pending -> processing`
  transition is a single conditional database update
  (`AnalysisRunRepositoryPort.claim_for_processing`,
  `UPDATE ... WHERE status = 'pending'`, checked by `rowcount`) — not a
  Python-side "load, validate, save". Two simultaneous `POST /process` calls
  for the same `AnalysisRun` can never both succeed: exactly one wins the
  claim and proceeds; the other gets `409 Conflict` immediately, without
  ever touching the inference engine or writing a `Prediction`.
- **Every non-`pending` status returns 409, with a tailored message:**
  `processing` → "already being processed"; `completed`/`needs_review` →
  "already been processed" (use `GET /prediction`); `failed` → "create a new
  AnalysisRun to retry" (a failed run is never reopened).
- **`processing` is never a permanent state.** Everything that happens after
  a successful claim — running the (simulated) engine, building the
  `Prediction`, the final commit — is wrapped in one recovery path: any
  failure moves the `AnalysisRun` to `failed` with a controlled
  `error_message`, written in its own transaction, independent of whatever
  just failed. The original exception is logged server-side and preserved as
  the cause of a controlled application error; the client sees
  `500 analysis_processing_failed` with a generic message, never a raw stack
  trace and never a fake "success" response. If *that* fallback write also
  fails (the one scenario this cannot self-heal), the original error and the
  write failure are both logged (the latter at `CRITICAL`) and the client gets
  `500 analysis_run_finalization_failed`.
- **A duplicate `Prediction` during finalization is a controlled conflict.**
  With claiming exclusive, this should be structurally impossible; if it
  ever happens anyway (e.g. manual database tampering), the use case first
  marks the `AnalysisRun` as `failed` with a controlled `error_message`, then
  raises `409 duplicate_prediction`. It never creates a second `Prediction`
  and never leaves the run in `processing`.
- **Still no Celery, no real AI/ML, no PyTorch, no dataset, no frontend, no
  authentication, no taxonomy.** None of the above changes the scope
  restrictions from earlier phases — this is entirely about the robustness
  and HTTP semantics of the existing synchronous, simulated pipeline.

## 12. Human review flow (Fase 5)

Human review is now exposed as an audit layer over an already-processed
`AnalysisRun`. It does not mutate the original `Prediction` and it does not
introduce taxonomy, training, datasets, metrics, authentication, frontend, or
Celery.

Endpoints:

| Method | Route | Behavior |
|---|---|---|
| POST | `/api/v1/analysis-runs/{analysis_run_id}/reviews` | Creates a review. Decisions: `confirmed`, `corrected`, `marked_inconclusive`, `rejected_invalid_sample`. |
| GET | `/api/v1/analysis-runs/{analysis_run_id}/reviews` | Lists review history chronologically. |
| GET | `/api/v1/analysis-runs/{analysis_run_id}/reviews/final` | Returns the current final review, or `404 human_review_not_found`. |

Rules enforced by the use cases:

- A review requires an existing `AnalysisRun` and an existing `Prediction`.
  Missing runs return `404 analysis_run_not_found`; missing predictions return
  `404 prediction_not_found`.
- `pending` and `processing` runs are not reviewable yet and return
  `409 analysis_run_not_reviewable`.
- `corrected` reviews must include `corrected_label`; the label is one of the
  same five broad visual classes used by `Prediction`, never species/genus.
- `marked_inconclusive` can only carry `corrected_label=inconclusive` if a
  corrected label is supplied.
- A new review defaults to `is_final=true`. If it is final,
  `SubmitHumanReviewUseCase` demotes any previous final review and inserts the
  new one in a single `UnitOfWork`. If the insert fails, rollback preserves the
  previous final review.
- `Prediction` is immutable in this flow: confirmed/corrected/inconclusive
  human decisions are stored in `HumanReview`, not written back into
  `Prediction`.

## 13. Run tests

```bash
pytest -v
```

(`pytest` alone also works — `testpaths = ["tests"]` is set in
`pyproject.toml` — but the explicit invocation above matches earlier phases'
docs.)

As of Fase 5 this collects **188 tests**, all passing:

| Folder | Count | What it covers |
|---|---|---|
| `tests/unit/domain/` | 26 | Entities, value objects, domain invariants (incl. `AnalysisRun` state transitions) — no I/O. |
| `tests/unit/application/` | 58 | Use cases with in-memory fakes (incl. `MockInferenceEngine`, `ProcessAnalysisRunUseCase` idempotency/claim/recovery scenarios, and `SubmitHumanReviewUseCase` final-review rollback) — no database, no filesystem. |
| `tests/unit/infrastructure/` | 14 | `Settings` + `PillowImageValidator`, in isolation. |
| `tests/integration/db/` | 28 | Real SQLAlchemy repositories against in-memory SQLite, incl. `claim_for_processing` atomicity, human-review final uniqueness, and real cross-repository transaction rollback. |
| `tests/api/` | 62 | Full FastAPI app via `TestClient`, SQLite + temp storage, incl. idempotency at every non-`pending` status and the human-review endpoints. |

26 + 58 + 14 + 28 + 62 = **188**, matching `pytest --collect-only -q`.

(A Fase 3 summary once reported `18 + 21 + 18 + 27 = 84`, which did not add
up — a mislabeled integration-test count that should have read `13`; no
tests were ever double-counted. `18 + 21 + 13 + 27 = 79` was the correct
Fase-3 total; it grew to 102 in Fase 3.5, 136 in Fase 4, 160 in Fase 4.6,
and 188 in Fase 5.)

- `tests/unit/` never touches a database or the filesystem (in-memory doubles).
- `tests/integration/db/` exercises the real SQLAlchemy repositories against
  an in-memory **SQLite** database — a fast substitute for local development
  only. Every table is included, including `predictions`: its
  `class_probabilities` column uses `PortableJSON` (Fase 4), which compiles
  to `JSONB` on PostgreSQL and generic `JSON` elsewhere — no table needs to
  be excluded anymore.
- `tests/api/` drives the FastAPI app end-to-end with `TestClient`, also
  against in-memory SQLite (shared across requests via `StaticPool`) and a
  temporary directory for image storage — see `tests/api/conftest.py`.
  Uploaded test images are generated in memory with Pillow; no external or
  invented image/dataset files are used anywhere in the test suite.

None of the above replaces validating migrations/constraints against real
PostgreSQL (see § 5).

## 14. Project sanitation, Git, and CI (Fase 5.5)

This phase closed operational debt accumulated across Fases 0–5 — no new
business functionality. See ARCHITECTURE.md § 19 for the full rationale.

- **Root folder name:** see the note at the top of this document
  (Prerequisites). Not renamed automatically; documented as a manual step.
- **Git:** the repository previously had an empty, non-functional `.git/`
  directory (`git status` reported `fatal: not a git repository`). It has
  since been initialized (`git init`) with `main` as the default branch.
  `.gitignore` was extended to also cover `.coverage`/`htmlcov/`,
  `build/`/`dist/`, `*.db`/`*.sqlite`/`*.sqlite3`, `*.log`/`logs/`, and
  `.claude/settings.local.json` (local tool config, machine-specific).
- **Cleanup:** all `__pycache__/` directories and a stray `build/` artifact
  (from a previous packaging step) were removed. `storage/petri_images/` and
  `storage/micro_images/` contain nothing but their `.gitkeep` placeholders —
  no leftover test-uploaded files. No `.pytest_cache/`, `.coverage`, or
  `*.sqlite*` files were present at the time of cleanup.
- **CI:** `.github/workflows/tests.yml` runs on every push/PR to `main`:
  checkout → `actions/setup-python@v5` (3.10) → `pip install -e ".[dev]"` →
  `pytest -v`. No deployment step, no Postgres service container, no
  secrets. Real PostgreSQL validation (§ 5) is explicitly **not** part of
  this CI yet — it remains a manual, separate step until a future
  improvement decides to add a `services: postgres:` block.
- **PostgreSQL real validation:** re-attempted in this phase — `docker` is
  not installed in this environment (`command not found` from both Bash and
  PowerShell), so `docker compose up -d` could not run.
  `python scripts/check_postgres_migrations.py` was still run against the
  default `DATABASE_URL` and failed exactly as expected, with a real
  `psycopg.errors.ConnectionTimeout` against `localhost:5432` — a genuine
  attempt with an honest, unresolved result, not a skipped step. This
  remains a **blocking prerequisite before any real deployment**, unchanged
  from every prior phase's status.
- **Reproducibility:** the `.venv` was not recreated in this phase (to avoid
  disrupting the active session), but `pip show` confirmed all 11 explicitly
  required dependencies (FastAPI, Uvicorn, SQLAlchemy, Alembic, Pydantic,
  Pydantic Settings, Pillow, python-multipart, psycopg, pytest, httpx) are
  both declared in `pyproject.toml` and installed at matching versions.
