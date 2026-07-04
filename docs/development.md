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
alembic, pydantic, pydantic-settings, pillow, numpy, scikit-learn,
python-multipart, psycopg) and
the `dev` extra (pytest, httpx) in one step, in editable mode, **inside the
active `.venv`** — confirm the venv is active (prompt shows `(.venv)`, or
`which python` / `where python` points inside `.venv`) before running this.
`httpx` is a dev-only dependency: it's what `fastapi.testclient.TestClient`
and `scripts/api_smoke_test.py` use, but the running API itself never
imports it.

`scikit-learn` is used only by the Fase 16 classical tabular baseline
(`logistic_regression_tabular`) over already-persisted `ImageFeatureVector`
rows. It is not PyTorch/TensorFlow, does not read image bytes, and is not used
by `MockInferenceEngine`.

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
| `API_BASE_URL` | `http://127.0.0.1:8000` | Base URL used by operational smoke scripts. |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Broker for asynchronous mock processing tasks. |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Auxiliary Celery result backend; not the source of truth for analysis state. |
| `CELERY_TASK_ALWAYS_EAGER` | `false` | Test/development switch to run Celery tasks inline without Redis/worker. |
| `CELERY_TASK_EAGER_PROPAGATES` | `true` | In eager mode, propagate task exceptions to tests. |
| `CELERY_TASK_TIME_LIMIT` / `CELERY_TASK_SOFT_TIME_LIMIT` | `300` / `240` | Optional safety limits for task runtime. |

## 4. Start/stop backing services (PostgreSQL, Redis)

```bash
docker compose up -d       # start postgres + redis in the background
docker compose ps          # check status / wait for "healthy"
docker compose down        # stop and remove the containers
docker compose down -v     # also wipe the postgres data volume
```

Redis is used by Celery as the broker/result backend for asynchronous mock
processing in local development. Tests use Celery eager mode and do not need
a real Redis process.

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
pipeline synchronously: it always uses
`MockInferenceEngine`, a deterministic simulation that never opens or
analyzes the actual image bytes, never identifies a species/genus, and
carries no diagnostic validity — see § 11 below. A given `AnalysisRun` can
only be processed once; a second call returns `409 Conflict`. If processing
fails after the run has been claimed, the run is persisted as `failed` and
the client receives a safe error response, not `200 OK`.

For operation-like local testing, run a Celery worker in a separate terminal:

```bash
docker compose up -d redis
celery -A blueberry_microid.infrastructure.tasks.celery_app.celery_app worker --loglevel=info -Q analysis
```

Then queue processing instead of running it inside the request:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analysis-runs/<analysis_run_id>/process-async
curl http://127.0.0.1:8000/api/v1/analysis-runs/<analysis_run_id>
curl http://127.0.0.1:8000/api/v1/analysis-runs/<analysis_run_id>/prediction
```

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

For the real Redis + Celery async path, start PostgreSQL, Redis, the API, and
a worker, then run the Celery smoke:

```bash
# terminal 1
docker compose up -d postgres redis
export DATABASE_URL=postgresql+psycopg://blueberry:blueberry@localhost:5432/blueberry_microid
alembic upgrade head

# terminal 2
uvicorn blueberry_microid.interfaces.api.app:create_app --factory --reload

# terminal 3
celery -A blueberry_microid.infrastructure.tasks.celery_app.celery_app worker --loglevel=info -Q analysis

# terminal 4
python scripts/celery_smoke_test.py
```

Stop local services when done:

```bash
docker compose down
```

`scripts/celery_smoke_test.py` calls `/process-async`, polls
`/api/v1/tasks/{task_id}` until `SUCCESS`, then verifies the durable
`AnalysisRun`, `Prediction`, and final `HumanReview`. It still uses only
generated Pillow images and `MockInferenceEngine`.

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
  gets created synchronously. `POST /api/v1/analysis-runs/{id}/process-async`
  queues the same use case through Celery and returns `202 Accepted`; the
  worker then moves the `AnalysisRun` through `pending` → `processing` →
  `completed` or `needs_review` (or `failed`, with `error_message`, if the
  processing step fails). A failed synchronous processing attempt returns a
  controlled HTTP error (`500 analysis_processing_failed`, or `409
  duplicate_prediction` for an existing Prediction), not `200 OK`.
  Reprocessing an already-processed `AnalysisRun` returns `409 Conflict`;
  create a new `AnalysisRun` instead.
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
- **Async queueing does not duplicate processing rules.** The Celery task
  calls `ProcessAnalysisRunUseCase` with SQLAlchemy repositories,
  `SqlAlchemyUnitOfWork`, and `MockInferenceEngine`. The `/process-async`
  endpoint only verifies the run exists and is still `pending`, then queues
  the task. It does not claim the row, create a Prediction, or call the
  inference engine.
- **No new `queued` state yet.** The HTTP response says `"status":
  "queued"` to describe the task operation, but the persisted `AnalysisRun`
  stays `pending` until the worker wins the atomic claim and moves it to
  `processing`. This avoids a premature migration. A race can enqueue two
  tasks before either worker claims the run; this is acceptable because only
  one task can win `claim_for_processing()`, so duplicates cannot create a
  second `Prediction`.
- **Still no real AI/ML, no PyTorch, no dataset, no frontend, no
  authentication, no taxonomy.** Celery changes where the mock processing
  runs, not what it does.

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

As of Fase 16 this collects **448 tests**. On a machine without PostgreSQL,
`pytest -v` reports **394 passed, 54 skipped** (the 54 PostgreSQL-only tests
skip automatically — see § 15):

| Folder | Count | What it covers |
|---|---|---|
| `tests/unit/domain/` | 26 | Entities, value objects, domain invariants (incl. `AnalysisRun` state transitions) — no I/O. |
| `tests/unit/application/` | 150 | Use cases with in-memory fakes (incl. `MockInferenceEngine`, `ProcessAnalysisRunUseCase` idempotency/claim/recovery scenarios, `SubmitHumanReviewUseCase` final-review rollback, curated dataset snapshot/manifest rules, `DatasetSplitter`/`CreateDatasetReleaseUseCase` determinism, leakage-prevention, `by_sample`/`by_lot`/`by_origin_lot` strategy rules, persisted ML preflight creation/rollback rules, majority-class baseline persistence/failure rules, classical tabular baseline gate/persistence/failure rules, `CreateImageDatasetAuditRunUseCase` persistence/rollback rules, and `CreateImageFeatureExtractionRunUseCase` audit-acceptance/persistence/rollback rules) — no database, no filesystem. |
| `tests/unit/infrastructure/` | 18 | `Settings`, Celery app/task configuration, and `PillowImageValidator`, in isolation. |
| `tests/unit/ml/` | 67 | Fase 11 training-manifest contracts, manifest/path validators, JSON loader, CLI exit codes, the intentionally unimplemented `TrainerPort`, the Fase 13 majority-class baseline trainer, the Fase 14 `ImageDatasetAuditor` (passed/warning/failed by cause, per-modality distinction, distributions, determinism, no file mutation, no tensors), the Fase 15 `ImageFeatureExtractor` (geometry/intensity/color/sharpness/texture/histogram correctness, per-modality separation, missing/corrupted-image handling, resize preprocessing, determinism, no large arrays), and the Fase 16 `FeatureMatrixBuilder`/`ClassicalTabularBaselineTrainer` (deterministic tabular matrices, split preservation, real accuracy/confusion metrics, no precision/recall/F1) — no raw image tensors, no PyTorch/TensorFlow, no neural model metrics. |
| `tests/integration/db/` | 28 | Real SQLAlchemy repositories against in-memory SQLite, incl. `claim_for_processing` atomicity, human-review final uniqueness, and real cross-repository transaction rollback. |
| `tests/api/` | 105 | Full FastAPI app via `TestClient`, SQLite + temp storage, incl. idempotency at every non-`pending` status, async eager processing, human-review endpoints, dataset snapshot manifest flow, dataset release/split/manifest flow across all three split strategies, ML preflight persistence/history flow, majority-class and classical-tabular baseline API/history flow, the Fase 14 image-audit flow, and the Fase 15 image-feature-extraction flow (modality/split vector filters, release/audit history listings, rejecting a failed or cross-release audit, no taxonomy/model-metrics leakage). |
| `tests/integration/postgres/` | 54 | **PostgreSQL-only** (Fase 6/8/9/10/12/13/14/15/16): real migrations, JSONB, native ENUMs, partial unique index, CHECK/FK/unique constraints, dataset snapshot/release tables, ML preflight tables, training run/prediction tables, classical baseline model-type constraint, image-dataset-audit tables, image-feature-extraction tables, UUID, and full API smoke flows. Auto-skipped unless `DATABASE_URL` points at PostgreSQL. |

26 + 150 + 18 + 67 + 28 + 105 + 54 = **448**, matching `pytest --collect-only -q`.

(A Fase 3 summary once reported `18 + 21 + 18 + 27 = 84`, which did not add
up — a mislabeled integration-test count that should have read `13`; no
tests were ever double-counted. `18 + 21 + 13 + 27 = 79` was the correct
Fase-3 total; it grew to 102 in Fase 3.5, 136 in Fase 4, 160 in Fase 4.6,
188 in Fase 5, 200 in Fase 6, 208 in Fase 7, 222 in Fase 8, 256 in Fase 9,
289 in Fase 10, 311 in Fase 11, 327 in Fase 12, 340 in Fase 13, 384 in
Fase 14, 432 in Fase 15, and 448 in Fase 16.)

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
- `tests/integration/postgres/` requires a **real PostgreSQL** and is the
  one place that validates PostgreSQL-only behavior — SQLite is never used
  as a stand-in there (see § 15).

SQLite-based tests do not replace validating migrations/constraints against
real PostgreSQL — that is exactly what `tests/integration/postgres/` and the
`postgres-migrations` CI job are designed to do once the workflow is pushed
to GitHub and a successful run is observed (§ 15).

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
- **CI:** `.github/workflows/tests.yml` runs on every push/PR to `main`.
  (As of Fase 6 this now has a second job that stands up real PostgreSQL —
  see § 15; the description here reflects the original Fase 5.5 state.)
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

## 15. Real PostgreSQL validation and CI (Fase 6)

Fase 6 closed the long-standing gap where the schema was only ever exercised
against SQLite. There are now real PostgreSQL tests and a dedicated CI job
configured to run them against a live PostgreSQL service. No new business
functionality was added — this is purely validation infrastructure. See
ARCHITECTURE.md § 20 for the design rationale.

### Running the normal (fast) tests

```bash
pytest -v
```

As of Fase 8, on a machine without PostgreSQL this is **206 passed, 16 skipped** — the 16
PostgreSQL-only tests skip automatically. Nothing fails just because you have
no database.

### Running the PostgreSQL-only tests locally

You need a real PostgreSQL. The simplest way is the bundled Docker Compose
service (§ 4):

```bash
# 1. start PostgreSQL
docker compose up -d          # or point DATABASE_URL at any PostgreSQL you have

# 2. tell the tests (and Alembic) where it is
export DATABASE_URL=postgresql+psycopg://blueberry:blueberry@localhost:5432/blueberry_microid
#   PowerShell: $env:DATABASE_URL = "postgresql+psycopg://blueberry:blueberry@localhost:5432/blueberry_microid"

