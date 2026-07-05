# BlueberryMicroID

## Fase 45 - Snapshot-Only Dataset Releases

Fase 45 adds `POST /api/v1/datasets/releases/from-snapshot` to create a
metadata-only `snapshot_release` directly from a curated `DatasetSnapshot`.
It freezes the snapshot items into `DatasetRelease.manifest` and records
`provenance` without calling `DatasetSplitter` and without creating
`DatasetSplitItem` rows.

The existing split-oriented `POST /api/v1/datasets/releases` remains intact.
`GET /api/v1/datasets/releases/{release_id}` returns either release kind, and
`GET /api/v1/datasets/releases/{release_id}/items` returns split items for a
`split_release` or manifest items for a `snapshot_release`.

This phase does not train, run YOLO, export COCO/YOLO annotations, copy
images, store binaries, add external datasets, add taxonomy, or make
diagnostic claims.

## Fase 44 - Snapshot Creation from Dataset Curation Runs

Fase 44 adds the explicit endpoint
`POST /api/v1/datasets/snapshots/from-curation-run` to freeze a completed,
human-reviewed `DatasetCurationRun` into a `DatasetSnapshot`.

Only included `DatasetCurationItem` rows can become `DatasetItem` rows. Each
snapshot item keeps metadata-only provenance back to the curation run and
curation item (`curation_run_id`, `curation_item_id`, and `provenance`) while
retaining the original references to `AnalysisRun`, `Sample`, Petri image,
micro image, `Prediction`, and final `HumanReview`. The manifest includes
that provenance, but never image bytes, model weights, secrets, taxonomy, or
diagnostic claims.

This phase does not create `DatasetRelease`, train/validation/test splits,
training jobs, YOLO runs, external datasets, frontend, authentication, or any
replacement for `MockInferenceEngine`.

## Fase 43 - Dataset Curation from Human-Reviewed Two-Image Analyses

Fase 43 adds persisted `DatasetCurationRun` and `DatasetCurationItem`
records. A curation run scans explicit `AnalysisRun` IDs, or all runs only
when `explicit_all_reviewed=true`, and records why each two-image analysis is
included or excluded before optionally creating a `DatasetSnapshot`.

Only analyses with a `Prediction`, both Petri/microscopy images, and a final
`HumanReview` can be included. Ground truth is derived from the same final
result rules used by the API: `confirmed` keeps the reviewed prediction
label, `corrected` uses the corrected label, `marked_inconclusive` yields
`inconclusive`, and `rejected_invalid_sample` is excluded. The layer stores
metadata and references only; it does not copy images, release a dataset,
train, evaluate models, add taxonomy, or replace `MockInferenceEngine`.

## Fase 39 - Smoke Model Evaluation & Promotion Gate

Fase 39 adds metadata-only model candidate evaluation for local/manual YOLO
smoke artifacts. It reads registered artifact metadata and summarized
`results.csv` values, classifies the Fase 38 smoke model as `smoke_only`,
and blocks promotion as `not_promotable`.

This phase does not train, run inference, load weights, expose downloads,
store binaries in DB, add taxonomy, or claim diagnostic/scientific validity.

Preliminary, non-diagnostic support for recognizing microorganisms associated with **blueberries**, from two kinds of lab imagery per sample:

- **Petri dish image** ("macro" only by relative scale) — a photograph of the Petri dish where microbial growth is observed. **Never** a photograph of the blueberry fruit itself.
- **Microscopy image** ("micro") — a photograph taken through a microscope from the same sample.

**What this system does not do (yet, or ever without further validation):**

- It does **not** run real inference, and never trains or loads a real/trained model. `POST /analysis-runs/{id}/process` and the Celery worker behind `POST /analysis-runs/{id}/process-async` only ever run `MockInferenceEngine` — a deterministic simulation that never opens or analyzes the actual image bytes, exists purely to validate the technical pipeline (`AnalysisRun` → `Prediction` → state transition), and carries no diagnostic validity. The synchronous response always says so explicitly (`disclaimer` field).
- It does **not** identify microorganism species or genus. No taxonomic classification exists in this codebase — only five broad, preliminary visual categories.
- It does **not** invent datasets or performance metrics.
- It has no frontend and no authentication yet. Celery/Redis is used only to run the existing mock processing path asynchronously; it does not add real AI.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design and phase history, and [CLAUDE.md](CLAUDE.md) for the development rules that govern this repository.

