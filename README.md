# BlueberryMicroID

> The GitHub repository keeps the historical name `BlueberryIdentifyID`; the application and Python package are named **BlueberryMicroID**.

BlueberryMicroID is a full-stack web platform for **preliminary, explainable analysis of microorganism-associated visual patterns in blueberry laboratory samples**. Each analysis combines a Petri-dish photograph and a microscopy photograph, extracts classical visual evidence from both, resolves contradictory signals conservatively, and requires a human specialist to confirm or correct the result.

The project is designed around traceability rather than black-box automation: every analysis stores extracted features, quality indicators, model/engine version, decision trace, review history and final expert resolution.

## Portfolio highlights

This repository demonstrates practical experience with:

- **Backend engineering:** FastAPI, SQLAlchemy 2, Alembic, PostgreSQL and application-layer use cases.
- **Frontend engineering:** React, TypeScript, Vite, React Router and TanStack Query.
- **Distributed processing:** Celery with Redis and authenticated worker smoke paths.
- **Computer vision:** Pillow, NumPy and OpenCV for Petri and microscopy feature extraction.
- **Security:** Argon2 password hashing, opaque revocable bearer sessions, role-based authorization and protected image access.
- **Architecture:** Clean Architecture / Ports and Adapters with explicit domain, application and infrastructure boundaries.
- **Quality engineering:** unit, API, PostgreSQL, frontend, Celery and full-stack Docker validation in CI.
- **Scientific restraint:** automatic outputs are explicitly preliminary, non-diagnostic and subject to mandatory expert review.

## Scientific scope

BlueberryMicroID is **not a diagnostic system** and does not claim confirmed genus or species identification. The current image-analysis rules are transparent, non-trained heuristics and have not been scientifically validated against a labelled dataset.

The morphology differential may compare broad visual compatibility with patterns reported for blueberry-associated fungi, but these values are **not calibrated probabilities** and are never treated as ground truth. Every automatic result requires expert review.

## Official analysis workflow

An authenticated user with role `specialist` or `admin` can submit a paired sample through the web interface or via:

```http
POST /api/v1/analysis/two-image-upload
Authorization: Bearer <access_token>
```

The official workflow:

1. validates and stores the Petri and microscopy images;
2. persists sample and capture metadata;
3. isolates the relevant visual regions and evaluates capture quality;
4. extracts macroscopic and microscopic morphology signals;
5. produces an explainable preliminary category;
6. evaluates coherence between broad classification and morphology evidence;
7. abstains as `inconclusive` when evidence is insufficient or contradictory;
8. records the engine identity and full decision trace;
9. marks the result as requiring human review;
10. lets a specialist confirm or correct the result without overwriting the original automatic evidence.

Current analyses use **`PreliminaryTwoImageEngine` 0.6.0**. Historical predictions remain immutable and retain the engine version that produced them.

Version 0.6.0 adds a preliminary count of Petri candidate regions, abstains from counting unsuitable or confluent captures, and preserves an optional specialist-confirmed count alongside the automatic evidence. It does not estimate CFU/mL or establish biological colony identity. See [`docs/product/colony_count.md`](docs/product/colony_count.md).

Relevant endpoints include:

```http
POST /api/v1/analysis-runs/{analysis_run_id}/reviews
GET  /api/v1/analysis-runs/{analysis_run_id}/preliminary-result
GET  /api/v1/analysis-runs/{analysis_run_id}/final-result
GET  /api/v1/analysis-runs
GET  /api/v1/analysis-runs/{analysis_run_id}/detail
```

The repository also keeps `MockInferenceEngine` for legacy orchestration and smoke-test paths. It is not the official image-analysis entry point.

## Authentication and authorization

Only `GET /health` and `POST /api/v1/auth/login` are public. Operational routes require an authenticated bearer session.

- `specialist`: samples, images, analyses, history and human review.
- `admin`: all specialist operations plus user administration and technical model/dataset/audit routes.

Security properties:

- passwords hashed with Argon2;
- opaque high-entropy session tokens;
- only SHA-256 token hashes persisted;
- configurable expiration;
- session revocation on password, role or active-state changes;
- administrator bootstrap without committed default credentials;
- protected image-content endpoints that do not expose physical storage paths;
- interactive API documentation disabled in production.

See [`docs/api/authentication.md`](docs/api/authentication.md) and [`docs/security/access_control_matrix.md`](docs/security/access_control_matrix.md).

## Web interface

The React/TypeScript application under [`frontend/`](frontend/) supports the complete operational workflow without requiring Swagger:

- login and expired-session handling;
- role-aware navigation;
- administrator user management;
- operational dashboard;
- paired Petri/microscopy upload with metadata and previews;
- visual segmentation overlays;
- quality-gate warnings and blocking reasons;
- explainable preliminary result;
- morphology differential and coherence assessment;
- expert review;
- searchable and paginated history;
- consolidated automatic-versus-human traceability detail.