# 3. run just the PostgreSQL suite
pytest -v -m postgres tests/integration/postgres
```

The `postgres` marker (registered in `pyproject.toml`) tags these tests. The
gate is the `DATABASE_URL` environment variable actually being set to a
`postgresql...` URL — not the app's default, which is a PostgreSQL URL even
when nothing is configured. If it is not set, the tests skip; they never fall
back to SQLite.

`tests/integration/postgres/conftest.py` applies the **real Alembic
migrations** (`downgrade base` → `upgrade head`) against that database before
the tests run, so a green run means the migrations themselves are valid on
PostgreSQL. Each test then runs against a truncated-clean schema.

### What the PostgreSQL tests validate (that SQLite cannot)

- All nine tables are created by the migrations.
- `predictions.class_probabilities` is real `JSONB` (round-trips a dict, the
  `->>` operator works, and the server-side column type is `jsonb`).
- Native `ENUM` columns store the enum **value** (`mock`, `pending`), not the
  Python member name.
- `UUID` columns return real `uuid.UUID` values.
- The partial unique index allows only one `is_final = true` human review per
  analysis run, while permitting many historical (non-final) ones.
- The `CHECK` constraints reject an out-of-range `confidence_score` and a
  `corrected` review missing its `corrected_label`.
- A full API smoke flow (sample → images → analysis run → mock processing →
  prediction → final human review) works end-to-end on PostgreSQL.

### CI

`.github/workflows/tests.yml` has three jobs:

1. `unit-and-api-tests` — installs the project and runs the full suite. It
   does not set `DATABASE_URL`, so the PostgreSQL-only tests skip here.
2. `postgres-migrations` — starts a `postgres:16` service container
   (`blueberry`/`blueberry`, database `blueberry_microid_test`), sets
   `DATABASE_URL`, runs `python scripts/check_postgres_migrations.py` (which
   applies the migrations and verifies they are reversible), then runs
   `pytest -m postgres tests/integration/postgres`.
3. `celery-smoke` — starts PostgreSQL and Redis service containers, applies
   Alembic migrations, starts a real API process and Celery worker, then runs
   `scripts/celery_smoke_test.py`.

No deployment, no Docker image build, and no secrets — the PostgreSQL
credentials in the workflow are throwaway values for an ephemeral CI
database. Validating migrations against a *self-managed/production*
PostgreSQL still uses the same `scripts/check_postgres_migrations.py` (§ 5)
and remains an operational step outside CI.

### CI verification status (Fase 6.5)

Estado B: workflow pushed, verification pending.

On 2026-07-02, the local repository was checked on branch `main` at commit
`7535d6a` (`Add PostgreSQL validation workflow`) before this documentation
update. After user approval, `origin` was configured as
`https://github.com/JaimePergueza/BlueberryIdentifyID.git` and `main` was
pushed successfully. However, no GitHub Actions run could be observed from
this environment: `gh --version` failed because GitHub CLI is not installed,
and an unauthenticated request to the GitHub Actions API returned `404 Not
Found`. PostgreSQL is therefore **not yet validated in CI**.

Manual verification steps:

Open the repository in GitHub, go to **Actions**, select
`.github/workflows/tests.yml`, and verify both jobs:

1. `unit-and-api-tests`
2. `postgres-migrations`

Only after both jobs pass in a real GitHub Actions run may the project be
described as PostgreSQL-validated in CI. If either job fails, record the run
URL/id and the failing log excerpt here before moving to Fase 7.

## 16. Asynchronous mock processing with Celery (Fase 7)

Fase 7 adds Celery/Redis as an execution boundary for the existing mock
processing path. It does **not** add real AI, PyTorch, training, datasets,
metrics, frontend, authentication, taxonomy, or species/genus
identification.

Local operation:

```bash
docker compose up -d redis
celery -A blueberry_microid.infrastructure.tasks.celery_app.celery_app worker --loglevel=info -Q analysis
uvicorn blueberry_microid.interfaces.api.app:create_app --factory --reload
```

Queue processing:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analysis-runs/<analysis_run_id>/process-async
```

The response is `202 Accepted`:

```json
{
  "analysis_run_id": "...",
  "task_id": "...",
  "status": "queued",
  "message": "Analysis processing has been queued"
}
```

Task state can be checked with `GET /api/v1/tasks/<task_id>`, but that is
only auxiliary. The durable source of truth is:

```bash
curl http://127.0.0.1:8000/api/v1/analysis-runs/<analysis_run_id>
curl http://127.0.0.1:8000/api/v1/analysis-runs/<analysis_run_id>/prediction
```

Testing does not require Redis. Tests configure Celery eager mode and use
SQLite/file-backed storage as needed:

```bash
CELERY_TASK_ALWAYS_EAGER=true CELERY_TASK_EAGER_PROPAGATES=true pytest -v
```

The synchronous endpoint remains available:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analysis-runs/<analysis_run_id>/process
```

It is useful for development and tests. For operation-style flows,
`/process-async` is preferred; a later phase may deprecate or protect the
synchronous route.

### Real Redis + worker smoke (Fase 7.5)

Fase 7.5 adds an operational smoke script and CI job to prove the async path
works with a real Redis broker/result backend and a real Celery worker, not
only eager mode.

Manual flow:

```bash
cp .env.example .env
docker compose up -d postgres redis
export DATABASE_URL=postgresql+psycopg://blueberry:blueberry@localhost:5432/blueberry_microid
alembic upgrade head
uvicorn blueberry_microid.interfaces.api.app:create_app --factory --reload
celery -A blueberry_microid.infrastructure.tasks.celery_app.celery_app worker --loglevel=info -Q analysis
python scripts/celery_smoke_test.py
docker compose down
```

In GitHub Actions, the `celery-smoke` job starts ephemeral PostgreSQL and
Redis service containers, applies Alembic migrations, starts a real Celery
worker and API process, then runs `scripts/celery_smoke_test.py`. It does
not use secrets, deploy anything, build Docker images, run real AI, use
PyTorch, or add taxonomy. The main source of truth remains `AnalysisRun` and
`Prediction`; `/tasks/{task_id}` is only an auxiliary Celery status view.

## 17. Curated dataset snapshots and manifests (Fase 8)

Fase 8 adds a dataset curation layer for future training pipelines. It does
not train models, calculate accuracy/precision/recall/F1, download external
datasets, copy image files, add taxonomy, or replace `MockInferenceEngine`.

Entities:

- `DatasetSnapshot` is an immutable dataset version: name, version,
  selection criteria, item count, label distribution, and notes.
- `DatasetItem` is one traceable reference inside a snapshot. It points back
  to the original `AnalysisRun`, `Sample`, `PetriImage`, `MicroImage`,
  `Prediction`, and final `HumanReview`. Image bytes are not copied.

Eligibility rules for trainable items:

- The `AnalysisRun` must exist and must not be `pending` or `processing`.
- A `Prediction` must exist, but it is not enough by itself.
- A final `HumanReview` must exist.
- The referenced Petri and micro images must exist.
- `rejected_invalid_sample` is excluded from trainable items.
- `marked_inconclusive` is excluded by default and included only when
  `include_inconclusive=true`.
- No species/genus/taxonomic label is created or exported.

Ground truth derivation:

- `confirmed`: ground truth is `Prediction.predicted_label`, because the
  final human review accepted that broad visual label.
- `corrected`: ground truth is `HumanReview.corrected_label`.
- `marked_inconclusive`: ground truth is `inconclusive` only when explicitly
  included.
- `rejected_invalid_sample`: excluded from trainable items.

Dataset endpoints:

```bash
POST /api/v1/datasets/snapshots
GET  /api/v1/datasets/snapshots
GET  /api/v1/datasets/snapshots/{dataset_snapshot_id}
GET  /api/v1/datasets/snapshots/{dataset_snapshot_id}/items
GET  /api/v1/datasets/snapshots/{dataset_snapshot_id}/manifest
```

Create example:

```json
{
  "name": "curated-blueberry-v1",
  "version": "0.1.0",
  "description": "Reviewed AnalysisRuns only",
  "created_by": "lab-team",
  "include_inconclusive": false,
  "include_rejected": false
}
```

The manifest response is deterministic and includes snapshot metadata,
`label_distribution`, and item rows with `analysis_run_id`, `sample_code`,
Petri/micro image paths, broad `ground_truth_label`,
`source_review_decision`, original `prediction_label`, `final_review_id`, and
basic Petri/micro metadata. It does not include image binaries, secrets,
model metrics, or taxonomy.

## 18. Dataset releases and deterministic train/validation/test splits (Fase 9)

Fase 9 adds a way to freeze a `DatasetSnapshot` into a reproducible
train/validation/test partition for future training pipelines. It does not
train a model, compute accuracy/precision/recall/F1, download an external
dataset, copy image bytes, add taxonomy, or replace `MockInferenceEngine`.

**`DatasetSnapshot` vs `DatasetRelease`:** a snapshot is *what* is curated
(which `AnalysisRun`s qualify and their ground truth); a release is *how*
that same, unmodified set of items is partitioned for a specific training
run. The same snapshot can have many releases (different seeds, different
ratios, different names/versions) without ever touching the snapshot or its
items — `CreateDatasetReleaseUseCase` only reads them.

Entities:

- `DatasetRelease`: references a `DatasetSnapshot`, records
  `split_strategy`, `random_seed`, the three ratios, item/train/validation/test
  counts, an overall `label_distribution`, and a per-split
  `split_distribution`.
- `DatasetSplitItem`: one `DatasetItem`'s split assignment (`train`,
  `validation`, or `test`) within a specific release, plus a denormalized
  `sample_id` and `ground_truth_label` for direct auditing. A `DatasetItem`
  can appear at most once per release (DB unique constraint on
  `(dataset_release_id, dataset_item_id)`).

**How splitting works (`DatasetSplitter`):** items are grouped by
`sample_id` first; the list of unique sample ids is sorted by their string
form (so incidental database/list ordering never affects the result), then
shuffled with `random.Random(random_seed)`. The shuffled list is sliced into
train/validation/test using `int(total_samples * ratio)` for train and
validation, with test absorbing the remainder — so every sample is assigned
exactly once even when the ratios don't divide evenly, and re-running with
the same seed always reproduces the same partition. **All `DatasetItem`s
that share a `sample_id` are assigned to the same split**, because the unit
of partitioning is the Sample, never the individual item/image — this is
what prevents one sample's Petri/microscopy evidence from leaking across
train and evaluation.

**Known, documented leakage risk this does *not* address:** `Sample.lot_code`
(the batch a sample was collected from) is not considered by the splitter.
Two different Samples from the same lot could still end up in different
splits, and a model could in principle pick up on lot-level artifacts shared
within a batch. This is a real, acknowledged limitation, not an oversight —
see ARCHITECTURE.md § 25 for the full rationale on why sample-level
splitting was implemented now and lot-level splitting was not.

**Small/empty datasets:** requesting a release from a snapshot with zero
`included` items returns `409 empty_dataset_snapshot`. A dataset too small
to populate all three splits (e.g. 2 samples with the default 70/15/15
ratios) does not fail — it still produces a valid release, but
`DatasetSplitter` logs a `WARNING` when at least one split ends up empty, so
this is visible in logs rather than silently accepted.

**Ratios:** default to 70/15/15 (`train_ratio`/`validation_ratio`/`test_ratio`),
configurable per release, and must sum to 1.0 (validated both in the
splitter, before any work happens, and again in the `DatasetRelease` entity
itself as a domain invariant). An invalid combination returns
`422 invalid_split_ratios`.

Dataset release endpoints:

```bash
POST /api/v1/datasets/releases
GET  /api/v1/datasets/releases
GET  /api/v1/datasets/releases/{dataset_release_id}
GET  /api/v1/datasets/releases/{dataset_release_id}/items
GET  /api/v1/datasets/releases/{dataset_release_id}/manifest
```