## MVP status (as of Fase 32)

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
and Alembic migrations. 556 automated tests (477 SQLite/eager-based + 79
PostgreSQL-only); Fase 17 also adds persisted comparison reports over completed
baseline `TrainingRun` metrics, and Fases 19-21 add classical Petri candidate
segmentation, human review of regions, and supervised annotation export
manifests. Fase 22 adds persisted annotation bundle runs/files that package
those exports into dry-run plans or filesystem bundles. Fase 23 adds a
persisted supervised annotation quality gate that checks bundle readiness
before any future training workflow. Fase 24 adds a persisted object
detection training dry-run: `DetectionTrainingRun`/`DetectionTrainingIssue`
plan a future YOLO training attempt (algorithm/mode contract, prerequisite
validation against an already-passed quality gate, a `command_preview` that
is never executed, and planned-only output paths) without training, without
installing `ultralytics`, and without importing `torch`. Fase 25 adds a
persisted `DetectionTrainingReadinessReport`/`DetectionTrainingReadinessIssue`
layer that evaluates whether a dry-run `DetectionTrainingRun` is technically
ready for a future real training phase (bundle/quality-gate/minimum-data/
environment/contract checks) — still without training anything, installing
`ultralytics`, importing `torch`, or requiring a GPU. Fase 26 adds a
persisted `DetectionTrainingEnvironmentSpec`/`DetectionTrainingEnvironmentIssue`
layer that specifies/validates the environment a future real training
attempt would need (Python/OS, ultralytics/torch/GPU/CUDA policy, base
weights policy, artifact storage policy, CI vs. local execution policy)
using only safe checks (`sys.version_info`, `platform.system()`,
`importlib.util.find_spec`, `pathlib`) — never installing dependencies,
importing `ultralytics`/`torch`, or running training in CI. Fase 27 adds a
persisted `DetectionTrainingArtifactPolicy`/`DetectionTrainingArtifactRecord`/
`DetectionTrainingArtifactIssue` layer that defines and validates an
artifact policy for a future real training attempt — planned weight/metric/
prediction/run-dir paths, forbidden binary extensions, repo-vs-external
storage rules, and `.gitignore` coverage of weight patterns — without
training anything, without writing a single artifact file, and without
creating any real weight. Fase 28 closes the operational risk Fase 27
flagged: `.gitignore` now has an explicit block of weight/model extensions
and training-output directories, `RepositorySafetyValidator` gives a
standalone, read-only way to confirm the repository can never accidentally
receive weights or heavy artifacts (independent of any persisted
`DetectionTrainingRun`), and `scripts/check_repository_safety.py` is a
zero-dependency CLI gate for that same check. Fase 29 adds a persisted
`DetectionTrainingExecutionRun`/`DetectionTrainingExecutionIssue` execution
gate: `DetectionTrainingExecutionGateEvaluator` checks every upstream
prerequisite (readiness, environment, artifact policy, repository safety,
CI detection, manual confirmation text) and `ManualYoloTrainingRunnerScaffold`
turns the result into a human-readable manual execution plan — a
`ready_to_execute` status still never trains anything or executes a
command; it only means a human could manually trigger training in a future,
separately-approved phase. Fase 30 adds versioned operator documentation
under `docs/training/`: a manual training runbook, operator checklist,
artifact registration protocol, rollback protocol, prohibited-actions list,
and a folder README, plus `scripts/check_training_docs.py` to validate the
documents. Fase 31 adds an experimental local/manual YOLO runner behind
strict gates: it is not exposed through FastAPI, does not run in CI, requires
the `training` optional dependency, requires exact manual confirmation,
requires a `ready_to_execute` execution run, requires a ready artifact policy
with actual registration enabled, uses an external `artifact_root_dir`, and
registers only metadata for generated artifacts. CI still does not install
`ultralytics`, import `torch`, require GPU, train YOLO, download weights,
generate weights, add datasets, or add taxonomy. Fase 32 validates the local
`training` dependency path and adds `--dry-run-validation-only` to the local
CLI so the same runner gates can be checked without importing `ultralytics`,
training, creating weights, or registering artifact metadata. The local smoke
closed as Cierre B on this workstation: dependency installation and import
were verified, but real YOLO training remained pending because no usable
local PostgreSQL service, persisted execution run, ready artifact policy, or
generated `dataset.yaml` bundle was available. The CI workflow runs
the fast suite on SQLite, applies
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
`DatasetSplitItem`. The label-only model type is `majority_class`: it
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

