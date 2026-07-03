# BlueberryMicroID

Preliminary, non-diagnostic support for recognizing microorganisms associated with **blueberries**, from two kinds of lab imagery per sample:

- **Petri dish image** ("macro" only by relative scale) — a photograph of the Petri dish where microbial growth is observed. **Never** a photograph of the blueberry fruit itself.
- **Microscopy image** ("micro") — a photograph taken through a microscope from the same sample.

**What this system does not do (yet, or ever without further validation):**

- It does **not** run real inference, and never trains or loads a real/trained model. `POST /analysis-runs/{id}/process` and the Celery worker behind `POST /analysis-runs/{id}/process-async` only ever run `MockInferenceEngine` — a deterministic simulation that never opens or analyzes the actual image bytes, exists purely to validate the technical pipeline (`AnalysisRun` → `Prediction` → state transition), and carries no diagnostic validity. The synchronous response always says so explicitly (`disclaimer` field).
- It does **not** identify microorganism species or genus. No taxonomic classification exists in this codebase — only five broad, preliminary visual categories.
- It does **not** invent datasets or performance metrics.
- It has no frontend and no authentication yet. Celery/Redis is used only to run the existing mock processing path asynchronously; it does not add real AI.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design and phase history, and [CLAUDE.md](CLAUDE.md) for the development rules that govern this repository.

## MVP status (as of Fase 15)

**What works today:** the full synchronous pipeline — sample intake, Petri
dish + microscopy image upload with strict validation, `AnalysisRun`
creation, simulated (mock) inference with crash-safe/idempotent processing
(synchronous or queued through Celery/Redis), an auditable human-review flow
(confirm/correct/mark inconclusive/reject), curated dataset snapshots,
reproducible dataset releases with deterministic train/validation/test
splits under three leakage-prevention strategies (`by_sample`, `by_lot`,
`by_origin_lot`), future-training manifest contracts and validators under
`ml/`, a persisted technical image-file audit for a release's Petri/micro
images, and a persisted non-deep feature-extraction layer over those same
audited images — all behind a versioned FastAPI, backed by SQLAlchemy models
and Alembic migrations. 432 automated tests (379 SQLite/eager-based + 53
PostgreSQL-only); the CI workflow runs the fast suite on SQLite, applies
migrations and PostgreSQL-only tests against a real PostgreSQL service, and
runs an operational Celery smoke against real PostgreSQL + Redis services on
every push/PR to `main`.

**What does not exist yet, on purpose:** a real or trained inference model
(only `MockInferenceEngine`, a deterministic non-diagnostic simulation), image
tensor training, PyTorch/TensorFlow/deep learning, taxonomic species/genus
identification, a frontend, and authentication.

**ML training contracts (Fase 11):** `TrainingManifest` reads the deterministic
DatasetRelease manifest shape, `TrainingConfig` records future experiment
settings, `ManifestValidator` checks split integrity, allowed preliminary
labels, paths, duplicates, leakage risks, and minimum counts, and
`JsonManifestDatasetLoader` loads JSON manifests for validation. `TrainerPort`
is a contract only: `train()` deliberately raises a not-implemented error. No
tensors, PyTorch, real model training, model metrics, external datasets, or
taxonomy were added.

**Persistent ML preflight reports (Fase 12):** `TrainingPreflightRun` stores
the result of validating a `DatasetRelease` manifest with a specific
`TrainingConfig`; `TrainingPreflightIssue` stores each validation error or
warning. A passed preflight means only that technical gates passed. It is not
scientific sufficiency, model performance, or approval to train.

**Majority-class baseline training runs (Fase 13):** `TrainingRun` records a
baseline experiment and `TrainingPrediction` records one prediction per
`DatasetSplitItem`. The only implemented model type is `majority_class`: it
chooses the most frequent reviewed label in the train split, predicts that
same broad visual label for train/validation/test, and calculates only metrics
derived from those persisted predictions (`accuracy_overall`,
`accuracy_by_split`, support, label distributions, confusion matrix). It never
opens images, creates tensors, uses PyTorch/TensorFlow/deep learning, launches
Celery, or changes `MockInferenceEngine`.

**Image dataset audit (Fase 14):** `ImageDatasetAuditRun`/`ImageDatasetAuditIssue`
persist a technical, file-level audit of the Petri/micro images referenced by
a `DatasetRelease` — existence, readability, format, dimensions, color mode,
declared-vs-real file size, and duplicate paths — using lightweight Pillow
checks (`ImageDatasetAuditor`), never PyTorch/TensorFlow, never a training
tensor, never a taxonomic judgment. This is separate from the Fase 12
preflight (which validates manifest *structure*, not image *files*). A
`passed` audit only means the files are technically usable; it says nothing
about scientific quality or dataset sufficiency.