Create example:

```json
{
  "dataset_snapshot_id": "11111111-1111-1111-1111-111111111111",
  "name": "release-v1",
  "version": "0.1.0",
  "split_strategy": "by_sample",
  "random_seed": 42,
  "train_ratio": 0.70,
  "validation_ratio": 0.15,
  "test_ratio": 0.15,
  "created_by": "lab-team"
}
```

The release manifest is deterministic (sorted by split, then
`analysis_run_id`) and includes release metadata (`split_strategy`,
`ratios`, `counts`, `label_distribution`, `split_distribution`) plus item
rows with `split`, `analysis_run_id`, `sample_id`, `sample_code`, `lot_code`,
`origin`, Petri/micro image paths, `ground_truth_label`,
`source_review_decision`, `prediction_label`, and `final_review_id` — the
same non-taxonomic, non-binary, metric-free shape as the Fase 8 snapshot
manifest, with `split`/`lot_code`/`origin` added so a release can be audited
to confirm which leakage-prevention unit it actually respects. See § 19 for
`by_lot`/`by_origin_lot` (Fase 10).

## 19. Advanced split strategies: `by_sample`, `by_lot`, `by_origin_lot` (Fase 10)

Fase 9's `by_sample` grouping prevents a Sample's own Petri/microscopy
evidence from leaking across train/validation/test, but does **not**
prevent leakage across Samples that share a `lot_code` — a model could
still learn lot-specific conditions (culture medium batch, capture
protocol, incubator, shared contamination) instead of a real
microbiological pattern. Fase 10 adds two stricter grouping strategies. No
model is trained in this phase, and none of this reduces leakage risk to
zero — see the caveat at the end of this section.

**The three strategies (`SplitStrategy`):**

| Strategy | Groups by | Use when |
|---|---|---|
| `by_sample` (default) | `Sample.id` | The baseline for any release; no stricter grouping key is available or required. |
| `by_lot` | `Sample.lot_code` | Multiple Samples share a production/collection lot and you want to rule out the model learning lot-specific artifacts. |
| `by_origin_lot` | `(Sample.origin, Sample.lot_code)` | Samples from different origins can share the same `lot_code` value (e.g. two suppliers numbering lots independently) and you want origin and lot both to define the leakage-prevention unit — the strictest option. |

Each is progressively stricter: `by_lot` is a superset of the guarantee
`by_sample` gives (it also keeps every Sample's own evidence together, since
grouping by lot only ever merges whole Samples, never splits one), and
`by_origin_lot` is a superset of `by_lot`'s guarantee for the same reason.

**Missing metadata never falls back silently.** Requesting `by_lot` when any
relevant Sample has no `lot_code` (or `by_origin_lot` when any Sample is
missing `origin` and/or `lot_code`) fails the whole release with
`422 dataset_split_metadata_error`:

```json
{
  "error": {
    "code": "dataset_split_metadata_error",
    "message": "sample '...' is missing lot_code, required by split_strategy='by_lot'"
  }
}
```

This is deliberate: silently degrading to `by_sample` (or silently excluding
the incomplete Sample) would hide a real leakage risk instead of surfacing
it. The fix is always to complete the Sample's metadata (`lot_code`/
`origin`, settable at `POST /api/v1/samples`) and retry, not to relax the
strategy.

**Where the grouping actually happens.** `DatasetItem` was **not** widened
with `lot_code`/`origin` — it still only carries `sample_id`, unchanged
since Fase 8/9. `CreateDatasetReleaseUseCase` resolves each item's Sample
metadata separately (via `SampleRepositoryPort`, only when
`split_strategy != by_sample`, to avoid the extra lookups on the common
path) and hands `DatasetSplitter` a `sample_id -> SampleSplitMetadata`
lookup alongside the items. The splitter itself never imports the `Sample`
entity — it only knows about this small, purpose-built metadata shape.

**Backward compatibility.** Fase 9 only ever wrote the free-text value
`"random_by_sample"` into `dataset_releases.split_strategy`. Migration
`0005` normalizes any such existing row to `"by_sample"` (semantically
identical — every Fase 9 release was already grouped by `sample_id`) before
adding a `CHECK` constraint restricting the column to the three current
values. `DatasetReleaseCreate`/`CreateDatasetReleaseRequest` both now
default to `by_sample` instead of the old string.

**Manifest and endpoints.** `GET /api/v1/datasets/releases/{id}/manifest`
now includes `split_strategy` at the top level and `sample_id`, `lot_code`,
`origin` per item — a release's manifest alone is now enough to audit which
leakage-prevention unit it respects, without querying the database
separately. No endpoint paths changed; `POST /api/v1/datasets/releases`
accepts `split_strategy` (defaulting to `by_sample` when omitted, so
existing callers are unaffected).

**This reduces leakage risk — it does not eliminate it.** Even
`by_origin_lot` cannot catch every possible confound (e.g. two different
lots processed on the same day by the same technician, or a shared imaging
setup change over time, are not modeled by any of these three strategies).
Choosing a stricter strategy than the data can support is also
counterproductive: it can start starving the smaller splits, which
`DatasetSplitter` already flags with a `WARNING` log line when a partition
ends up empty (see Fase 9).

## 20. ML training manifest contracts and validators (Fase 11)

Fase 11 defines the contract a future training pipeline must satisfy before
any model code exists. It does **not** train, evaluate, or load a model; it
does not add PyTorch, tensors, external datasets, frontend, authentication, or
taxonomy. `MockInferenceEngine` remains the only inference implementation.

The contract starts from the deterministic manifest exported by
`GET /api/v1/datasets/releases/{dataset_release_id}/manifest`. That manifest
already carries reviewed ground truth, split assignment, Petri and microscopy
paths, sample metadata, and the release strategy (`by_sample`, `by_lot`, or
`by_origin_lot`). Fase 11 maps that JSON into:

- `TrainingManifest` / `TrainingManifestItem`
  (`ml/contracts/training_manifest.py`): immutable-ish dataclasses for the
  release manifest shape, including split counts, label distribution, image
  paths, review decision, prediction label, and sample metadata.
- `TrainingConfig` (`ml/configs/training_config.py`): future experiment
  settings and validation thresholds. It records intent only; it is not a
  training runner.
- `ManifestValidationReport` (`ml/reports/validation_report.py`): structured
  errors, warnings, counts, leakage-check booleans, and recommendations.

`ManifestValidator` checks the manifest before any future trainer may run:

- all three splits (`train`, `validation`, `test`) must be present and non-empty;
- every item needs non-empty Petri and microscopy paths;
- labels are limited to the existing preliminary visual categories
  (`no_evident_growth`, `suspicious_growth`, `probable_fungal_growth`,
  `probable_bacterial_growth`, `inconclusive`);
- `inconclusive` is rejected unless `TrainingConfig.allow_inconclusive=True`;
- duplicate `analysis_run_id`s and duplicate item identities are errors;
- a `sample_id` cannot appear in multiple splits;
- `by_lot` and `by_origin_lot` manifests are checked for lot/origin leakage
  using the metadata exported by Fase 10;
- optional minimum total, per-split, and per-label counts are enforced as
  readiness gates, not as performance metrics.

`ImagePathValidator` only checks that referenced Petri/micro paths exist on
disk. It does not open image bytes, decode files, copy images, or infer
anything about the sample. This keeps validation safe for manifests that may
contain large or sensitive image files.

`DatasetLoaderPort` and `JsonManifestDatasetLoader` provide the first loader
contract for future training code: load JSON, validate it, and iterate items by
split. They intentionally return manifest items, not tensors or augmented image
data. `TrainerPort` is a boundary for a future implementation; calling
`train()` now raises `TrainingNotImplementedError` after making clear that real
training is outside this phase.

To validate a manifest manually:

```bash
python scripts/validate_training_manifest.py path/to/dataset_release_manifest.json
```

An optional JSON config can be supplied:

```bash
python scripts/validate_training_manifest.py path/to/manifest.json --config path/to/training_config.json
```

The command prints a JSON validation report and exits `0` only when the
manifest is valid. It exits `1` for validation failures and `2` for load/config
errors. It never calculates accuracy, precision, recall, F1, or any other
model metric.

## 21. Persistent ML preflight reports (Fase 12)

Fase 12 persists the result of the Fase 11 manifest validation so a future
training attempt can be audited before it exists. It still does **not** train a
model, load PyTorch, compute model metrics, download datasets, launch Celery,
or add taxonomy.

`TrainingPreflightRun` records one validation execution for a
`DatasetRelease`: status (`passed`, `warning`, `failed`), `is_valid`, the
exact `TrainingConfig` JSON used, summary counts, split/label distributions,
leakage checks, recommendation text, timestamp, optional `created_by`, and
optional notes. It stores metadata only: no images, no binaries, no secrets,
no model artifacts, no accuracy/precision/recall/F1.

`TrainingPreflightIssue` records every validation finding from the report:
`severity` (`error` or `warning`), a simple code, message, optional field, and
optional item reference. Errors come from `ManifestValidator` and, only when
explicitly requested, `ImagePathValidator`. Warnings remain warnings; a run
with warnings and no errors is persisted as `warning`, not failed.

The persistent API reuses the existing `DatasetReleaseManifestExporter` and
Fase 11 validators. It does not duplicate validation logic in repositories or
routers, and it does not modify `DatasetRelease`, `DatasetSnapshot`,
`DatasetItem`, `Prediction`, or `HumanReview`.

Endpoints:

- `POST /api/v1/ml/preflight-runs`
- `GET /api/v1/ml/preflight-runs`
- `GET /api/v1/ml/preflight-runs/{preflight_run_id}`
- `GET /api/v1/ml/preflight-runs/{preflight_run_id}/issues`
- `GET /api/v1/datasets/releases/{dataset_release_id}/preflight-runs`

The standalone CLI remains useful for local checks:

```bash
python scripts/validate_training_manifest.py path/to/dataset_release_manifest.json
```

It prints a report but does not persist anything. Use the API when an
auditable `TrainingPreflightRun`/`TrainingPreflightIssue` history is required.
A `passed` preflight is only a technical gate result; it does not prove the
dataset is scientifically sufficient or that training should proceed.

## 22. Majority-class baseline training runs (Fase 13)

Fase 13 adds a persisted experimental baseline over an existing
`DatasetRelease`. It is deliberately small: no image decoding, no tensors, no
PyTorch/TensorFlow, no CNN/ViT, no Celery, no external datasets, and no
replacement of `MockInferenceEngine`.

`TrainingRun` stores one baseline execution: release, preflight, run kind,
baseline model type, status, exact `TrainingConfig`, baseline state, metrics,
summary, timestamps, author notes, and any error message. `TrainingPrediction`
stores one prediction per `DatasetSplitItem`, preserving the reviewed
`ground_truth_label`, the baseline `predicted_label`, split, correctness, and
references to the release item. The database enforces allowed statuses,
`run_kind=baseline`, `baseline_model_type=majority_class`, allowed splits,
allowed preliminary labels, FKs, and uniqueness of one prediction per
`(training_run_id, dataset_split_item_id)`.

`MajorityClassBaselineTrainer` uses only the train split labels to choose the
majority preliminary label. Ties are deterministic, using the existing
`PredictedLabel` enum order. It then predicts that same label for all
train/validation/test items. The only metrics recorded are calculated directly
from those predictions: `accuracy_overall`, `accuracy_by_split`,
`support_by_split`, `label_distribution_by_split`, and `confusion_matrix`.
Precision, recall and F1 remain out of scope.