**Classical tabular baseline (Fase 16):** `POST /api/v1/ml/training-runs/classical-baseline`
trains `logistic_regression_tabular` with scikit-learn over persisted
`ImageFeatureVector` rows only. `FeatureMatrixBuilder` flattens numeric Petri
and/or micro feature JSON deterministically, preserves train/validation/test
splits, and uses `DatasetSplitItem.ground_truth_label` as `y`; it never uses
raw image bytes or `Prediction` as ground truth. `TrainingRun` stores config,
feature names, basic model parameters, and real metrics derived from persisted
`TrainingPrediction` rows: accuracy, support, label distributions, and
confusion matrices. No model pickle, PyTorch, TensorFlow, CNN, ViT, deep
learning, external dataset, frontend, authentication, or taxonomy was added.

**Training run comparison reports (Fase 17):** `TrainingRunComparison` and
`TrainingRunComparisonEntry` freeze a reproducible comparison of already
completed `TrainingRun` rows from the same `DatasetRelease`. The comparator
reads persisted metrics only (`accuracy_by_split` and support), ranks by
validation or test accuracy, records the selection policy, warnings such as
low support, and may mark one candidate as a preliminary baseline. It does
not train a new model, recalculate predictions, open image bytes, introduce
new metrics, use PyTorch/TensorFlow/deep learning, or change
`MockInferenceEngine`.

**External microbiology CV landscape review (Fase 18):**
`docs/references/microbiology_cv_landscape.md` documents external reference
projects and datasets such as YOLOv5-style bacteria detection, MEMTrack,
DIBaS, Petri colony detection work, clinical bacterial datasets, and unresolved
CSI-Microbes/SinfNet leads. It is a technical adoption map only: no external
code, dataset, model, dependency, endpoint, migration, frontend, taxonomy,
PyTorch, TensorFlow, YOLO, CNN, ViT, or deep learning was integrated.

**Classical Petri segmentation prototype (Fase 19):**
`PetriSegmentationRun` and `PetriSegmentationRegion` persist
OpenCV-headless classical threshold/morphology/contour results for Petri
images only. `ClassicalPetriSegmenter` reports geometric candidate regions
(area, perimeter, centroid, bounding box, circularity, solidity, mean
intensity) and never processes micro images, trains, uses OpenCV DNN/YOLO, or
confirms real colonies, taxonomy, genus/species, diagnosis, or model
performance.

**Petri region review and supervised annotation exports (Fases 20-21):**
`PetriRegionReview` records final human decisions for geometric Petri
candidate regions, with optional corrected bounding boxes that never modify
the original `PetriSegmentationRegion`. `PetriAnnotationExportRun` and
`PetriAnnotationExportItem` convert final reviewed annotations into
`blueberry_manifest`, COCO-style JSON, or YOLO label-manifest JSON for future
supervised training. YOLO here means only the text label format represented in
JSON, never a YOLO model, training loop, dependency, weights, or detector.
Only `candidate_valid` is exported as a positive object by default; false
positives, uncertain regions, and resegmentation requests are not positive
training objects by default. The only category is the generic
`candidate_region`; no taxonomy, masks, image bytes, copied images, model
metrics, PyTorch, TensorFlow, CNN, ViT, or deep learning are introduced.

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
- **Majority-class baseline:** `POST /api/v1/ml/training-runs/baseline` runs the label-only comparison baseline. It requires a matching non-failed preflight, revalidates the release manifest, uses train labels only to select the majority class, persists one prediction per split item, and reports real baseline metrics from those predictions. It does not read image bytes, train neural networks, use PyTorch, or alter the mock inference engine.
- **Classical tabular baseline:** `POST /api/v1/ml/training-runs/classical-baseline` requires a matching non-failed preflight and a completed `ImageFeatureExtractionRun` for the same `DatasetRelease`, builds a tabular matrix from `ImageFeatureVector`, fits logistic regression on train only, predicts train/validation/test, and persists real metrics plus predictions. It uses scikit-learn for classical tabular ML only; no PyTorch/TensorFlow/deep learning, raw image tensors, model serialization, external datasets, or taxonomy.
- **Training run comparisons:** `POST /api/v1/ml/training-run-comparisons` compares completed baseline runs for one `DatasetRelease` using persisted accuracy/support metrics only. Selection is preliminary and traceable; no training, model artifact, new prediction, raw image access, PyTorch/TensorFlow/deep learning, external dataset, or taxonomy is involved.
- **Classical Petri segmentation:** `POST /api/v1/ml/petri-segmentations` runs an OpenCV-headless classical candidate-region segmentation over Petri images in a `DatasetRelease`. It stores only geometry for candidate regions; no masks, image bytes, YOLO, OpenCV DNN, deep learning, taxonomy, diagnosis, or real-colony confirmation.
- **Supervised Petri annotation exports:** `POST /api/v1/ml/petri-annotation-exports` exports final reviewed Petri candidate-region annotations as Blueberry manifest, COCO-style JSON, or YOLO label-manifest JSON. It never trains YOLO or any model and never copies images by default.
- **Annotation export bundles:** `POST /api/v1/ml/annotation-bundles` turns a persisted `PetriAnnotationExportRun` into a dry-run plan or filesystem bundle with README, Blueberry manifest, COCO JSON, YOLO label text files, `dataset.yaml`, and bundle `manifest.json`. YOLO means label syntax only. Images are externally referenced by default, not copied; no model training, model weights, PyTorch/TensorFlow/deep learning, external dataset, taxonomy, or frontend is introduced.
- **Annotation quality gates:** `POST /api/v1/ml/annotation-quality-gates` validates an `AnnotationBundleRun` before future training. It checks bundle state, expected files, manifests, splits, bboxes, categories, duplicate boxes, support counts, and warnings such as single-class bundles. `passed` means technically ready by configured gates, not scientific validation or model performance.
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
- `GET /api/v1/datasets/releases/{dataset_release_id}/training-run-comparisons` lists persisted comparison reports for that release.
- `GET /api/v1/datasets/releases/{dataset_release_id}/image-audits` lists technical image-file audits for that release.