**Non-deep image feature extraction (Fase 15):** `ImageFeatureExtractionRun`/`ImageFeatureVector`
persist simple, reproducible, technical features (geometry, intensity, color,
approximate sharpness/edge density, grayscale histogram) computed with
Pillow + numpy from the Petri/micro images of a `DatasetRelease` whose
Fase 14 audit was not failed. This is a third independent layer — preflight
validates the manifest, audit validates the files, extraction computes
numbers from those same files — and never trains a model, never uses
PyTorch/TensorFlow, and never assigns taxonomy. `numpy` was added as an
explicit dependency for this phase (array arithmetic only, not a deep
learning framework).

**Curated datasets (Fase 8):** `DatasetSnapshot` freezes a reviewed dataset
version and `DatasetItem` records traceable references to the original
`AnalysisRun`, images, `Prediction`, and final `HumanReview`. A trainable item
requires a final human review; `Prediction` alone is never ground truth.
Manifests expose paths and metadata only, not image bytes, secrets, metrics, or
taxonomy.

**Dataset releases and splits (Fase 9):** `DatasetRelease` freezes a
reproducible train/validation/test partition of a `DatasetSnapshot`, using a
seeded, deterministic shuffle (`DatasetSplitter`), never sklearn or any new
heavy dependency.

**Advanced split strategies (Fase 10):** the default `by_sample` strategy
only prevents a Sample's own evidence from leaking across splits. `by_lot`
(groups by `Sample.lot_code`) and `by_origin_lot` (groups by
`Sample.origin` + `lot_code`) are stricter options for when multiple Samples
share a production lot and could let a model learn lot-specific conditions
instead of a real pattern. Missing metadata never falls back silently to a
weaker strategy — `by_lot`/`by_origin_lot` fail with
`422 dataset_split_metadata_error` instead. None of the three strategies
eliminates leakage risk completely (e.g. same-day/same-technician confounds
are not modeled). See `docs/development.md` § 19 and ARCHITECTURE.md § 26.

**CI validation status:** GitHub Actions was observed green on 2026-07-03 for
Fase 14 at commit `d61673f2fceda3b1f7de0664665ce46f3702385d`:
`unit-and-api-tests`, `postgres-migrations`, and `celery-smoke` all completed
successfully. Fases 11, 12, 13, and 15 have **not** been separately
re-verified against a fresh Actions run as of this paragraph — only the
local (SQLite) suite was run for them, and it stays green. Local
PostgreSQL/Redis smoke still requires Docker, which is not installed in this
development environment.

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

# 4. Start PostgreSQL and Redis via Docker Compose
docker compose up -d

# 5. Run database migrations
alembic upgrade head
# ...or verify the whole thing end-to-end (connection + migrate + reversibility check):
python scripts/check_postgres_migrations.py

# 6. Run the API
uvicorn blueberry_microid.interfaces.api.app:create_app --factory --reload

# 7. Run a Celery worker for async mock processing (separate terminal)
celery -A blueberry_microid.infrastructure.tasks.celery_app.celery_app worker --loglevel=info -Q analysis

# 8. Smoke-test the running API (separate terminal)
python scripts/api_smoke_test.py

# 9. Smoke-test the real Redis + Celery async path (separate terminal)
python scripts/celery_smoke_test.py

# 10. Run the test suite (fast; PostgreSQL-only tests auto-skip)
pytest -v

# 11. Run the PostgreSQL-only tests against the database from step 4
export DATABASE_URL=postgresql+psycopg://blueberry:blueberry@localhost:5432/blueberry_microid
pytest -v -m postgres tests/integration/postgres

