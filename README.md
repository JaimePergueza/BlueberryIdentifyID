# BlueberryMicroID

Preliminary, non-diagnostic support for recognizing microorganisms associated with **blueberries**, from two kinds of lab imagery per sample:

- **Petri dish image** ("macro" only by relative scale) — a photograph of the Petri dish where microbial growth is observed. **Never** a photograph of the blueberry fruit itself.
- **Microscopy image** ("micro") — a photograph taken through a microscope from the same sample.

**What this system does not do (yet, or ever without further validation):**

- It does **not** run real inference, and never trains or loads a real/trained model. `POST /analysis-runs/{id}/process` only ever runs `MockInferenceEngine` — a deterministic simulation that never opens or analyzes the actual image bytes, exists purely to validate the technical pipeline (`AnalysisRun` → `Prediction` → state transition), and carries no diagnostic validity. Its response always says so explicitly (`disclaimer` field).
- It does **not** identify microorganism species or genus. No taxonomic classification exists in this codebase — only five broad, preliminary visual categories.
- It does **not** invent datasets or performance metrics.
- It has no frontend, no Celery/async task processing (processing is synchronous), and no authentication yet.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design and phase history, and [CLAUDE.md](CLAUDE.md) for the development rules that govern this repository.

## MVP status (as of Fase 6.5)

**What works today:** the full synchronous pipeline — sample intake, Petri
dish + microscopy image upload with strict validation, `AnalysisRun`
creation, simulated (mock) inference with crash-safe/idempotent processing,
and an auditable human-review flow (confirm/correct/mark
inconclusive/reject) — all behind a versioned FastAPI, backed by SQLAlchemy
models and Alembic migrations. 200 automated tests (188 SQLite-based +
12 PostgreSQL-only); the CI workflow is configured to run the fast suite on
SQLite **and**, in a separate job, apply the migrations to a real PostgreSQL
service and run the PostgreSQL-only tests against it on every push/PR to
`main`.

**What does not exist yet, on purpose:** Celery/async task processing (the
API is fully synchronous), a real or trained inference model (only
`MockInferenceEngine`, a deterministic non-diagnostic simulation), any
taxonomic species/genus identification, a frontend, and authentication.

**PostgreSQL validation status (Fase 6.5):** Estado B - workflow pushed,
but the GitHub Actions run has not been observed from this environment.
`origin` is configured as
`https://github.com/JaimePergueza/BlueberryIdentifyID.git` and `main` was
pushed successfully, but `gh` is not installed and the unauthenticated GitHub
API request for Actions runs returned `404 Not Found` (for example, if the
repository is private or requires authenticated API access). Do **not** treat
PostgreSQL as validated in CI until a successful `postgres-migrations` run is
confirmed. PostgreSQL was also **not** run in this local development
environment, which has no Docker installed. To complete verification, open
GitHub Actions and verify the `unit-and-api-tests` and
`postgres-migrations` jobs; see `docs/development.md` § 15.

**Repository root folder name:** currently `IndetificadorMicro` (a
misspelling); the recommended name is `BlueberryMicroID`. This has not been
renamed automatically — see `docs/development.md` (Prerequisites) for why
and how to do it manually. The Python package itself is already correctly
named `blueberry_microid` and is unaffected either way.

## Quick start

```bash
# 1. Create and activate a virtual environment (never install into your global Python)
python -m venv .venv
source .venv/bin/activate        # Linux/macOS/Git Bash
# .venv\Scripts\Activate.ps1     # Windows PowerShell

# 2. Install the project (editable) with dev dependencies
python -m pip install --upgrade pip
pip install -e ".[dev]"

# 3. Configure environment variables
cp .env.example .env

# 4. Start PostgreSQL (and Redis, reserved for a future phase) via Docker Compose
docker compose up -d

# 5. Run database migrations
alembic upgrade head
# ...or verify the whole thing end-to-end (connection + migrate + reversibility check):
python scripts/check_postgres_migrations.py

# 6. Run the API
uvicorn blueberry_microid.interfaces.api.app:create_app --factory --reload

# 7. Smoke-test the running API (separate terminal)
python scripts/api_smoke_test.py

# 8. Run the test suite (fast; PostgreSQL-only tests auto-skip)
pytest -v

# 9. Run the PostgreSQL-only tests against the database from step 4
export DATABASE_URL=postgresql+psycopg://blueberry:blueberry@localhost:5432/blueberry_microid
pytest -v -m postgres tests/integration/postgres
```