`CreateBaselineTrainingRunUseCase` requires a matching non-failed
`TrainingPreflightRun`, exports and revalidates the release manifest, and then
persists the completed `TrainingRun` plus all `TrainingPrediction`s
transactionally. If manifest revalidation fails, it persists a `failed`
`TrainingRun` with validation errors and no predictions, so the failed attempt
is still auditable.

Endpoints:

- `POST /api/v1/ml/training-runs/baseline`
- `GET /api/v1/ml/training-runs`
- `GET /api/v1/ml/training-runs/{training_run_id}`
- `GET /api/v1/ml/training-runs/{training_run_id}/predictions`
- `GET /api/v1/datasets/releases/{dataset_release_id}/training-runs`
- `GET /api/v1/ml/preflight-runs/{preflight_run_id}/training-runs`

This baseline is not real AI and does not establish scientific performance. It
only provides a reproducible, transparent lower-bound experiment over reviewed
labels for later comparison.

## 23. Image dataset audit reports (Fase 14)

Fase 14 adds a persisted **technical** audit of the Petri/micro image *files*
referenced by a `DatasetRelease` — separate from, and independent of, the
Fase 12 `TrainingPreflightRun` (which validates the manifest's structure:
splits, labels, sample/lot leakage). An image audit answers a narrower
question: are the files themselves technically usable (exist, decode without
corruption, plausible format/dimensions/color mode)? It never opens an image
as a training tensor, never trains a model, and never makes a
microbiological/taxonomic judgment.

`ImageDatasetAuditRun` stores: the release, `status`
(`passed`/`warning`/`failed`), `is_passed` (true for passed/warning, false
for failed — same convention as `TrainingPreflightRun.is_valid`), per-modality
counts (total/checked/failed for Petri and micro separately),
`warning_count`/`error_count`, a `summary` dict, and four JSON distributions
(format, color mode, dimension bucket, file-size bucket). `ImageDatasetAuditIssue`
stores one finding per image: severity, modality (`petri`/`micro`), optional
references to the originating `DatasetItem`/`DatasetSplitItem`, the image
path, a machine-readable `code`, a message, and optional `details`.

`ImageDatasetAuditor` (`ml/validation/image_dataset_auditor.py`) opens each
image with Pillow the same lightweight way `PillowImageValidator` already
does at upload time: `Image.open().verify()` on one handle to catch
corruption, a fresh second `Image.open()` to read format/size/mode. Severity
is fixed by design (documented in the module docstring since several codes
were left as an implementation choice): `image_empty_path`, `image_missing`,
`image_unreadable`, `image_format_mismatch`, and `image_size_bytes_mismatch`
are **errors** (block a clean `passed` audit); `image_too_small`,
`image_too_large`, `image_unsupported_color_mode`, `image_metadata_missing`,
`image_dimension_outlier`, and `image_duplicate_path` are **warnings** (do
not block). `ImageAuditConfig` controls which checks run and their
thresholds — a technical config, not a training config.

`TrainingManifestItem` was extended with eight new optional fields
(`dataset_item_id`, `dataset_split_item_id`, `petri_width`, `petri_height`,
`petri_file_size_bytes`, `micro_width`, `micro_height`,
`micro_file_size_bytes`), populated by `DatasetReleaseManifestExporter` from
the `PetriImage`/`MicroImage` records it already loads — so
`ImageDatasetAuditor` only depends on `TrainingManifest` + `ImageAuditConfig`,
never on the image repositories directly, and `DatasetItem` itself was not
widened.

`CreateImageDatasetAuditRunUseCase` re-exports the release manifest (same
`DatasetReleaseManifestExporter` the preflight uses), runs the auditor, and
persists the run plus all issues transactionally via `UnitOfWorkPort`. It
never modifies `DatasetRelease`, `DatasetItem`, `TrainingRun`, or the image
files, and never touches Celery or PyTorch.

Endpoints:

- `POST /api/v1/ml/image-audits`
- `GET /api/v1/ml/image-audits`
- `GET /api/v1/ml/image-audits/{audit_run_id}`
- `GET /api/v1/ml/image-audits/{audit_run_id}/issues`
- `GET /api/v1/datasets/releases/{dataset_release_id}/image-audits`

A `passed` image audit only certifies basic technical fitness of the image
files — it says nothing about scientific quality, dataset sufficiency, or
microbiological validity.

## 24. Non-deep image feature extraction (Fase 15)

Fase 15 adds a persisted layer that extracts **simple, technical, non-deep**
features from the Petri/micro images referenced by a `DatasetRelease` whose
`ImageDatasetAuditRun` (Fase 14) was not failed. This is a third, independent
layer on top of the Fase 12 preflight (manifest structure) and the Fase 14
audit (file technical fitness): preflight validates the manifest, audit
validates the files, feature extraction computes technical numbers from
those same files. No model is trained; no PyTorch/TensorFlow/CNN/ViT is
used; features have no microbiological meaning.

**New dependency: numpy.** `numpy>=1.24,<2.0` was added explicitly to
`pyproject.toml`. It was already present transitively in this development
environment but not declared — meaning a clean `pip install -e ".[dev]"` in
CI would not have had it. It is used only for array arithmetic (mean,
standard deviation, histogram, a finite-differences Laplacian) — not a deep
learning framework, and not involved in any model training.

`ImageFeatureExtractionRun` records: the release, the audit it was validated
against, `status` (`completed`/`partial`/`failed`), `is_completed` (true for
completed/partial — the run finished running — false only for failed, i.e.
it never got to run extraction at all), the exact
`ImageFeatureExtractionConfig` used, item/vector counts, and a summary.
`ImageFeatureVector` records one Petri or micro image's feature set: run,
release, item, split item, split, modality, path, `features` (JSON),
`preprocessing` (JSON — what was actually applied: RGB conversion, resize,
before/after dimensions), and an `extraction_version` tag (`v1`).

Status design (documented because the spec left the exact rule open): every
image in the manifest is always attempted — one failure never stops the
rest. At the end: no errors -> `completed`; at least one error and
`fail_on_unreadable_image=true` (default) -> `failed`; at least one error and
`fail_on_unreadable_image=false` -> `partial`. This lets a run with some
broken images still persist useful vectors for the images that did work,
while still flagging clearly whether the whole set can be trusted.

`ImageFeatureExtractor` (`ml/preprocessing/image_feature_extractor.py`, a
directory reserved since early phases) opens each image the same two-step
way `PillowImageValidator` and `ImageDatasetAuditor` already do
(`verify()` for corruption, then a fresh read), and computes:

- **Geometry**: `width`, `height`, `aspect_ratio`, real `file_size_bytes`.
- **Intensity**: `mean`/`std`/`min`/`max_intensity` over the grayscale image.
- **Color** (only if the image is RGB/RGBA): `mean_r/g/b`, `std_r/g/b`,
  `mean_saturation` (via `Image.convert("HSV")`).
- **Sharpness**: `laplacian_variance`, a finite-differences discrete
  Laplacian using `numpy.roll` (the border wraps instead of being padded —
  a deliberate, documented simplification for this "approximate" metric).
- **Texture**: `edge_density` (gradient-magnitude threshold),
  `dark_pixel_ratio`, `bright_pixel_ratio`.
- **Histogram**: `grayscale_histogram` with N bins (`histogram_bins`,
  default 16), normalized to sum to 1.0.

Everything is deterministic; no randomness is involved anywhere.

`CreateImageFeatureExtractionRunUseCase` follows the same shape as
`CreateBaselineTrainingRunUseCase` (Fase 13) and
`CreateImageDatasetAuditRunUseCase` (Fase 14): look up the release, look up
the audit, verify the audit belongs to that release and its status is
acceptable per `require_audit_passed`/`allow_audit_warning` (a `failed`
audit is never accepted, regardless of config), re-export the manifest, run
the extractor, and persist the run plus every vector transactionally. It
never modifies `DatasetRelease`, `DatasetItem`, or `ImageDatasetAuditRun`.

Endpoints:

- `POST /api/v1/ml/image-feature-extractions`
- `GET /api/v1/ml/image-feature-extractions`
- `GET /api/v1/ml/image-feature-extractions/{feature_extraction_run_id}`
- `GET /api/v1/ml/image-feature-extractions/{feature_extraction_run_id}/vectors` (optional `modality`/`split` filters)
- `GET /api/v1/datasets/releases/{dataset_release_id}/image-feature-extractions`
- `GET /api/v1/ml/image-audits/{image_audit_run_id}/feature-extractions`

These features are purely technical measurements of the image files. They
are not a microbiological finding, not a growth/contamination indicator, and
not a step toward taxonomic identification.

## 25. Classical tabular baseline over image features (Fase 16)

Fase 16 adds the first baseline that actually uses the persisted
`ImageFeatureVector` rows from Fase 15. It is still a classical/tabular
experiment, not deep learning: no PyTorch, no TensorFlow, no CNN/ViT, no raw
image tensors, no model artifact serialization, no external datasets, no
frontend, and no taxonomy.

`TabularFeatureTrainingConfig` selects the completed
`ImageFeatureExtractionRun`, modality strategy (`petri_only`, `micro_only`,
or `concatenate`), standardization, logistic-regression parameters, minimum
train counts/classes, and whether inconclusive labels are allowed. At least
one modality must be selected. `partial` or `failed` extractions are rejected
by default.

`FeatureMatrixBuilder` receives only persisted feature vectors plus
`DatasetSplitItem`s. It flattens numeric feature JSON deterministically,
expands small numeric histograms into columns, prefixes names by modality
(for example `petri__intensity__mean_intensity`), keeps a stable sorted
`feature_names` list, and builds `X_train`, `X_validation`, and `X_test`
without mixing splits. Labels (`y`) come only from
`DatasetSplitItem.ground_truth_label`, never from `Prediction`.

`ClassicalTabularBaselineTrainer` fits scikit-learn
`LogisticRegression` on train only. Validation/test are used only after fit
to generate predictions and metrics. The persisted metrics are real
calculations from `TrainingPrediction`: `accuracy_overall`,
`accuracy_by_split`, `support_by_split`, `label_distribution_by_split`,
`confusion_matrix`, and `confusion_matrix_by_split`. Precision, recall and F1
remain out of scope.

`CreateClassicalBaselineTrainingRunUseCase` requires: existing
`DatasetRelease`; matching non-failed `TrainingPreflightRun`; completed
`ImageFeatureExtractionRun` for that release; available feature vectors; and
at least the configured number of train items/classes. A data-shape failure
(for example one train class) is persisted as a `TrainingRun` with
`status=failed` and no predictions; invalid gates return a controlled
conflict. Successful runs persist the completed `TrainingRun` plus one
`TrainingPrediction` per split item transactionally.

Endpoint:

- `POST /api/v1/ml/training-runs/classical-baseline`

The older `POST /api/v1/ml/training-runs/baseline` majority-class endpoint
remains as a label-only comparison baseline.

## 26. Training run comparison reports (Fase 17)

Fase 17 adds a persisted comparison layer for baseline candidates. It does
not train anything: it only reads completed `TrainingRun` rows that already
belong to the same `DatasetRelease` and already have persisted metrics from
Fase 13 or Fase 16.

`TrainingRunComparison` stores the release, name, primary metric
(`accuracy` only), primary split (`validation` or `test`), selection policy,
optional selected `TrainingRun`, a JSON summary, warnings, author, and notes.
`TrainingRunComparisonEntry` stores one immutable metrics snapshot per run:
rank, model type, accuracy by split, support by split, generalization gap,
and the original metrics JSON. It references the source `TrainingRun`; it
does not copy predictions or images.