ML preflight endpoints (Fase 12 — persistent validation reports, no training):

- `POST /api/v1/ml/preflight-runs` validates a DatasetRelease manifest with a `TrainingConfig` and persists the report.
- `GET /api/v1/ml/preflight-runs` lists persisted preflight runs.
- `GET /api/v1/ml/preflight-runs/{preflight_run_id}` returns a preflight run with its issues.
- `GET /api/v1/ml/preflight-runs/{preflight_run_id}/issues` lists validation errors/warnings.
- `GET /api/v1/ml/preflight-runs/{preflight_run_id}/training-runs` lists baseline training runs linked to that preflight.

ML baseline endpoints (Fase 13/Fase 16 - majority-class plus classical tabular baselines):

- `POST /api/v1/ml/training-runs/baseline` creates a majority-class baseline `TrainingRun`.
- `POST /api/v1/ml/training-runs/classical-baseline` creates a logistic-regression tabular baseline from `ImageFeatureVector`.
- `GET /api/v1/ml/training-runs` lists training runs.
- `GET /api/v1/ml/training-runs/{training_run_id}` returns one training run.
- `GET /api/v1/ml/training-runs/{training_run_id}/predictions` lists persisted baseline predictions; optional `split=train|validation|test`.

ML training run comparison endpoints (Fase 17 - compare persisted metrics only):

- `POST /api/v1/ml/training-run-comparisons` creates a comparison report from completed runs in one release.
- `GET /api/v1/ml/training-run-comparisons` lists comparison reports; optional `dataset_release_id`.
- `GET /api/v1/ml/training-run-comparisons/{comparison_id}` returns one report with entries.
- `GET /api/v1/ml/training-run-comparisons/{comparison_id}/entries` lists ranked entries.

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

Petri segmentation endpoints (Fase 19 - classical candidate regions, no deep learning):

- `POST /api/v1/ml/petri-segmentations` runs classical Petri segmentation for a DatasetRelease.
- `GET /api/v1/ml/petri-segmentations` lists segmentation runs; optional `dataset_release_id` or `image_audit_run_id`.
- `GET /api/v1/ml/petri-segmentations/{segmentation_run_id}` returns one run with regions.
- `GET /api/v1/ml/petri-segmentations/{segmentation_run_id}/regions` lists candidate regions; optional `split=train|validation|test`.
- `GET /api/v1/datasets/releases/{dataset_release_id}/petri-segmentations` lists runs for a release.
- `GET /api/v1/ml/image-audits/{image_audit_run_id}/petri-segmentations` lists runs for an image audit.

Petri annotation export endpoints (Fase 21 - supervised annotation formats, no model training):

- `POST /api/v1/ml/petri-annotation-exports`
- `GET /api/v1/ml/petri-annotation-exports`
- `GET /api/v1/ml/petri-annotation-exports/{export_run_id}`
- `GET /api/v1/ml/petri-annotation-exports/{export_run_id}/items`
- `GET /api/v1/ml/petri-annotation-exports/{export_run_id}/manifest`
- `GET /api/v1/datasets/releases/{dataset_release_id}/petri-annotation-exports`
- `GET /api/v1/ml/petri-segmentations/{petri_segmentation_run_id}/annotation-exports`

