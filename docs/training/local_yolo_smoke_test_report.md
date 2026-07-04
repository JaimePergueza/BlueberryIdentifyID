# Local YOLO Smoke Test Report

## Fase 33 Status

- Date: 2026-07-04
- Commit at start: `dfa56afd46d4b95b1283e73f356721f9b59566f2`
- Database URL: `postgresql+psycopg://blueberry:blueberry@localhost:5432/blueberry_microid`
- Artifact root planned: `D:\BlueberryMicroID_training_fixture\artifacts`
- Storage root planned: `D:\BlueberryMicroID_training_fixture\storage`
- Fixture type: synthetic technical smoke fixture only
- Scientific claim: none

## Seed Result

Fase 33 adds `scripts/seed_local_training_fixture.py`, a local-only seed script
that can create the minimum persisted chain required before running the local
YOLO runner:

1. `Sample`
2. Petri image fixture
3. Micro image fixture
4. `AnalysisRun` processed by `MockInferenceEngine`
5. final `HumanReview`
6. `DatasetSnapshot`
7. `DatasetRelease`
8. `ImageDatasetAuditRun`
9. `PetriSegmentationRun`
10. final `PetriRegionReview` with `candidate_valid`
11. `PetriAnnotationExportRun`
12. completed `AnnotationBundleRun` with real `dataset.yaml`
13. passed `AnnotationQualityGateRun`
14. planned `DetectionTrainingRun`
15. ready `DetectionTrainingReadinessReport`
16. ready `DetectionTrainingEnvironmentSpec`
17. ready `DetectionTrainingArtifactPolicy`
18. `DetectionTrainingExecutionRun` with `ready_to_execute`

The script does not train, does not import `ultralytics`, does not import
`torch`, does not download images or weights, and does not create model
weights. Generated images are synthetic technical fixtures created with Pillow
at runtime and are not microbiological or scientific data.

## Local Execution Attempt

Dry-run command:

```text
python scripts/seed_local_training_fixture.py --artifact-root-dir D:\BlueberryMicroID_training_fixture\artifacts --storage-root-dir D:\BlueberryMicroID_training_fixture\storage --dry-run --emit-json
```

Result: passed. It emitted the expected JSON keys and did not persist records
or create runtime files.

Persisted seed command attempted:

```text
python scripts/seed_local_training_fixture.py --artifact-root-dir D:\BlueberryMicroID_training_fixture\artifacts --storage-root-dir D:\BlueberryMicroID_training_fixture\storage --created-by local-fixture-operator --emit-json
```

Result: blocked before migrations because PostgreSQL local was not reachable.

Exact blocking reason:

```text
PostgreSQL is not reachable at localhost:5432; start the local database before seeding
```

No persisted IDs were generated in this workstation run.

## Runner Dry-Run Validation

`dry_run_validation_only` against real persisted records was not executed in
this run because the persisted seed could not be created without PostgreSQL.
Once PostgreSQL is running and the seed succeeds, the script prints a ready
command similar to:

```text
python scripts/run_local_yolo_training.py --execution-run-id <execution_run_id> --artifact-root-dir <artifact_root_dir> --base-model-path <external-local-base-model-path> --manual-confirmation-text "I understand this will run local YOLO training outside CI" --dry-run-validation-only
```

## Real Training

Real YOLO training was not executed. The exact reason is that the required
persisted local seed records were not created because PostgreSQL was not
available. No weights were generated, no artifact metadata was registered, and
no binaries were written to the database.

## Risks Before Fase 34

- Start PostgreSQL locally at `localhost:5432` with the configured database and credentials.
- Run Alembic migrations through the seed script.
- Re-run the persisted seed and confirm all IDs are generated.
- Provide an external local `base_model_path` or an approved local model YAML path that does not download weights.
- Run `--dry-run-validation-only` against the generated `execution_run_id`.
- Only then consider a one-epoch local YOLO smoke run outside CI.

## Fase 34 Local PostgreSQL Bootstrap Attempt

- Date: 2026-07-04
- Commit at start: `307ea8d934d272019674f8e2de8182997859ce08`
- Operating system: Microsoft Windows NT 10.0.26200.0
- Existing local compose config: `docker-compose.yml`
- Docker availability: unavailable (`docker` command not found)
- Docker Compose availability: unavailable (`docker` command not found)
- Local `psql` availability: unavailable
- `localhost:5432`: not reachable
- `DATABASE_URL`: `postgresql+psycopg://blueberry:***@localhost:5432/blueberry_microid`
- External storage root prepared: `D:\BlueberryMicroID_local_storage`
- External artifact root prepared: `D:\BlueberryMicroID_training_artifacts`

Repository safety:

```json
{
  "gitignore_exists": true,
  "is_safe": true,
  "missing_gitignore_patterns": [],
  "path_violations": [],
  "recommendations": []
}
```

Training docs validation:

```text
training docs validation passed
```

Alembic status:

```text
alembic current timed out after 30 seconds because PostgreSQL was not reachable at localhost:5432
```

Seed dry-run:

```text
passed; emitted expected JSON keys with would_persist=false and would_train=false
```

Persisted seed attempt:

```text
seed_local_training_fixture failed: PostgreSQL is not reachable at localhost:5432; start the local database before seeding
```

Fase 34 closes as Cierre C in this workstation environment. The project
already has a local PostgreSQL service definition in `docker-compose.yml`, but
Docker/PostgreSQL are not available to start it here. No persisted seed IDs
were generated, no `dataset.yaml` was created, and `dry_run_validation_only`
against real persisted records was not run.

No YOLO training was executed. No weights were created, no binaries were
stored in the database, no datasets were downloaded, no taxonomy was added,
and CI remains a non-training workflow.