`TrainingRunComparator` rejects comparisons that would be misleading:
fewer than two runs, mixed releases, non-completed runs, missing metrics,
missing primary split accuracy, or missing primary split support. Ranking is
descending by the selected accuracy split. `prefer_simpler_if_tie` uses the
documented simplicity order (`majority_class` before
`logistic_regression_tabular`); `no_auto_selection` still ranks entries but
does not mark a candidate.

Warnings are metadata, not failures. A low-support warning is recorded when
the primary split has very few items, so the report can be audited without
pretending that the comparison is scientifically strong.

Endpoints:

- `POST /api/v1/ml/training-run-comparisons`
- `GET /api/v1/ml/training-run-comparisons`
- `GET /api/v1/ml/training-run-comparisons/{comparison_id}`
- `GET /api/v1/ml/training-run-comparisons/{comparison_id}/entries`
- `GET /api/v1/datasets/releases/{dataset_release_id}/training-run-comparisons`

This phase adds no PyTorch, TensorFlow, CNN, ViT, raw image tensors, new
dataset, external tracker, frontend, authentication, taxonomy, model
artifact, or new business prediction path. It also does not replace
`MockInferenceEngine`.

## 27. External microbiology CV landscape review (Fase 18)

Fase 18 adds the documentation-only reference map:

```text
docs/references/microbiology_cv_landscape.md
```

Use it before proposing external computer-vision adoption. It classifies
YOLOv5-style bacteria detection, MEMTrack, DIBaS, Petri colony detection
work, clinical bacterial datasets, surveys/reviews, and unresolved
CSI-Microbes/SinfNet leads by modality, compatibility, risk, and recommended
use.

The document does not authorize installing external dependencies or importing
external data. Any future adoption still needs its own phase, license review,
domain-gap review, tests, and explicit user approval. In particular, do not
add YOLO, PyTorch, TensorFlow, CNN, ViT, deep learning, external datasets,
frontend, authentication, taxonomy, MLflow, TensorBoard, W&B, or a
replacement for `MockInferenceEngine` based only on this landscape review.

Recommended next direction from the review: a constrained classical Petri
colony segmentation prototype, because it can use current Petri imagery and
does not require bounding-box annotations or deep-learning infrastructure.

## 28. Classical Petri segmentation prototype (Fase 19)

Fase 19 adds the persisted classical Petri segmentation layer:

- `PetriSegmentationConfig` controls a single allowed algorithm,
  `classical_threshold`, with `otsu`, `adaptive`, or `manual` thresholding,
  optional blur/morphology, area/circularity/border filters, `max_regions`,
  and version `petri_classical_v1`.
- `ClassicalPetriSegmenter` consumes a `TrainingManifest`, reads only
  `petri_image_path`, and ignores `micro_image_path`.
- `PetriSegmentationRun` stores release/audit reference, status
  (`completed`, `partial`, `failed`), config, counts, and summary.
- `PetriSegmentationRegion` stores one geometric candidate region: area,
  perimeter, centroid, bounding box, circularity, solidity, mean intensity,
  split, and references to `DatasetItem`/`DatasetSplitItem`.

Dependency note: this phase adds `opencv-python-headless>=4.9,<4.11`.
OpenCV 4.13 was avoided because it requires `numpy>=2`, while this project
intentionally keeps `numpy<2.0`. OpenCV is used only for classical processing
(grayscale/color conversion, blur, thresholding, morphology, contours,
bounding boxes, geometry). Do not use OpenCV DNN, YOLO, pretrained models,
PyTorch, TensorFlow, CNN, ViT, or deep learning here.

Endpoints:

- `POST /api/v1/ml/petri-segmentations`
- `GET /api/v1/ml/petri-segmentations`
- `GET /api/v1/ml/petri-segmentations/{segmentation_run_id}`
- `GET /api/v1/ml/petri-segmentations/{segmentation_run_id}/regions`
- `GET /api/v1/datasets/releases/{dataset_release_id}/petri-segmentations`
- `GET /api/v1/ml/image-audits/{image_audit_run_id}/petri-segmentations`

A "candidate region" is only a geometric segment from a classical image
pipeline. It is not a confirmed colony, not a microbiological diagnosis, not
taxonomy, and not model performance. The original images are never modified;
masks and image bytes are not stored in the database.

## 29. Human review of Petri segmentation regions (Fase 20)

Fase 20 adds a persistent human-review layer for the candidate regions
produced by the Fase 19 classical segmenter, before any future use of those
regions to train a real object detector (YOLO) or supervised segmentation
model.

- `PetriRegionReview` records a reviewer's decision about one
  `PetriSegmentationRegion`. It never mutates the original region — a
  corrected bounding box, if supplied, is stored only on the review row.
- `PetriRegionReviewDecision` has exactly four values: `candidate_valid`,
  `candidate_false_positive`, `candidate_uncertain`, `needs_resegmentation`.
  None of them assert a confirmed colony or a taxonomic identification.
- "Final review" follows the same pattern as `HumanReview` (Fase 5): at most
  one `PetriRegionReview` per region can have `is_final=True` at a time,
  enforced by a partial unique index and a demote-then-add transactional
  sequence in `SubmitPetriRegionReviewUseCase`.
- `PetriReviewedAnnotationManifestExporter` exports a deterministic JSON
  manifest of reviewed regions for one `PetriSegmentationRun`: only final
  reviews by default (`include_non_final=true` adds historical ones), with
  `original_bbox`, an optional `corrected_bbox`, and an `effective_bbox`
  (the corrected one if present, otherwise the original). There is no YOLO
  export format or label files yet — that remains out of scope until an
  explicit future phase.

Endpoints:

- `POST /api/v1/ml/petri-regions/{region_id}/reviews`
- `GET /api/v1/ml/petri-regions/{region_id}/reviews`
- `GET /api/v1/ml/petri-regions/{region_id}/reviews/final`
- `GET /api/v1/ml/petri-segmentations/{segmentation_run_id}/region-reviews`
- `GET /api/v1/datasets/releases/{dataset_release_id}/petri-region-reviews`
- `GET /api/v1/ml/petri-segmentations/{segmentation_run_id}/reviewed-annotations-manifest`

No PyTorch, TensorFlow, YOLO, CNN, ViT, deep learning, real model training,
external datasets, or taxonomy are introduced in this phase, and
`MockInferenceEngine` is not replaced.

## 30. Supervised Petri annotation exports (Fase 21)

Fase 21 converts final human reviews of Petri candidate regions into
supervised annotation export formats for future training. It still does not
train anything.

- `PetriAnnotationExportRun` stores one export attempt for a
  `DatasetRelease` + `PetriSegmentationRun`: format, status
  (`completed`, `partial`, `failed`), config, output manifest JSON, counts,
  summary, creator/notes, and optional error message.
- `PetriAnnotationExportItem` stores one exported annotation: references to
  the export run, final `PetriRegionReview`, original
  `PetriSegmentationRegion`, dataset item/split item, split, Petri image
  path, generic label, bbox, bbox source (`corrected` or `original`), and a
  per-item JSON payload. It never stores images, masks, or taxonomy.
- `PetriAnnotationExporter` selects reviews deterministically. By default it
  uses only `is_final=True` reviews with decision `candidate_valid`. It uses
  a corrected bbox when present and allowed; otherwise it falls back to the
  original segmentation bbox. `candidate_false_positive`,
  `candidate_uncertain`, and `needs_resegmentation` are not positive
  training objects by default.
- Supported formats are `blueberry_manifest`, `coco_json`, and `yolo_txt`.
  COCO is only annotation JSON. YOLO is only a label-line manifest in JSON
  (`0 x_center y_center width height`), not a YOLO model or training path.

Endpoints:

- `POST /api/v1/ml/petri-annotation-exports`
- `GET /api/v1/ml/petri-annotation-exports`
- `GET /api/v1/ml/petri-annotation-exports/{export_run_id}`
- `GET /api/v1/ml/petri-annotation-exports/{export_run_id}/items`
- `GET /api/v1/ml/petri-annotation-exports/{export_run_id}/manifest`
- `GET /api/v1/datasets/releases/{dataset_release_id}/petri-annotation-exports`
- `GET /api/v1/ml/petri-segmentations/{petri_segmentation_run_id}/annotation-exports`

This phase does not copy images by default, does not write label files to
disk, does not train YOLO or any other model, and does not add PyTorch,
TensorFlow, CNN, ViT, deep learning, external datasets, frontend,
authentication, taxonomy, MLflow, TensorBoard, or W&B.

## 31. Annotation export bundles (Fase 22)

Fase 22 packages a persisted `PetriAnnotationExportRun` into an auditable
annotation bundle for future supervised training workflows. It still does
not train anything.

- `AnnotationBundleConfig` controls dry-run planning, output directory,
  overwrite behavior, included formats (`blueberry_manifest`, COCO JSON,
  YOLO label files, `dataset.yaml`, README), validation, and split
  directory preservation. `copy_images=true` is intentionally rejected in
  this phase.
- `AnnotationBundleRun` stores the bundle attempt linked to
  `PetriAnnotationExportRun`, `DatasetRelease`, and `PetriSegmentationRun`,
  with status (`dry_run`, `completed`, `failed`), counts, config,
  validation summary, bundle manifest, output directory, creator/notes, and
  optional error message.
- `AnnotationBundleFile` stores metadata for each planned or written file:
  role, absolute path, relative path, content type, size, checksum, and
  bundle reference. It never stores image bytes.
- `AnnotationBundleValidator` checks persisted export data before writing:
  bbox geometry, splits, optional image existence, supported format payloads,
  and label/category/name fields for forbidden taxonomy-like terms.
- `AnnotationBundleWriter` produces deterministic bundle content. Dry-run
  mode persists the planned file list without writing. Real mode writes
  text/JSON/YAML files only: README, Blueberry manifest, COCO annotations,
  YOLO label `.txt` files, `dataset.yaml`, and `manifest.json`.

Endpoints:

- `POST /api/v1/ml/annotation-bundles`
- `GET /api/v1/ml/annotation-bundles`
- `GET /api/v1/ml/annotation-bundles/{bundle_run_id}`
- `GET /api/v1/ml/annotation-bundles/{bundle_run_id}/files`
- `GET /api/v1/datasets/releases/{dataset_release_id}/annotation-bundles`
- `GET /api/v1/ml/petri-annotation-exports/{export_run_id}/annotation-bundles`

YOLO in this phase means only label text format. The bundle does not copy
images by default, does not include binaries, does not train or evaluate a
model, does not add PyTorch/TensorFlow/CNN/ViT/deep learning, does not
download datasets, does not add frontend/authentication/taxonomy, and does
not replace `MockInferenceEngine`.

## 32. Supervised annotation quality gates (Fase 23)

Fase 23 adds a persisted technical quality gate for an `AnnotationBundleRun`.
It answers whether a generated supervised annotation bundle is technically
ready for a future training workflow. It does not train, score, or approve a
model.

- `AnnotationQualityGateConfig` defines thresholds and policies for completed
  bundle status, expected files, COCO/Yolo/Blueberry manifest checks, split
  support, bbox size, empty splits, duplicate boxes, images without
  annotations, single-class warnings, allowed splits, and allowed categories.
  Allowed categories must remain non-taxonomic.