See [docs/development.md](docs/development.md) for full details, including the exact current test count, how the fast suite uses SQLite, and how the PostgreSQL-only tests and the `postgres-migrations` CI job are intended to validate the real schema once the workflow is pushed and observed (§ 15).

## Operational notes

- **Simulated inference only:** the only `InferenceEnginePort` implementation is `MockInferenceEngine` — deterministic (hashes `analysis_run.id`, no randomness), never reads image content, never names a species/genus, and keeps `confidence_score` moderate (≤ 0.75) by design. See `docs/development.md` § 10.
- **Idempotent, crash-safe processing:** `POST /analysis-runs/{id}/process` claims the `pending -> processing` transition with a single atomic conditional database update, so two simultaneous calls for the same AnalysisRun can never both proceed — one gets `409 Conflict`, whichever loses the race, and no state is left ambiguous. `processing` is never a permanent state: any processing failure after the claim is caught, logged server-side, persisted as `failed` with a controlled `error_message`, and returned as a safe HTTP error rather than `200 OK`; a duplicate `Prediction` returns `409 Conflict` and also leaves the run `failed`, without creating a second prediction. See `docs/development.md` § 11.
- **Human review audit flow:** after an `AnalysisRun` has a `Prediction`, an expert can submit reviews under `/api/v1/analysis-runs/{id}/reviews`. A new final review demotes any previous final review in the same transaction, while the original `Prediction` stays immutable for traceability. See `docs/development.md` § 12.
- **Upload limits:** Petri/micro image uploads are capped by `MAX_UPLOAD_SIZE_MB` (default 20 MB, configurable via `.env`); oversized uploads get `413 Payload Too Large`.
- **Strict image validation:** every upload must have an allowed MIME type and extension, decode cleanly with Pillow, *and* have its real detected format agree with both the declared MIME type and the extension — a mislabeled file is rejected even if each check would pass in isolation.
- **Structured logging:** every request gets a `request_id` (echoed back via an `X-Request-ID` response header) and one structured log line (JSON or console format, via `LOG_FORMAT`); 5xx errors are logged server-side with a full stack trace but never expose internal details to the client.
- **PostgreSQL validation status:** Estado B as of Fase 6.5 - the GitHub Actions workflow was pushed to `origin`, but no run has been observed from this environment because `gh` is not installed and the unauthenticated Actions API request returned `404 Not Found`. PostgreSQL is therefore **not yet validated in CI**. To validate locally, start PostgreSQL and run `pytest -m postgres tests/integration/postgres` and `python scripts/check_postgres_migrations.py` - see `docs/development.md` § 5 and § 15.
- **Continuous integration:** `.github/workflows/tests.yml` has two jobs on every push/PR to `main` - `unit-and-api-tests` (full suite on SQLite) and `postgres-migrations` (spins up a real `postgres:16` service, applies the Alembic migrations, and runs the PostgreSQL-only tests). No deployment step and no secrets. The workflow must still be verified in GitHub Actions.

## API overview

Once running, interactive docs are available at `/docs` (Swagger UI) and `/redoc`. All endpoints are versioned under `/api/v1`; see [ARCHITECTURE.md](ARCHITECTURE.md) for the full endpoint list and the request/response error format.

A minimal health check is available unversioned at `GET /health`.

Human review endpoints:

- `POST /api/v1/analysis-runs/{analysis_run_id}/reviews` creates a review (`confirmed`, `corrected`, `marked_inconclusive`, or `rejected_invalid_sample`).
- `GET /api/v1/analysis-runs/{analysis_run_id}/reviews` returns chronological review history.
- `GET /api/v1/analysis-runs/{analysis_run_id}/reviews/final` returns the current final human review.

## Project layout

This project follows Clean Architecture (`domain/` → `application/` → `infrastructure/` + `interfaces/`). See [ARCHITECTURE.md](ARCHITECTURE.md) for the folder-by-folder breakdown and the rules that keep each layer independent of the others.