## Current product status

Implemented:

- authentication with revocable sessions;
- `admin` and `specialist` roles;
- administrator user management and secure bootstrap command;
- operational React/TypeScript frontend;
- sample, metadata and protected image persistence;
- strict upload validation;
- Petri and microscopy segmentation;
- capture-quality gating;
- classical morphology feature extraction;
- explainable preliminary classification;
- blueberry-focused morphology differential;
- coherence resolution and conservative abstention;
- human review and final-result resolution;
- paginated analysis history and filters;
- auditable dataset curation, snapshots and releases;
- PostgreSQL migrations;
- synchronous and Celery-backed processing paths;
- reproducible Docker Compose deployment;
- synthetic demonstration data and demo seeding;
- backend, frontend, PostgreSQL, Celery and full-stack smoke validation in GitHub Actions.

The main remaining product-quality work is scientific validation with a controlled labelled dataset, stronger browser-level end-to-end coverage, observability and production deployment hardening.

## Technology

### Backend

- Python 3.10+
- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL 16
- Celery
- Redis
- pwdlib / Argon2
- Pillow
- NumPy
- OpenCV
- scikit-learn
- pytest

### Frontend

- React
- TypeScript
- Vite
- React Router
- TanStack Query
- Vitest
- Testing Library

### Deployment

- Docker / Docker Compose
- Nginx frontend gateway
- PostgreSQL and Redis persistent volumes
- isolated API and worker services
- migration-gated startup

## Architecture

The backend follows Clean Architecture / Ports and Adapters:

```text
interfaces/       HTTP and external entry points
application/      use cases, DTOs, ports, application services
domain/           entities, enums, value objects, business rules
infrastructure/   SQLAlchemy, storage, security, configuration, tasks
ml/               image processing, validation, differential and training contracts
```

The backend remains the source of business and scientific workflow rules; the frontend consumes typed contracts and does not duplicate analysis logic.

## Local development

### 1. Create the backend environment

```bash
python -m venv .venv
```

Activate it and install development dependencies:

```bash
pip install -e ".[dev]"
```

### 2. Configure local variables

```bash
cp .env.example .env
```

On Windows:

```powershell
Copy-Item .env.example .env
```

Real environment files are excluded from Git. Do not commit credentials.

### 3. Start PostgreSQL and Redis

```bash
docker compose up -d postgres redis
```

### 4. Apply migrations

```bash
alembic upgrade head
```

### 5. Create the first administrator

```bash
python scripts/create_admin.py
```

The command prompts for credentials; there is no committed default administrator password.

### 6. Start the API

```bash
python -m uvicorn blueberry_microid.interfaces.api.app:create_app --factory --reload
```

Development endpoints:

- API docs: `http://127.0.0.1:8000/docs`
- health: `http://127.0.0.1:8000/health`

### 7. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Full-stack Docker demo

Copy the Docker environment template and replace all placeholder credentials:

```bash
cp .env.docker.example .env.docker
```

Then start the stack with the Compose environment file configured for your shell/workflow. The Compose topology includes PostgreSQL, Redis, migrations, API, Celery worker and the production frontend gateway.

The optional demo profile requires explicit demo passwords; empty passwords are not treated as valid defaults.

## Tests and validation

Backend:

```bash
pytest -v
python scripts/check_postgres_migrations.py
```

Frontend:

```bash
cd frontend
npm run check
```

CI covers:

- backend unit and API tests;
- frontend component tests and production build;
- PostgreSQL migration/integration behavior;
- authenticated Celery/Redis/API smoke flow;
- production Docker Compose build, startup, migration, demo seed and public-origin smoke validation.

## Key documentation

- [`docs/mvp/README.md`](docs/mvp/README.md): demonstrable MVP scope.
- [`docs/morphology_engine.md`](docs/morphology_engine.md): morphology, quality and scientific limitations.
- [`frontend/README.md`](frontend/README.md): frontend architecture and local use.
- [`docs/api/authentication.md`](docs/api/authentication.md): authentication and user administration.
- [`docs/security/access_control_matrix.md`](docs/security/access_control_matrix.md): route-access policy.
- [`docs/api/two_image_upload_analysis.md`](docs/api/two_image_upload_analysis.md): official analysis API.
- [`docs/api/analysis_history.md`](docs/api/analysis_history.md): history and consolidated detail API.
- [`ARCHITECTURE.md`](ARCHITECTURE.md): architecture and historical phase detail.
- [`docs/development.md`](docs/development.md): development procedures.

## Non-goals

- confirmed genus or species identification;
- diagnostic or clinical claims;
- replacing laboratory protocols or expert assessment;
- treating morphology compatibility scores as calibrated probabilities;
- automatic inclusion of uploads in training datasets;
- silently rewriting historical predictions when an engine version changes;
- training or promoting a production YOLO model during normal API execution.