- `AnnotationQualityGateRun` stores the auditable result for one
  `AnnotationBundleRun`: status (`passed`, `warning`, `failed`), counts by
  split, error/warning counts, quality summary, bbox statistics, category
  distribution, config, creator/notes, and optional error message.
- `AnnotationQualityGateIssue` stores each blocking error or warning:
  severity, code, message, optional split/image/annotation reference, and JSON
  details. It stores metadata only, never full file contents or images.
- `AnnotationQualityGateValidator` checks bundle state, expected files,
  manifest consistency, allowed categories, splits, bbox validity, duplicate
  bboxes, support thresholds, images without annotations, COCO consistency,
  and YOLO label-line syntax. YOLO here remains label text format only.

Statuses:

- `passed`: no blocking errors and no warnings under the selected config.
- `warning`: no blocking errors, but reviewable warnings exist.
- `failed`: at least one blocking technical error exists.

Endpoints:

- `POST /api/v1/ml/annotation-quality-gates`
- `GET /api/v1/ml/annotation-quality-gates`
- `GET /api/v1/ml/annotation-quality-gates/{quality_gate_run_id}`
- `GET /api/v1/ml/annotation-quality-gates/{quality_gate_run_id}/issues`
- `GET /api/v1/datasets/releases/{dataset_release_id}/annotation-quality-gates`
- `GET /api/v1/ml/annotation-bundles/{annotation_bundle_run_id}/quality-gates`

A passed quality gate means only technical readiness by configured checks. It
does not imply scientific sufficiency, microbiological diagnosis, taxonomy,
or model performance. This phase does not implement or train YOLO, does not
use PyTorch/TensorFlow/CNN/ViT/deep learning, does not download datasets, and
does not replace `MockInferenceEngine`.

## 33. Object detection training dry-run (Fase 24)

Fase 24 prepares the architecture for a future real object-detection
training phase — it never trains anything. It is a planning-only layer:
`status=planned` never means a model was trained.

- `DetectionTrainingConfig` (`ml/configs/detection_training_config.py`)
  defaults to `algorithm=yolo_dry_run`, `mode=dry_run`, `device="cpu"`, and
  `allow_external_weights=false`. It does not require or check a GPU, and
  `pretrained_weights_path` is never downloaded or validated remotely. If
  `allow_external_weights=true`, only a warning is recorded — nothing is
  fetched.
- `DetectionTrainingRun` persists a training plan: references to the
  `AnnotationBundleRun`, `AnnotationQualityGateRun`, `DatasetRelease`, and
  `PetriAnnotationExportRun` involved; `status` (`planned`, `blocked`,
  `failed`); `is_runnable`; and JSON `config`, `training_plan`,
  `command_preview`, `dataset_summary`, `quality_gate_summary`, and
  `expected_outputs`.
- `DetectionTrainingIssue` stores planning-time findings only — severity
  `error`/`warning`/`info`, a code (e.g. `quality_gate_not_passed`,
  `dataset_yaml_missing`, `yolo_labels_missing`, `no_training_executed`,
  `external_weights_requested`), and a message. No weights, images, or full
  label sets are ever stored.
- `ObjectDetectionTrainerPort.plan_training(...)` is a planning-only
  contract: implementations must never call `subprocess`, never import
  `ultralytics` or `torch`, never write model weights, and never download
  anything. `YoloDryRunTrainer` is the only implementation: it validates the
  requested algorithm/mode, that the bundle is `completed`, that the quality
  gate is `passed` (when required), and that `dataset.yaml`/YOLO label files
  exist, then builds a `command_preview` (a JSON description of the YOLO
  command that *would* run, never executed) and `expected_outputs` (planned
  paths for weights/metrics/predictions, never created on disk).
- `CreateDetectionTrainingRunUseCase` requires the referenced
  `AnnotationQualityGateRun` to belong to the referenced
  `AnnotationBundleRun` (otherwise 409 `detection_training_not_allowed`).
  It never modifies the bundle or quality gate, and persists `planned` when
  everything checks out, `blocked` when prerequisites are missing, or
  `failed` only on an internal planning error.

Endpoints:

- `POST /api/v1/ml/detection-training-runs`
- `GET /api/v1/ml/detection-training-runs`
- `GET /api/v1/ml/detection-training-runs/{detection_training_run_id}`
- `GET /api/v1/ml/detection-training-runs/{detection_training_run_id}/issues`
- `GET /api/v1/datasets/releases/{dataset_release_id}/detection-training-runs`
- `GET /api/v1/ml/annotation-bundles/{annotation_bundle_run_id}/detection-training-runs`
- `GET /api/v1/ml/annotation-quality-gates/{quality_gate_run_id}/detection-training-runs`

This phase does not train YOLO or any model, does not install `ultralytics`,
does not import `torch`, does not use PyTorch/TensorFlow/CNN/ViT/real deep
learning, does not download external weights or datasets, does not require a
GPU, does not create weight files (`.pt`/`.onnx`/`.h5`), does not add a
frontend/authentication/taxonomy/diagnosis claim, does not integrate
MLflow/TensorBoard/W&B, and does not replace `MockInferenceEngine`.

## 34. Detection training readiness report (Fase 25)

Fase 25 evaluates whether a dry-run `DetectionTrainingRun` (Fase 24) is
technically ready to move to a future real training phase. It never trains
anything, never installs `ultralytics`, and never imports `torch`.

- `DetectionTrainingReadinessConfig` (`ml/configs/detection_training_readiness_config.py`)
  has 22 fields: `require_*` booleans for each technical gate (planning
  state, bundle completed, quality gate passed, `dataset.yaml`, YOLO labels,
  minimum data), eight per-split minimums, `warn_if_copy_images_disabled`,
  environment flags (`require_training_executor`,
  `require_ultralytics_installed`, `require_torch_installed`, `require_gpu`,
  `allow_cpu_training_future`), an external-weights policy pair, and
  `strict_mode`. By default no environment dependency is required.
- `DetectionTrainingReadinessReport` persists `decision` (one of
  `ready_for_training`, `needs_more_annotations`, `blocked_by_quality`,
  `blocked_by_environment`, `blocked_by_contract`,
  `blocked_by_configuration`), `status` (`ready`/`warning`/`blocked`/`failed`),
  `is_ready`, and seven JSON summaries (`data_summary`, `split_summary`,
  `quality_summary`, `environment_summary`, `contract_summary`,
  `risk_summary`, `recommendation_summary`). Unlike `DetectionTrainingRun`, a
  report can be `status=warning` with `is_ready=true` — non-blocking
  warnings (e.g. `copy_images_disabled`) do not prevent readiness.
  `DetectionTrainingReadinessIssue` stores severity-tagged findings with
  fixed codes; neither entity stores images, weights, or full label sets.
- `DetectionTrainingReadinessEvaluator` (`application/services/`) only
  inspects already-persisted metadata across seven sections (dry-run state,
  bundle, quality gate, minimum data, contract, environment, categories). It
  never calls `subprocess`, never imports `ultralytics`/`torch`, never
  queries a real GPU, and never modifies files. When
  `require_ultralytics_installed`/`require_torch_installed`/`require_gpu` is
  requested, the evaluator always blocks — there is no safe way to confirm
  those without installing/importing them, so it never tries. When several
  blocking categories co-occur, the decision priority is contract > quality
  > environment > configuration > data.
- `CreateDetectionTrainingReadinessReportUseCase` looks up the
  `DetectionTrainingRun` (404 if missing), its issues, the associated
  `AnnotationBundleRun`/files, and the `AnnotationQualityGateRun`/issues (if
  any), runs the evaluator, and persists the report plus issues in one
  `UnitOfWorkPort` transaction. It never modifies `DetectionTrainingRun`,
  `AnnotationBundleRun`, or `AnnotationQualityGateRun`. An internal
  evaluation failure becomes a persisted `status=failed`/
  `decision=blocked_by_contract` report, never an unpersisted exception.

Endpoints:

- `POST /api/v1/ml/detection-training-readiness-reports`
- `GET /api/v1/ml/detection-training-readiness-reports`
- `GET /api/v1/ml/detection-training-readiness-reports/{readiness_report_id}`
- `GET /api/v1/ml/detection-training-readiness-reports/{readiness_report_id}/issues`
- `GET /api/v1/ml/detection-training-runs/{detection_training_run_id}/readiness-reports`
- `GET /api/v1/datasets/releases/{dataset_release_id}/detection-training-readiness-reports`
- `GET /api/v1/ml/annotation-bundles/{annotation_bundle_run_id}/detection-training-readiness-reports`
- `GET /api/v1/ml/annotation-quality-gates/{quality_gate_run_id}/detection-training-readiness-reports`

This phase does not train YOLO or any model, does not install `ultralytics`,
does not import `torch`, does not use PyTorch/TensorFlow/CNN/ViT/real deep
learning, does not download external weights or datasets, does not require a
GPU, does not create weight files, does not add a
frontend/authentication/taxonomy/diagnosis claim, does not integrate
MLflow/TensorBoard/W&B, does not use Celery, and does not replace
`MockInferenceEngine`. A `ready_for_training` report never certifies
scientific validity or a trained model — only that the configured technical
gates passed.

## 35. Training environment specification (Fase 26)

Fase 26 defines, validates, and persists a specification of the environment
a future real detection-training attempt would need, given a
`DetectionTrainingRun` that already has a `DetectionTrainingReadinessReport`
(Fase 25). It never installs dependencies, never imports
`ultralytics`/`torch`, and never trains anything.

- `DetectionTrainingEnvironmentConfig`
  (`ml/configs/detection_training_environment_config.py`) has 22 fields:
  optional `target_python_version`/`target_os`, `allow_cpu_training=true`,
  `require_gpu`/`require_cuda=false` with an optional
  `target_cuda_version`, `require_ultralytics`/`require_torch=false` with
  optional target versions, `allow_dependency_installation=false`,
  a weights policy triplet (`allow_external_weights=false`,
  `pretrained_weights_policy="none"`, `pretrained_weights_path`), an
  artifact-storage policy (`artifact_output_dir`,
  `allow_artifacts_outside_repo=true`/`allow_artifacts_inside_repo=false`,
  `max_expected_artifact_size_mb`), an execution policy
  (`allow_ci_training=false`, `allow_local_training=true`,
  `require_manual_confirmation=true`), and `strict_mode`/`notes`. No
  `require_*` flag ever triggers a real install, import, or download — it
  only changes which issues the evaluator reports.
- `DetectionTrainingEnvironmentSpec` persists `decision` (one of
  `environment_ready`, `needs_manual_setup`,
  `blocked_by_missing_requirements`, `blocked_by_policy`,
  `blocked_by_unsupported_platform`, `blocked_by_storage_policy`,
  `blocked_by_dependency_policy`), `status`
  (`ready`/`warning`/`blocked`/`failed`), `is_environment_ready`, and seven
  JSON policy/summary fields (`detected_environment`, `dependency_policy`,
  `hardware_policy`, `artifact_policy`, `execution_policy`,
  `setup_instructions`, `safe_check_summary`, plus
  `risk_summary`/`recommendation_summary`). Like Fase 25, a spec can be
  `status=warning` with `is_environment_ready=true`.
  `DetectionTrainingEnvironmentIssue` stores severity-tagged findings with
  fixed codes; neither entity stores images, weights, or full label sets.