# 12. Validate a future-training manifest exported from a DatasetRelease
python scripts/validate_training_manifest.py path/to/dataset_release_manifest.json
```

See [docs/development.md](docs/development.md) for full details, including the exact current test count, how the fast suite uses SQLite, and how the PostgreSQL-only tests and the `postgres-migrations` CI job are intended to validate the real schema once the workflow is pushed and observed (§ 15).

## Operational notes

- **Simulated inference only:** the only `InferenceEnginePort` implementation is `MockInferenceEngine` — deterministic (hashes `analysis_run.id`, no randomness), never reads image content, never names a species/genus, and keeps `confidence_score` moderate (≤ 0.75) by design. See `docs/development.md` § 10.
- **Async mock processing:** `POST /api/v1/analysis-runs/{id}/process-async` enqueues the same mock processing use case in Celery and returns `202 Accepted`. The worker creates the `Prediction`; the source of truth is still `GET /api/v1/analysis-runs/{id}` and `GET /api/v1/analysis-runs/{id}/prediction`, not the Celery result backend.
- **Real Celery smoke:** `scripts/celery_smoke_test.py` exercises `/process-async` against a running API, Redis broker/backend, and real Celery worker. It still uses only generated Pillow images and `MockInferenceEngine`.
- **Idempotent, crash-safe processing:** `POST /analysis-runs/{id}/process` claims the `pending -> processing` transition with a single atomic conditional database update, so two simultaneous calls for the same AnalysisRun can never both proceed — one gets `409 Conflict`, whichever loses the race, and no state is left ambiguous. `processing` is never a permanent state: any processing failure after the claim is caught, logged server-side, persisted as `failed` with a controlled `error_message`, and returned as a safe HTTP error rather than `200 OK`; a duplicate `Prediction` returns `409 Conflict` and also leaves the run `failed`, without creating a second prediction. See `docs/development.md` § 11.
- **Human review audit flow:** after an `AnalysisRun` has a `Prediction`, an expert can submit reviews under `/api/v1/analysis-runs/{id}/reviews`. A new final review demotes any previous final review in the same transaction, while the original `Prediction` stays immutable for traceability. See `docs/development.md` § 12.
- **Training manifest validation only:** `scripts/validate_training_manifest.py` validates the JSON manifest exported by a `DatasetRelease` against the Fase 11 contracts. It checks structure, split coverage, allowed preliminary labels, duplicate/leakage risks, and minimum counts; it does not open image bytes, train a model, calculate accuracy/precision/recall/F1, or use PyTorch.
- **Persistent preflight validation:** `POST /api/v1/ml/preflight-runs` runs the same manifest validation and persists the report. Use the standalone CLI for quick local checks; use the API when the result must be auditable and queryable by `DatasetRelease`.
- **Majority-class baseline:** `POST /api/v1/ml/training-runs/baseline` runs the only implemented experimental baseline. It requires a matching non-failed preflight, revalidates the release manifest, uses train labels only to select the majority class, persists one prediction per split item, and reports real baseline metrics from those predictions. It does not read image bytes, train neural networks, use PyTorch, or alter the mock inference engine.
- **Technical image dataset audit:** `POST /api/v1/ml/image-audits` opens each Petri/micro image file referenced by a `DatasetRelease` with Pillow (existence, corruption, format, dimensions, color mode, declared-vs-real file size) and persists the result. It is a technical file check, not the Fase 12 manifest preflight and not a scientific/microbiological evaluation; it never creates tensors or uses PyTorch/TensorFlow.
- **Non-deep image feature extraction:** `POST /api/v1/ml/image-feature-extractions` requires a non-failed `ImageDatasetAuditRun` for the same `DatasetRelease`, then computes geometry/intensity/color/sharpness/texture/histogram features per Petri/micro image with Pillow + numpy and persists one `ImageFeatureVector` per image. It never trains a model, never uses PyTorch/TensorFlow, and never assigns taxonomy.
- **Upload limits:** Petri/micro image uploads are capped by `MAX_UPLOAD_SIZE_MB` (default 20 MB, configurable via `.env`); oversized uploads get `413 Payload Too Large`.
- **Strict image validation:** every upload must have an allowed MIME type and extension, decode cleanly with Pillow, *and* have its real detected format agree with both the declared MIME type and the extension — a mislabeled file is rejected even if each check would pass in isolation.
- **Structured logging:** every request gets a `request_id` (echoed back via an `X-Request-ID` response header) and one structured log line (JSON or console format, via `LOG_FORMAT`); 5xx errors are logged server-side with a full stack trace but never expose internal details to the client.
- **CI validation status:** as of Fase 7.5, GitHub Actions run `28618230579` passed `unit-and-api-tests`, `postgres-migrations`, and `celery-smoke` on commit `c4427c4df648ec0c9326d4b88e922435ffac60d6`. To validate locally, start PostgreSQL/Redis and run `pytest -m postgres tests/integration/postgres`, `python scripts/check_postgres_migrations.py`, and `python scripts/celery_smoke_test.py` - see `docs/development.md` § 5, § 15, and § 16.
- **Continuous integration:** `.github/workflows/tests.yml` has three jobs on every push/PR to `main` - `unit-and-api-tests` (full suite on SQLite), `postgres-migrations` (real `postgres:16` service, Alembic migrations, PostgreSQL-only tests), and `celery-smoke` (real PostgreSQL + Redis services, real API process, real Celery worker, and `scripts/celery_smoke_test.py`). No deployment step, Docker image build, secrets, real AI, PyTorch, frontend, or taxonomy.

## API overview

Once running, interactive docs are available at `/docs` (Swagger UI) and `/redoc`. All endpoints are versioned under `/api/v1`; see [ARCHITECTURE.md](ARCHITECTURE.md) for the full endpoint list and the request/response error format.

A minimal health check is available unversioned at `GET /health`.

Human review endpoints:

- `POST /api/v1/analysis-runs/{analysis_run_id}/reviews` creates a review (`confirmed`, `corrected`, `marked_inconclusive`, or `rejected_invalid_sample`).
- `GET /api/v1/analysis-runs/{analysis_run_id}/reviews` returns chronological review history.
- `GET /api/v1/analysis-runs/{analysis_run_id}/reviews/final` returns the current final human review.

Dataset endpoints:

- `POST /api/v1/datasets/snapshots` creates a frozen curated dataset snapshot.
- `GET /api/v1/datasets/snapshots` lists snapshots.
- `GET /api/v1/datasets/snapshots/{dataset_snapshot_id}` returns snapshot metadata.
- `GET /api/v1/datasets/snapshots/{dataset_snapshot_id}/items` lists traceable dataset items.
- `GET /api/v1/datasets/snapshots/{dataset_snapshot_id}/manifest` returns a deterministic JSON manifest for future training pipelines.

Dataset release endpoints (Fase 9 — reproducible train/validation/test splits):

- `POST /api/v1/datasets/releases` creates a release from a `DatasetSnapshot`, partitioning items by Sample with a deterministic seed.
- `GET /api/v1/datasets/releases` lists releases.
- `GET /api/v1/datasets/releases/{dataset_release_id}` returns release metadata (ratios, counts, label/split distributions).
- `GET /api/v1/datasets/releases/{dataset_release_id}/items` lists each item's split assignment.
- `GET /api/v1/datasets/releases/{dataset_release_id}/manifest` returns a deterministic JSON manifest including each item's split.
- `GET /api/v1/datasets/releases/{dataset_release_id}/preflight-runs` lists persisted ML preflight validations for that release.
- `GET /api/v1/datasets/releases/{dataset_release_id}/training-runs` lists baseline training runs for that release.
- `GET /api/v1/datasets/releases/{dataset_release_id}/image-audits` lists technical image-file audits for that release.

ML preflight endpoints (Fase 12 — persistent validation reports, no training):

- `POST /api/v1/ml/preflight-runs` validates a DatasetRelease manifest with a `TrainingConfig` and persists the report.
- `GET /api/v1/ml/preflight-runs` lists persisted preflight runs.
- `GET /api/v1/ml/preflight-runs/{preflight_run_id}` returns a preflight run with its issues.
- `GET /api/v1/ml/preflight-runs/{preflight_run_id}/issues` lists validation errors/warnings.
- `GET /api/v1/ml/preflight-runs/{preflight_run_id}/training-runs` lists baseline training runs linked to that preflight.

ML baseline endpoints (Fase 13 - majority-class baseline only, no image training):

- `POST /api/v1/ml/training-runs/baseline` creates a majority-class baseline `TrainingRun`.
- `GET /api/v1/ml/training-runs` lists training runs.
- `GET /api/v1/ml/training-runs/{training_run_id}` returns one training run.
- `GET /api/v1/ml/training-runs/{training_run_id}/predictions` lists persisted baseline predictions; optional `split=train|validation|test`.

Image dataset audit endpoints (Fase 14 — technical file audit, no training):

- `POST /api/v1/ml/image-audits` audits the Petri/micro image files referenced by a `DatasetRelease` and persists the report.
- `GET /api/v1/ml/image-audits` lists persisted image audit runs.
- `GET /api/v1/ml/image-audits/{audit_run_id}` returns an audit run with its issues.
- `GET /api/v1/ml/image-audits/{audit_run_id}/issues` lists per-image technical findings.
- `GET /api/v1/datasets/releases/{dataset_release_id}/image-audits` lists audits for that release.

Image feature extraction endpoints (Fase 15 — non-deep technical features, no training):

- `POST /api/v1/ml/image-feature-extractions` extracts features for a `DatasetRelease` + `ImageDatasetAuditRun` and persists the run and its vectors.
- `GET /api/v1/ml/image-feature-extractions` lists persisted extraction runs.
- `GET /api/v1/ml/image-feature-extractions/{feature_extraction_run_id}` returns a run with its vectors.
- `GET /api/v1/ml/image-feature-extractions/{feature_extraction_run_id}/vectors` lists feature vectors; optional `modality=petri|micro` and `split=train|validation|test` filters.
- `GET /api/v1/datasets/releases/{dataset_release_id}/image-feature-extractions` lists extraction runs for that release.
- `GET /api/v1/ml/image-audits/{image_audit_run_id}/feature-extractions` lists extraction runs for that audit.

Async processing endpoints:

- `POST /api/v1/analysis-runs/{analysis_run_id}/process-async` queues mock processing and returns `202`.
- `GET /api/v1/tasks/{task_id}` returns auxiliary Celery task state; use the AnalysisRun endpoints as the durable source of truth.

## Project layout

This project follows Clean Architecture (`domain/` → `application/` → `infrastructure/` + `interfaces/`). See [ARCHITECTURE.md](ARCHITECTURE.md) for the folder-by-folder breakdown and the rules that keep each layer independent of the others.
