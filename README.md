# BlueberryMicroID

> The GitHub repository keeps the historical name `BlueberryIdentifyID`; the
> application and Python package are named **BlueberryMicroID**.

BlueberryMicroID is a web-platform backend for preliminary analysis of
microorganism-associated visual patterns in blueberry laboratory samples.
Each analysis combines two photographs from the same sample:

1. a Petri dish image;
2. a microscopy image.

The system extracts classical visual signals from both images, produces an
explainable preliminary category, requires a human expert to confirm or correct
the result, and preserves the complete audit trail.

## Scientific scope

BlueberryMicroID is **not a diagnostic system**. It does not identify
microorganism genus or species and must not replace laboratory protocols or
expert assessment.

The current image-analysis rules are transparent, non-trained heuristics. They
inspect real pixels but have not been scientifically validated against a
labelled dataset. Every automatic result is therefore preliminary and always
requires expert review.

## Official MVP workflow

The frontend MVP must use:

```http
POST /api/v1/analysis/two-image-upload
```

This endpoint:

- validates and stores both images;
- creates `Sample`, `PetriImage`, `MicroImage`, `AnalysisRun`, and `Prediction`;
- analyzes real pixel signals with `PreliminaryTwoImageEngine` version `0.2.0`;
- records the engine as `ModelType.CLASSICAL`;
- returns explanations, extracted features, image-quality indicators, warnings,
  and a decision trace;
- marks the analysis as `needs_review`;
- always returns `requires_human_review=true`.

The result can then be reviewed and retrieved through:

```http
POST /api/v1/analysis-runs/{analysis_run_id}/reviews
GET  /api/v1/analysis-runs/{analysis_run_id}/preliminary-result
GET  /api/v1/analysis-runs/{analysis_run_id}/final-result
```

The repository still contains `MockInferenceEngine` for legacy orchestration and
Celery smoke tests. Those paths do not inspect image pixels and are not the
official MVP analysis entry point.

## Current product status

Implemented:

- sample and image persistence;
- strict upload validation;
- classical Petri and microscopy feature extraction;
- explainable preliminary classification;
- human review and final-result resolution;
- auditable dataset curation, snapshots, and releases;
- PostgreSQL migrations;
- synchronous and Celery-backed technical processing paths;
- automated SQLite, PostgreSQL, and Celery smoke tests.

Still required for the demonstrable product:

- authentication and basic roles;
- analysis history, search, filters, and consolidated detail API;
- operational React/TypeScript frontend;
- reproducible full-stack deployment and demonstration data.

See [`docs/mvp/README.md`](docs/mvp/README.md) for the delivery scope and
priorities.

## Technology

- Python 3.10+
- FastAPI
- SQLAlchemy 2 and Alembic
- PostgreSQL 16
- Celery and Redis
- Pillow, NumPy, and OpenCV
- scikit-learn for classical dataset baselines
- pytest

The code follows Clean Architecture / Ports and Adapters:

```text
interfaces/       HTTP and external entry points
application/      use cases, DTOs, ports, application services
domain/           entities, enums, value objects, business rules
infrastructure/   SQLAlchemy, storage, configuration, tasks
ml/               image processing, validation, and training contracts
```

## Local setup

### 1. Create the environment

```bash
python -m venv .venv
```

Activate it and install development dependencies:

```bash
pip install -e ".[dev]"
```

### 2. Configure variables

```bash
cp .env.example .env
```

On Windows, copy `.env.example` to `.env` manually or use PowerShell:

```powershell
Copy-Item .env.example .env
```

### 3. Start PostgreSQL and Redis

```bash
docker compose up -d postgres redis
```

### 4. Apply migrations

```bash
alembic upgrade head
```

### 5. Start the API

```bash
python -m uvicorn blueberry_microid.interfaces.api.app:create_app --factory --reload
```

Available endpoints:

- API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

## Tests

Run the default suite:

```bash
pytest -v
```

Validate the full PostgreSQL migration chain using a configured PostgreSQL
`DATABASE_URL`:

```bash
python scripts/check_postgres_migrations.py
```

GitHub Actions also validates PostgreSQL-specific behavior and a real
FastAPI/Celery/Redis smoke path.

## Key documentation

- [`docs/mvp/README.md`](docs/mvp/README.md): demonstrable MVP scope.
- [`docs/api/two_image_upload_analysis.md`](docs/api/two_image_upload_analysis.md): official analysis API.
- [`ARCHITECTURE.md`](ARCHITECTURE.md): architecture and historical phase detail.
- [`docs/development.md`](docs/development.md): development procedures.
- [`CLAUDE.md`](CLAUDE.md): repository development constraints and historical decisions.

## Non-goals for the MVP

- confirmed genus or species identification;
- claims of diagnostic or scientific accuracy;
- replacing expert review;
- automatic inclusion of uploads in training datasets;
- training or promoting a production YOLO model during normal API execution.