- `DetectionTrainingEnvironmentEvaluator` (`application/services/`) only
  uses safe, non-invasive checks: `sys.version_info`, `platform.system()`,
  `importlib.util.find_spec(...)` to detect `ultralytics`/`torch`
  availability **without importing them**, `pathlib` for
  `artifact_output_dir` existence/location **without writing files by
  default**, and `os.environ` only to detect CI variables (`CI`,
  `GITHUB_ACTIONS`) informationally. It never calls `subprocess`, never
  queries real GPU/CUDA, never installs or downloads anything, and never
  modifies project files. `require_gpu=true`/`require_cuda=true` always
  block (`blocked_by_missing_requirements`) — there is no safe way to
  confirm those without external commands. If the referenced
  `DetectionTrainingReadinessReport` is `blocked`/`failed`, or its
  `decision` isn't `ready_for_training`, the spec is blocked
  (`readiness_not_ready`) before anything else is evaluated.
  `allow_ci_training=true` is always a blocking error
  (`blocked_by_policy`); detecting that the evaluation itself is running
  inside a CI job only produces a non-blocking **warning** with the same
  code — this keeps the project's own GitHub Actions test run from
  breaking, since running this evaluation from a CI job does not by itself
  mean a future real training step would run there.
- `CreateDetectionTrainingEnvironmentSpecUseCase` looks up the
  `DetectionTrainingRun` and `DetectionTrainingReadinessReport` (404 if
  missing), verifies the readiness report belongs to the run (otherwise
  409 `detection_training_environment_not_allowed`), looks up the
  associated `AnnotationBundleRun`, runs the evaluator, and persists the
  spec plus issues in one `UnitOfWorkPort` transaction. It never modifies
  `DetectionTrainingRun`, `DetectionTrainingReadinessReport`, or
  `AnnotationBundleRun`. An internal evaluation failure becomes a
  persisted `status=failed` spec, never an unpersisted exception.

Endpoints:

- `POST /api/v1/ml/detection-training-environment-specs`
- `GET /api/v1/ml/detection-training-environment-specs`
- `GET /api/v1/ml/detection-training-environment-specs/{environment_spec_id}`
- `GET /api/v1/ml/detection-training-environment-specs/{environment_spec_id}/issues`
- `GET /api/v1/ml/detection-training-runs/{detection_training_run_id}/environment-specs`
- `GET /api/v1/ml/detection-training-readiness-reports/{readiness_report_id}/environment-specs`
- `GET /api/v1/ml/annotation-bundles/{annotation_bundle_run_id}/detection-training-environment-specs`
- `GET /api/v1/datasets/releases/{dataset_release_id}/detection-training-environment-specs`

This phase does not train YOLO or any model, does not install
`ultralytics`, does not import `torch`, does not use
PyTorch/TensorFlow/CNN/ViT/real deep learning, does not download external
weights or datasets, does not run training in CI, does not require a GPU,
does not create weight files, does not add a
frontend/authentication/taxonomy/diagnosis claim, does not integrate
MLflow/TensorBoard/W&B, and does not replace `MockInferenceEngine`. An
`environment_ready` spec never certifies that a real training environment
was provisioned — only that the configured technical gates passed.

## 36. Training artifact policy & registry (Fase 27)

Fase 27 defines, validates, and persists an artifact policy for a future
real detection-training attempt, given a `DetectionTrainingRun` that
already has a `DetectionTrainingReadinessReport` (Fase 25) and a
`DetectionTrainingEnvironmentSpec` (Fase 26). It never trains anything and
never creates real weight files.

- `DetectionTrainingArtifactPolicyConfig` (`ml/configs/`) has 22 fields: an
  optional `artifact_root_dir` with `require_artifact_root_dir=true`, a
  repo-storage policy (`allow_artifacts_inside_repo=false`/
  `allow_artifacts_outside_repo=true`), an external-URI policy
  (`allow_external_uri=false`, `allowed_external_uri_schemes=[]`), an
  extension policy (`forbidden_extensions` defaulting to
  `.pt`/`.pth`/`.onnx`/`.h5`/`.ckpt`/`.pb`/`.tflite`,
  `allowed_metadata_extensions` defaulting to
  `.json`/`.yaml`/`.yml`/`.txt`/`.csv`/`.md`), a Git policy
  (`require_gitignore_rules=true`, `required_gitignore_patterns`), a
  checksum policy (`require_checksums_for_actual_artifacts=true`,
  `checksum_algorithm="sha256"`, optional `max_artifact_size_mb`), a
  registry policy (`allow_actual_artifact_registration=false`,
  `register_planned_artifacts=true`, `register_actual_artifacts=false`,
  `allow_missing_planned_paths=true`), and `strict_mode`/`notes`. No field
  ever creates `artifact_root_dir`, writes an artifact file, or computes a
  real checksum — this phase has no mechanism to produce a real artifact.
- `DetectionTrainingArtifactPolicy` persists `decision` (one of
  `artifact_policy_ready`, `needs_external_storage`,
  `blocked_by_repo_storage`, `blocked_by_missing_output_dir`,
  `blocked_by_forbidden_extension`, `blocked_by_policy_violation`,
  `blocked_by_environment`), `status` (`ready`/`warning`/`blocked`/
  `failed`), `is_policy_ready`, an optional `artifact_root_dir`, and seven
  JSON policy/summary fields (`planned_output_summary`, `storage_policy`,
  `git_policy`, `checksum_policy`, `registry_summary`, `risk_summary`,
  `recommendation_summary`). Like Fases 25-26, a policy can be
  `status=warning` with `is_policy_ready=true`, but `is_policy_ready=true`
  always requires `decision=artifact_policy_ready`.
  `DetectionTrainingArtifactRecord` represents a planned (or, in a future
  explicit phase, real) artifact — `artifact_kind`, `artifact_state`,
  `location_type`, optional path/URI fields, `file_extension`,
  `size_bytes`, `checksum_sha256`, and optional JSON `metadata` — without
  ever storing binary content. `DetectionTrainingArtifactIssue` stores
  severity-tagged findings with fixed codes; none of the three entities
  stores weights, images, or full label sets.
- `DetectionTrainingArtifactPolicyEvaluator` (`application/services/`)
  takes the `DetectionTrainingRun`, `DetectionTrainingEnvironmentSpec`,
  `AnnotationBundleRun`+files, and config — it deliberately does not take
  the `DetectionTrainingReadinessReport`, because none of its rules depend
  on a field of that entity (only on the environment spec's
  `status`/`decision`); readiness-report membership checks live in the use
  case instead, to avoid duplicating a validation that belongs elsewhere.
  It only uses safe, read-only checks: `pathlib` for
  `artifact_root_dir` location **without writing anything**, and reading
  `.gitignore` if present **without ever modifying it**. It never calls
  `subprocess`, never imports `torch`/`ultralytics`, never installs
  dependencies, never downloads anything, never computes a real checksum
  (no real artifact exists to hash), and never creates a weight file. If a
  planned `expected_output` (`weights_path_planned`,
  `metrics_path_planned`, `predictions_path_planned`, `run_dir_planned`)
  points inside the repo with a forbidden extension, it blocks
  (`blocked_by_repo_storage`/`blocked_by_forbidden_extension`) before the
  policy can be accepted; a planned artifact outside the repo is recorded
  as a `DetectionTrainingArtifactRecord` with `artifact_state=planned`,
  never `registered`/`missing` (those states only apply to real artifacts
  in a future phase). Blocking-category priority when several co-occur is
  `blocked_by_environment` > `blocked_by_missing_output_dir` >
  `blocked_by_repo_storage` > `blocked_by_forbidden_extension` >
  `blocked_by_policy_violation`; with warnings but no blocking errors, the
  decision falls back to `needs_external_storage`.
- `CreateDetectionTrainingArtifactPolicyUseCase` looks up the
  `DetectionTrainingRun`, `DetectionTrainingReadinessReport`, and
  `DetectionTrainingEnvironmentSpec` (404 if any is missing), verifies the
  readiness report belongs to the run, that the environment spec belongs
  to the run, and that the environment spec belongs to the readiness
  report (otherwise 409
  `detection_training_artifact_policy_not_allowed`), looks up the
  associated `AnnotationBundleRun` and its files, runs the evaluator, and
  persists the policy plus its records and issues in one `UnitOfWorkPort`
  transaction. It never modifies `DetectionTrainingRun`,
  `DetectionTrainingReadinessReport`, or `DetectionTrainingEnvironmentSpec`.
  An internal evaluation failure becomes a persisted `status=failed`
  policy, never an unpersisted exception.

Endpoints:

- `POST /api/v1/ml/detection-training-artifact-policies`
- `GET /api/v1/ml/detection-training-artifact-policies`
- `GET /api/v1/ml/detection-training-artifact-policies/{artifact_policy_id}`
- `GET /api/v1/ml/detection-training-artifact-policies/{artifact_policy_id}/records`
- `GET /api/v1/ml/detection-training-artifact-policies/{artifact_policy_id}/issues`
- `GET /api/v1/ml/detection-training-runs/{detection_training_run_id}/artifact-policies`
- `GET /api/v1/ml/detection-training-readiness-reports/{readiness_report_id}/artifact-policies`
- `GET /api/v1/ml/detection-training-environment-specs/{environment_spec_id}/artifact-policies`
- `GET /api/v1/ml/annotation-bundles/{annotation_bundle_run_id}/detection-training-artifact-policies`
- `GET /api/v1/datasets/releases/{dataset_release_id}/detection-training-artifact-policies`

This phase does not train YOLO or any model, does not install
`ultralytics`, does not import `torch`, does not use
PyTorch/TensorFlow/CNN/ViT/real deep learning, does not download external
weights or datasets, does not copy or modify images, does not write
artifact files or create real `.pt`/`.pth`/`.onnx`/`.h5`/`.ckpt` weights,
does not upload binaries to the repository, does not run training in CI,
does not require a GPU, does not add a
frontend/authentication/taxonomy/diagnosis claim, does not integrate
MLflow/TensorBoard/W&B, and does not replace `MockInferenceEngine`. An
`artifact_policy_ready` policy never certifies that a real artifact, a
trained weight, or a provisioned training environment exists — only that
the configured artifact-policy technical gates passed.

## 37. Git ignore & training safety guardrails (Fase 28)

Fase 28 closes the operational risk Fase 27 flagged: the repository's real
`.gitignore` did not yet cover every weight/model-output pattern that
`DetectionTrainingArtifactPolicyEvaluator` already required. It adds a
standalone, read-only way to confirm the repository can never accidentally
receive weights or heavy training artifacts, independent of any persisted
`DetectionTrainingRun`/`DetectionTrainingArtifactPolicy`.

- `.gitignore` now has an explicit block for weight/model extensions
  (`*.pt`, `*.pth`, `*.onnx`, `*.h5`, `*.ckpt`, `*.pb`, `*.tflite`) and
  training-output directories (`runs/`, `training_outputs/`,
  `training_artifacts/`, `model_artifacts/`, `checkpoints/`, `weights/`,
  `mlruns/`, `wandb/`, `tensorboard/`, `lightning_logs/`, `predictions/`,
  `inference_outputs/`, `evaluation_outputs/`, `experiments/`,
  `.local_training/`). This is a manual, documented edit — no code in this
  phase writes or modifies `.gitignore`, the same rule Fase 27 already
  established for the evaluator.
- `blueberry_microid.ml.configs.training_safety_defaults` is the single
  source of truth for `default_forbidden_extensions()`/
  `default_required_gitignore_patterns()`. Both
  `DetectionTrainingArtifactPolicyConfig` (Fase 27, per-policy evaluation)
  and the new `RepositorySafetyConfig` (Fase 28, whole-repository scan) read
  from this one module, so the two checks can never disagree about what
  counts as a forbidden pattern.