Annotation bundle endpoints (Fase 22 - export bundle packaging, no training):

- `POST /api/v1/ml/annotation-bundles`
- `GET /api/v1/ml/annotation-bundles`
- `GET /api/v1/ml/annotation-bundles/{bundle_run_id}`
- `GET /api/v1/ml/annotation-bundles/{bundle_run_id}/files`
- `GET /api/v1/datasets/releases/{dataset_release_id}/annotation-bundles`
- `GET /api/v1/ml/petri-annotation-exports/{export_run_id}/annotation-bundles`

Annotation quality gate endpoints (Fase 23 - bundle readiness validation, no training):

- `POST /api/v1/ml/annotation-quality-gates`
- `GET /api/v1/ml/annotation-quality-gates`
- `GET /api/v1/ml/annotation-quality-gates/{quality_gate_run_id}`
- `GET /api/v1/ml/annotation-quality-gates/{quality_gate_run_id}/issues`
- `GET /api/v1/datasets/releases/{dataset_release_id}/annotation-quality-gates`
- `GET /api/v1/ml/annotation-bundles/{annotation_bundle_run_id}/quality-gates`

Detection training dry-run endpoints (Fase 24 - planning only, no YOLO training):

- `POST /api/v1/ml/detection-training-runs`
- `GET /api/v1/ml/detection-training-runs`
- `GET /api/v1/ml/detection-training-runs/{detection_training_run_id}`
- `GET /api/v1/ml/detection-training-runs/{detection_training_run_id}/issues`
- `GET /api/v1/datasets/releases/{dataset_release_id}/detection-training-runs`
- `GET /api/v1/ml/annotation-bundles/{annotation_bundle_run_id}/detection-training-runs`
- `GET /api/v1/ml/annotation-quality-gates/{quality_gate_run_id}/detection-training-runs`

Detection training readiness report endpoints (Fase 25 - technical readiness only, no training):

- `POST /api/v1/ml/detection-training-readiness-reports`
- `GET /api/v1/ml/detection-training-readiness-reports`
- `GET /api/v1/ml/detection-training-readiness-reports/{readiness_report_id}`
- `GET /api/v1/ml/detection-training-readiness-reports/{readiness_report_id}/issues`
- `GET /api/v1/ml/detection-training-runs/{detection_training_run_id}/readiness-reports`
- `GET /api/v1/datasets/releases/{dataset_release_id}/detection-training-readiness-reports`
- `GET /api/v1/ml/annotation-bundles/{annotation_bundle_run_id}/detection-training-readiness-reports`
- `GET /api/v1/ml/annotation-quality-gates/{quality_gate_run_id}/detection-training-readiness-reports`

Detection training environment spec endpoints (Fase 26 - environment specification/validation only, no training):

- `POST /api/v1/ml/detection-training-environment-specs`
- `GET /api/v1/ml/detection-training-environment-specs`
- `GET /api/v1/ml/detection-training-environment-specs/{environment_spec_id}`
- `GET /api/v1/ml/detection-training-environment-specs/{environment_spec_id}/issues`
- `GET /api/v1/ml/detection-training-runs/{detection_training_run_id}/environment-specs`
- `GET /api/v1/ml/detection-training-readiness-reports/{readiness_report_id}/environment-specs`
- `GET /api/v1/ml/annotation-bundles/{annotation_bundle_run_id}/detection-training-environment-specs`
- `GET /api/v1/datasets/releases/{dataset_release_id}/detection-training-environment-specs`

Detection training artifact policy endpoints (Fase 27 - artifact policy/registry only, no training, no real weights):

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

Detection training execution gate endpoints (Fase 29 - manual runner scaffold only, never trains a model):

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

Async processing endpoints:

- `POST /api/v1/analysis-runs/{analysis_run_id}/process-async` queues mock processing and returns `202`.
- `GET /api/v1/tasks/{task_id}` returns auxiliary Celery task state; use the AnalysisRun endpoints as the durable source of truth.

## Project layout

This project follows Clean Architecture (`domain/` → `application/` → `infrastructure/` + `interfaces/`). See [ARCHITECTURE.md](ARCHITECTURE.md) for the folder-by-folder breakdown and the rules that keep each layer independent of the others.
