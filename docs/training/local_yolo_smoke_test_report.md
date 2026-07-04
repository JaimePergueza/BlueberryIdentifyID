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

## Fase 35 Local PostgreSQL Runtime Setup

- Date: 2026-07-04
- Pending commit at execution time
- PostgreSQL strategy: native Windows PostgreSQL 16 installed with `winget install PostgreSQL.PostgreSQL.16 --accept-package-agreements --accept-source-agreements`
- Docker used: no
- PostgreSQL service: `postgresql-x64-16`, running
- `DATABASE_URL`: `postgresql+psycopg://blueberry:***@localhost:5432/blueberry_microid`
- External storage root: `D:\BlueberryMicroID_local_storage`
- External artifact root: `D:\BlueberryMicroID_training_artifacts`

Connection check:

```text
{'database_url': 'postgresql+psycopg://blueberry:***@localhost:5432/blueberry_microid', 'select_1': 1}
```

Alembic:

```text
alembic upgrade head: succeeded through revision 0021
alembic current: 0021 (head)
```

Seed command:

```text
python scripts/seed_local_training_fixture.py --storage-root-dir D:/BlueberryMicroID_local_storage --artifact-root-dir D:/BlueberryMicroID_training_artifacts --created-by fase35-local-seed --dataset-name fase35_local_training_fixture --emit-json
```

Seed result:

```json
{
  "analysis_run_id": "26693386-f6b7-43a6-9cf7-d78e97e69437",
  "annotation_bundle_run_id": "d5651a5e-1184-4ac1-82c2-20bf7e63bbb2",
  "annotation_quality_gate_run_id": "151becce-efb1-472c-97a2-df13b2c5458c",
  "artifact_policy_id": "afc1f01c-47bd-4248-a2fe-26e42fd88d7a",
  "artifact_root_dir": "D:\\BlueberryMicroID_training_artifacts",
  "dataset_release_id": "3d4e555f-1936-4b6c-bd9f-e04df74f8922",
  "dataset_snapshot_id": "40f16d13-d8f0-46cc-804f-2ea21fd9045d",
  "dataset_yaml_path": "D:\\BlueberryMicroID_training_artifacts\\bundle\\fase35_local_training_fixture-20260704134328\\dataset.yaml",
  "detection_training_run_id": "acf9a111-3f53-4fd4-bffb-fbf1ebbce162",
  "environment_spec_id": "0305e33d-fe7a-4c99-a456-d55c3a5d71a0",
  "execution_run_id": "b5eb9008-ee86-4dfe-a35e-e7e4c33517c1",
  "human_review_id": "7909d3ba-4034-48ce-b492-b29ed7c4ccf9",
  "image_audit_run_id": "3b7cdc4d-15d6-4b05-aa0d-f8b3d835e621",
  "petri_annotation_export_run_id": "b9d39d68-84b0-4dd8-ad56-e9eabedc69f0",
  "petri_region_review_id": "b07f026d-7f9e-47fa-8a1c-763dfe620959",
  "petri_segmentation_run_id": "a9587e00-7ef1-4d6a-83f7-f87e98c16037",
  "readiness_report_id": "a7fd1183-51d8-429a-a9d1-ce4ee61cef16",
  "sample_id": "e8aa18cf-6b52-4420-8c11-e2ccb842cb3c"
}
```

Bundle validation:

- `dataset.yaml`: exists outside the repository.
- Bundle directory: exists outside the repository.
- COCO JSON: exists.
- Blueberry manifest: exists.
- YOLO labels: exist.
- README: exists.
- `manifest.json`: exists.
- No generated weights or training outputs appeared in the repository.

Inspection command:

```text
python scripts/inspect_local_training_fixture.py --execution-run-id b5eb9008-ee86-4dfe-a35e-e7e4c33517c1
```

Inspection result:

```json
{
  "annotation_bundle_status": "completed",
  "annotation_quality_gate_status": "passed",
  "artifact_policy_decision": "artifact_policy_ready",
  "artifact_policy_status": "ready",
  "detection_training_status": "planned",
  "environment_decision": "environment_ready",
  "environment_status": "ready",
  "execution_decision": "ready_for_manual_execution",
  "execution_status": "ready_to_execute",
  "readiness_decision": "ready_for_training",
  "readiness_status": "warning"
}
```

Dry-run validation command:

```text
python scripts/run_local_yolo_training.py --execution-run-id b5eb9008-ee86-4dfe-a35e-e7e4c33517c1 --artifact-root-dir D:/BlueberryMicroID_training_artifacts --base-model-path D:/BlueberryMicroID_training_artifacts/base_models/phase35-local-yolo-model.yaml --manual-confirmation-text "I understand this will run local YOLO training outside CI" --dry-run-validation-only
```

Dry-run validation result:

```json
{
  "summary": {
    "metadata_persisted": false,
    "training_would_run": true,
    "ultralytics_imported": false,
    "validation_only": true
  }
}
```

Real YOLO training was not executed in Fase 35. The exact reason is that this
phase stops after proving local PostgreSQL persistence and runner validation
against real records; the base model used here is an external local YAML
placeholder for validation only, not downloaded weights. Fase 36 can perform a
minimal real local training attempt only after an approved external local base
model policy is selected.

No weights were created, no binaries were stored in the database, no external
datasets were downloaded, no taxonomy was added, and CI remains a
non-training workflow.