- `RepositorySafetyValidator` (`ml/validation/repository_safety_validator.py`)
  is a read-only check that does not require any
  `DetectionTrainingRun`/`DetectionTrainingArtifactPolicy` to exist: it
  reads `.gitignore` and reports missing required patterns (or a missing
  file), and optionally checks a list of candidate absolute paths for ones
  that resolve inside the repository with a forbidden extension. It lives
  in `ml/`, not `application/`, because it depends on no port and
  orchestrates no use case — it is a repository-hygiene utility any future
  caller (a use case, a CLI, a pre-commit hook) can reuse. It never writes
  `.gitignore`, never creates files, never imports `torch`/`ultralytics`,
  and never calls `subprocess`. It returns a `RepositorySafetyReport`
  (`ml/reports/repository_safety_report.py`) with `is_safe`,
  `gitignore_exists`, `missing_gitignore_patterns`, `path_violations`
  (path/extension/reason), and `recommendations`.
- `scripts/check_repository_safety.py` follows the same standalone-CLI
  pattern as `scripts/validate_training_manifest.py`: it prints the JSON
  report and exits `0`/`1`. It needs no `DetectionTrainingRun` and no
  FastAPI/PostgreSQL/Redis/Celery connection — the cheapest possible gate,
  meant to be runnable at any time (including ahead of a future real
  training phase) without installing anything new.
- `tests/unit/ml/test_repository_safety_validator.py::test_real_repository_gitignore_is_safe`
  runs `RepositorySafetyValidator` against the repository's actual
  `.gitignore` (not a synthetic one) with the default config. It runs inside
  the existing `unit-and-api-tests` CI job — no new CI job and no heavy
  dependency were added; this phase's CI guardrail is literally that test
  failing if someone removes a required pattern.

This phase adds no new entities or tables (it is repository hygiene, not a
new domain aggregate), does not train YOLO, does not install `ultralytics`,
does not import `torch`, does not use PyTorch/TensorFlow/CNN/ViT/real deep
learning, does not download external weights or datasets, does not copy or
modify images, does not store binaries in the database, does not upload
binary artifacts to the repository, does not run training in CI, does not
require a GPU, does not add a frontend/authentication/taxonomy/diagnosis
claim, does not integrate MLflow/TensorBoard/W&B, and does not replace
`MockInferenceEngine`.

## 38. Training execution gate & manual runner scaffold (Fase 29)

Fase 29 creates the formal execution gate for a future, manual, real
object-detection training attempt — separate from this system — without
executing training in this phase.

- `DetectionTrainingExecutionRun` persists an execution-gate evaluation for
  a `DetectionTrainingRun` that already has a
  `DetectionTrainingReadinessReport`, `DetectionTrainingEnvironmentSpec`,
  and `DetectionTrainingArtifactPolicy`. `status`
  (`DetectionTrainingExecutionStatus`) has exactly four values — `blocked`,
  `manual_required`, `ready_to_execute`, `failed` — deliberately with no
  `running`/`completed`/`trained`/`model_created`, since this phase never
  runs anything. `is_executable` is an entity invariant that is always
  `False`: constructing one with `True` raises `ValueError`, because no
  mechanism yet exists that would give that value any meaning.
  `DetectionTrainingExecutionIssue` stores severity-tagged findings with 18
  fixed codes; neither entity stores weights, images, or full label sets.
- `DetectionTrainingExecutionConfig` (`ml/configs/`) treats
  `enable_real_training=false`/`dry_run_only=true` as safety rails, not
  feature flags: turning either one on always blocks
  (`training_execution_disabled`), never unlocks execution.
  `require_manual_confirmation=true` requires `manual_confirmation_text` to
  match `required_confirmation_text` exactly ("I understand this will only
  create a scaffold and will not train a model" by default); missing or
  mismatched text yields `status=manual_required`.
  `allow_ready_to_execute_status=false` caps the reachable status at
  `manual_required` even when everything else passes.
- `DetectionTrainingExecutionGateEvaluator` (`application/services/`) takes
  the four upstream entities plus an already-computed
  `RepositorySafetyReport` (the use case instantiates
  `RepositorySafetyValidator`; the evaluator never does). It validates, in
  blocking-priority order: run prerequisites (`planned`, `is_runnable`,
  `command_preview`, `expected_outputs`) > readiness
  (`ready_for_training`) > environment (`environment_ready`) > artifact
  policy (`artifact_policy_ready`) > repository safety
  (`RepositorySafetyValidator.is_safe` and
  `artifact_policy.storage_policy.artifact_root_dir_inside_repo`) > CI
  (`CI`/`GITHUB_ACTIONS` env vars) > configuration
  (`enable_real_training`/`dry_run_only`). It always adds
  `no_training_executed` and `real_runner_not_implemented`. It never calls
  `subprocess`, never imports `torch`/`ultralytics`, never installs
  dependencies, never modifies files, and never creates weights.
- `ManualYoloTrainingRunnerScaffold` (`application/services/`) turns a
  `DetectionTrainingExecutionGateEvaluation` into a human-readable JSON
  `execution_plan`: `preconditions`, `manual_steps`, `command_preview`
  (copied from the run, never executed), `output_expectations`,
  `artifact_policy_reminders`, `rollback_notes`, `safety_notes`,
  `prohibited_actions`, and a `checklist`. Pure text/JSON derived from the
  evaluation; it never executes anything and never writes files.
- `CreateDetectionTrainingExecutionRunUseCase` looks up the four upstream
  entities (404 if any is missing) and verifies six membership
  relationships (readiness-run, environment-run, environment-readiness,
  artifact_policy-run, artifact_policy-readiness, artifact_policy-environment)
  before evaluating; any violation raises
  `DetectionTrainingExecutionRunNotAllowedError` (409). It instantiates
  `RepositorySafetyValidator` directly (same pattern as
  `CreateImageDatasetAuditRunUseCase` with `ImageDatasetAuditor`), runs the
  evaluator, enriches `execution_plan` with
  `ManualYoloTrainingRunnerScaffold`, and persists the execution run plus
  issues in one `UnitOfWorkPort` transaction. It never modifies any of the
  four upstream entities. An internal evaluation failure becomes a
  persisted `status=failed` execution run, never an unpersisted exception.

Endpoints:

- `POST /api/v1/ml/detection-training-execution-runs`
- `GET /api/v1/ml/detection-training-execution-runs`
- `GET /api/v1/ml/detection-training-execution-runs/{execution_run_id}`
- `GET /api/v1/ml/detection-training-execution-runs/{execution_run_id}/issues`
- `GET /api/v1/ml/detection-training-runs/{detection_training_run_id}/execution-runs`
- `GET /api/v1/ml/detection-training-readiness-reports/{readiness_report_id}/execution-runs`
- `GET /api/v1/ml/detection-training-environment-specs/{environment_spec_id}/execution-runs`
- `GET /api/v1/ml/detection-training-artifact-policies/{artifact_policy_id}/execution-runs`
- `GET /api/v1/ml/annotation-bundles/{annotation_bundle_run_id}/detection-training-execution-runs`
- `GET /api/v1/datasets/releases/{dataset_release_id}/detection-training-execution-runs`

This phase does not train YOLO, does not execute YOLO, does not execute
training commands, does not call `subprocess`, does not install
`ultralytics`, does not import `torch`, does not use
PyTorch/TensorFlow/CNN/ViT/real deep learning, does not download external
weights or datasets, does not run training in CI, does not require a GPU,
does not create real weights (`.pt`/`.onnx`/`.h5`/`.pth`/`.ckpt`), does not
copy or modify images, does not store binaries in the database, does not
upload binary artifacts to the repository, does not add a
frontend/authentication/taxonomy/diagnosis claim, does not integrate
MLflow/TensorBoard/W&B, and does not replace `MockInferenceEngine`. A
`ready_to_execute` execution run never certifies that a model was
trained — only that the configured technical gates passed and a human
would still have to trigger training manually, in a future and separately
approved phase.
## 40. Manual training runbook and operator checklist (Fase 30)

Fase 30 adds preventive operations documentation for a future manual object
detection training attempt. It is documentation only: no real YOLO runner,
no training execution, no dependency installation, no artifact generation,
and no business-logic changes.

The new folder `docs/training/` contains:

- `manual_training_runbook.md` for the full human procedure and required
  upstream gates.
- `operator_checklist.md` for operator checkboxes and stop criteria.
- `artifact_registration_protocol.md` for future metadata-only registration
  of weights, metrics, predictions, logs, run directories, config, and
  manifests.
- `rollback_protocol.md` for failed future training attempts and unsafe
  artifacts.
- `prohibited_actions.md` for forbidden execution, artifact, data, and
  product-boundary actions.
- `README.md` for folder purpose and reading order.

The runbook requires these gates to be reviewed before any later authorized
manual training attempt: `AnnotationBundleRun` completed,
`AnnotationQualityGateRun` passed, `DetectionTrainingRun` planned,
`DetectionTrainingReadinessReport` ready,
`DetectionTrainingEnvironmentSpec` ready,
`DetectionTrainingArtifactPolicy` ready, `RepositorySafetyValidator`
passed/safe, and `DetectionTrainingExecutionRun` `manual_required` or
`ready_to_execute`. It explicitly states that `command_preview` is not an
executable instruction and that `ready_to_execute` does not mean a model was
trained.

`scripts/check_training_docs.py` validates the training documents in
read-only mode. It checks that all six Markdown files exist, required
sections are present, all gates are mentioned, the checklist has `- [ ]`
items, the artifact protocol mentions `checksum_sha256`, rollback covers
failed artifacts, prohibited actions forbid training in CI and weights in
Git, and the README says there is no real training. The script has no
external dependencies, does not import `torch` or `ultralytics`, does not
call `subprocess`, does not modify files, and exits `0` on success or `1`
on validation failure.

Fase 30 does not train YOLO, execute YOLO, execute training commands, install
`ultralytics`, import `torch`, use PyTorch, TensorFlow, CNN, ViT, or real
deep learning, download external weights or datasets, run training in CI,
require GPU, create weights, copy or modify images, store binaries in DB,
upload binary artifacts to the repo, add frontend/authentication/taxonomy/
diagnosis, integrate external experiment tools, or replace
`MockInferenceEngine`.

## 41. Local experimental YOLO training runner (Fase 31)

Fase 31 adds the first real training runner, but only for local/manual use.
It is not wired into FastAPI, Celery, Redis, or GitHub Actions.

- `pyproject.toml` defines the optional `training` extra with
  `ultralytics>=8.3,<9.0`. CI does not install this extra.
- `LocalYoloTrainingRunner` validates no CI, exact manual confirmation,
  `ready_to_execute` execution run, ready artifact policy, actual artifact
  registration permission, external artifact root, local base model path,
  dataset YAML from the approved bundle, and repository safety before it
  lazily imports `ultralytics`.
- `RunLocalYoloTrainingUseCase` persists only metadata-only
  `DetectionTrainingArtifactRecord` rows for actual artifacts.
- `scripts/run_local_yolo_training.py` is the local operator entry point.

The runner may create real YOLO outputs only under the approved external
`artifact_root_dir`. It records path, relative path, extension, size,
`checksum_sha256`, artifact kind/state, and execution-run metadata. It does
not store binary content in PostgreSQL and does not copy outputs into the
repository.

Fase 31 still forbids CI training, automatic training, external datasets,
unapproved weight downloads, repository-stored weights, DB-stored binaries,
original image modification, taxonomy, diagnosis claims, frontend,
authentication, external tracking tools, and replacing `MockInferenceEngine`.
