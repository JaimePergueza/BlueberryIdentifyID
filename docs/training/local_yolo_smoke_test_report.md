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

## Fase 36 Local YOLO Minimal Training Execution

- Date: 2026-07-04
- Pending commit at execution time
- Initial Fase 35 execution id requested: `b5eb9008-ee86-4dfe-a35e-e7e4c33517c1`
- Actual execution id used: `2395f350-0e95-4ba5-8e98-6836226c0fdf`
- Reason for new id: the Fase 35 id was no longer present in local PostgreSQL, so a new local seed was persisted before training.
- Original bundle dataset yaml: `D:\BlueberryMicroID_training_artifacts\bundle\fase36_local_training_fixture-20260704135949\dataset.yaml`
- YOLO-compatible dataset yaml used for training: `D:\BlueberryMicroID_training_artifacts\yolo_views\fase36_smoke_canonical\dataset.yaml`
- Artifact root: `D:\BlueberryMicroID_training_artifacts`
- Base model path: `D:\BlueberryMicroID_training_artifacts\base_models\yolov8n_blueberry_smoke.yaml`
- Base model type: local YAML architecture copied from the locally installed `ultralytics` package, not downloaded weights.

Pre-flight results:

```text
repository safety: is_safe=true
training docs: training docs validation passed
PostgreSQL select 1: 1
alembic current: 0021 (head)
ultralytics import: ok, version 8.4.87
```

Persisted gate inspection:

```json
{
  "annotation_bundle_status": "completed",
  "annotation_quality_gate_status": "passed",
  "artifact_policy_status": "ready",
  "detection_training_status": "planned",
  "environment_status": "ready",
  "execution_status": "ready_to_execute",
  "readiness_decision": "ready_for_training",
  "readiness_status": "warning"
}
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

Training command:

```text
python scripts/run_local_yolo_training.py --execution-run-id 2395f350-0e95-4ba5-8e98-6836226c0fdf --dataset-yaml D:/BlueberryMicroID_training_artifacts/yolo_views/fase36_smoke_canonical/dataset.yaml --artifact-root-dir D:/BlueberryMicroID_training_artifacts --base-model-path D:/BlueberryMicroID_training_artifacts/base_models/yolov8n_blueberry_smoke.yaml --confirmation-text "I confirm local YOLO training outside CI" --epochs 1 --image-size 320 --batch-size 1 --device cpu --workers 0 --run-name fase36_smoke --allow-existing-output-dir
```

Training result:

```json
{
  "artifact_root_dir": "D:\\BlueberryMicroID_training_artifacts",
  "dataset_yaml_path": "D:\\BlueberryMicroID_training_artifacts\\yolo_views\\fase36_smoke_canonical\\dataset.yaml",
  "execution_run_id": "2395f350-0e95-4ba5-8e98-6836226c0fdf",
  "save_dir": "D:\\BlueberryMicroID_training_artifacts\\fase36_smoke",
  "summary": {
    "artifact_kinds": [
      "actual_metrics",
      "actual_weights",
      "other"
    ],
    "metadata_only": true,
    "no_binary_content_stored": true,
    "record_count": 15
  }
}
```

Generated external artifacts include:

- `D:\BlueberryMicroID_training_artifacts\fase36_smoke\weights\best.pt`
- `D:\BlueberryMicroID_training_artifacts\fase36_smoke\weights\last.pt`
- `D:\BlueberryMicroID_training_artifacts\fase36_smoke\results.csv`
- `D:\BlueberryMicroID_training_artifacts\fase36_smoke\args.yaml`
- PNG/JPG plots generated by Ultralytics under `D:\BlueberryMicroID_training_artifacts\fase36_smoke`

Weight checksums:

```text
best.pt sha256=0E322D1DF754F6BDD72E7FFD464B54BFE1BEEA6DD1072C09F9F6FC7E491B26CE
last.pt sha256=5ED0416B3DB90BEFF0817407B2ED080A816B822CD6D47BB924D915BF7B08D177
```

Metadata-only registry:

```json
{
  "artifact_count": 19,
  "artifact_summary": {
    "actual_metrics": 1,
    "actual_weights": 2,
    "other": 12,
    "planned_metrics": 1,
    "planned_predictions": 1,
    "planned_run_dir": 1,
    "planned_weights": 1
  }
}
```

Important operational notes:

- Smoke decision: `smoke_training_completed`.
- The run is a technical smoke only, not a scientific model.
- Ultralytics emitted warnings that no labels were found during metric computation; the generated weights prove execution, not dataset quality.
- On first Ultralytics import/training, Ultralytics downloaded `Arial.ttf` into `D:\BlueberryMicroID_training_artifacts\ultralytics_config\Ultralytics`. This was not a dataset or model weight, but it is an automatic runtime asset download and should be disabled/pre-seeded before stricter future runs.
- No model weights were created inside the repository.
- No binary content was stored in the database; only paths, sizes, states, kinds, and checksums were recorded.
- No external dataset was used.
- No taxonomy, genus/species claim, or microbiological diagnosis was added.
- CI remains a non-training workflow.

Post-test final persisted run:

- Reason: `pytest -m postgres` resets local PostgreSQL state, so a final seed
  and smoke run were executed after tests to leave a real local training run
  inspectable.
- Final execution id: `9b4e75f4-7ef1-4438-ab4e-e3fa6fde3383`
- Final dataset yaml: `D:\BlueberryMicroID_training_artifacts\yolo_views\fase36_smoke_final\dataset.yaml`
- Final save dir: `D:\BlueberryMicroID_training_artifacts\fase36_smoke_final`
- Final artifact count in DB: 19
- Final actual weights: 2
- Final actual metrics: 1

Final weight checksums:

```text
best.pt sha256=584AFC2DEAC65C176A8A69144C1108169DD20DA7CC939B6342FB75904C17F79C
last.pt sha256=38A3B692B7CA3A94AE5782A9DD246121FD16C9797074D1FA70BD6461E3ADF894
```

Final inspector command:

```text
python scripts/inspect_local_yolo_training_run.py --local-training-run-id 9b4e75f4-7ef1-4438-ab4e-e3fa6fde3383
```

## Fase 37 YOLO Label Export Fix and Runtime Asset Control

- Date: 2026-07-04
- Pending commit at execution time
- Decision: `smoke_training_blocked` for the real training rerun because the permission/usage reviewer rejected the external training command before execution.
- Code/data fix status: completed locally.

Root cause:

- The original bundle `dataset.yaml` was not directly trainable by Ultralytics because it did not define `train` or `val`; it only pointed `test` to `external_image_paths`.
- The original YOLO label file existed but was empty.
- Code root cause: `AnnotationBundleWriter._yolo_lines()` only read `manifest["labels"]`. The seed used `blueberry_manifest`, which stores `annotations`/`bbox` rather than a `labels` section, so YOLO `.txt` files were emitted empty.
- A canonical YOLO `images/` and `labels/` training view was also missing.

Fixes added:

- `AnnotationBundleWriter` now derives YOLO label lines from `blueberry_manifest` image dimensions and reviewed bbox data when a YOLO `labels` section is absent.
- `scripts/validate_yolo_training_dataset.py` validates trainable YOLO datasets without importing `ultralytics` or `torch`.
- `scripts/build_yolo_training_view.py` builds an external Ultralytics-compatible `images/{split}` and `labels/{split}` view from a reviewed bundle.
- `LocalYoloTrainingRunner` now passes `plots=false` and `pretrained=false` to reduce runtime asset downloads and avoid implicit pretrained weights.

Original dataset validation:

```json
{
  "is_trainable": false,
  "issues": [
    {"code": "train_missing"},
    {"code": "val_missing"},
    {"code": "split_path_missing"},
    {"code": "train_labels_missing"},
    {"code": "val_labels_missing"}
  ]
}
```

External YOLO view built:

```text
D:\BlueberryMicroID_training_artifacts\yolo_training_views\fase37_smoke\dataset.yaml
```

Validated view result:

```json
{
  "is_trainable": true,
  "image_count": 3,
  "label_file_count": 3,
  "non_empty_label_file_count": 3,
  "annotation_count": 3
}
```

Dry-run validation against persisted records:

```json
{
  "summary": {
    "metadata_persisted": false,
    "training_would_run": true,
    "ultralytics_imported": false,
    "validation_only": true,
    "training_kwargs": {
      "plots": false,
      "pretrained": false
    }
  }
}
```

Real training rerun:

```text
blocked before execution by permission/usage reviewer:
Automatic approval review failed: You've hit your usage limit.
```

No Fase 37 training weights were generated. No Fase 37 binaries were stored in
the database. No external datasets, taxonomy, diagnosis, genus/species labels,
or CI training steps were added.

## Fase 38 YOLO Labels-Fixed Smoke Training Rerun

- Date: 2026-07-04
- Pending commit at execution time
- Decision: `smoke_training_completed_with_labels`.
- Detection training execution run used for the final post-test smoke: `c3239bbe-869a-4e22-90c5-427e568328bf`.
- Requested historical execution id `b5eb9008-ee86-4dfe-a35e-e7e4c33517c1` was not present in the local PostgreSQL database at rerun time.
- Intermediate execution id `9b4e75f4-7ef1-4438-ab4e-e3fa6fde3383` was used before final tests, then removed when `pytest -m postgres` reset local PostgreSQL state.
- Dataset YAML: `D:\BlueberryMicroID_training_artifacts\yolo_training_views\fase37_smoke\dataset.yaml`.
- YOLO training view: `D:\BlueberryMicroID_training_artifacts\yolo_training_views\fase37_smoke`.
- Artifact root: `D:\BlueberryMicroID_training_artifacts`.
- Base model path: `D:\BlueberryMicroID_training_artifacts\base_models\yolov8n_blueberry_smoke.yaml`.
- YOLO config dir: `D:\BlueberryMicroID_training_artifacts\ultralytics_config`.
- Run name: `fase38_smoke_labels_fixed_final`.
- Run dir: `D:\BlueberryMicroID_training_artifacts\fase38_smoke_labels_fixed_final`.

Pre-run validation:

```json
{
  "is_trainable": true,
  "image_count": 3,
  "label_file_count": 3,
  "non_empty_label_file_count": 3,
  "annotation_count": 3,
  "issues": []
}
```

Dry-run validation:

```json
{
  "summary": {
    "metadata_persisted": false,
    "training_would_run": true,
    "ultralytics_imported": false,
    "validation_only": true,
    "training_kwargs": {
      "plots": false,
      "pretrained": false
    }
  }
}
```

Training command configuration:

```text
epochs=1
image_size=320
batch_size=1
device=cpu
workers=0
plots=false
pretrained=false
```

Ultralytics label evidence:

```text
train: Scanning ... labels\train... 1 images, 0 backgrounds, 0 corrupt
Epoch 1/1 ... Instances 3
val: Scanning ... labels\val... 1 images, 0 backgrounds, 0 corrupt
Class all Images 1 Instances 1
```

No `no labels found` or `labels empty` message was observed. The metrics were
computed as a smoke test only and are not scientifically useful:

```text
metrics/precision(B)=0
metrics/recall(B)=0
metrics/mAP50(B)=0
metrics/mAP50-95(B)=0
```

Generated artifacts:

```text
D:\BlueberryMicroID_training_artifacts\fase38_smoke_labels_fixed_final\args.yaml
D:\BlueberryMicroID_training_artifacts\fase38_smoke_labels_fixed_final\results.csv
D:\BlueberryMicroID_training_artifacts\fase38_smoke_labels_fixed_final\weights\best.pt
D:\BlueberryMicroID_training_artifacts\fase38_smoke_labels_fixed_final\weights\last.pt
```

Registered metadata-only checksums:

```text
results.csv sha256=ee72b8f808e94e580792d2b4ec194f09f5e4803c6bebd4ebaf5b1b83b156ac50
best.pt sha256=abc791316fa719b11092038fdb0dfeba918f488e607c22c194f1505c0255a65d
last.pt sha256=983eac9260c8442ced6477e3dec8e75828fb55ed1133049c938d6914f15216b6
args.yaml sha256=c9807edc9a203664b8a4b669fd69ae427f58f86942d492df7f159e9cf09f21f8
```

Runtime assets before and after were unchanged and stayed outside the
repository:

```text
D:\BlueberryMicroID_training_artifacts\ultralytics_config\Ultralytics\Arial.ttf
D:\BlueberryMicroID_training_artifacts\ultralytics_config\Ultralytics\persistent_cache.json
D:\BlueberryMicroID_training_artifacts\ultralytics_config\Ultralytics\settings.json
```

`Arial.ttf` was already present from the earlier smoke run and did not appear
as a new repository artifact. No model weights were created inside the
repository. No binary content was stored in the database; only paths, kinds,
states, sizes, and checksums were registered. No external dataset, taxonomy,
genus/species claim, microbiological diagnosis, frontend, authentication, or
CI training step was added.
## Fase 39 Smoke Model Evaluation and Promotion Gate

- Date: 2026-07-04
- Source local training execution run: `d2d0c627-d5b2-4528-888e-af899e4f4537`
- Model candidate id: `84496312-01aa-4d00-a2a0-affa415fd255`
- Model evaluation run id: `055414c1-756b-45cb-8afd-66d4c768c2d3`
- Promotion gate run id: `0218bfc9-ed50-47a8-bc27-eb4f9761e18a`
- Evaluation decision: `smoke_only`
- Promotion decision: `not_promotable`
- Metrics: precision `0`, recall `0`, mAP50 `0`, mAP50-95 `0`.
- Blocking reasons: `smoke_only`, `metrics_zero`, `dataset_insufficient`.

Fase 39 did not train, did not run inference, did not load weights, did not
copy artifacts, and did not store binary content in PostgreSQL. It created
metadata-only candidate/evaluation/gate records so the Fase 38 smoke weights
are explicitly classified as smoke-only and not promotable. The smoke model
is not a scientific model and must not be used for production inference.
After the PostgreSQL integration test reset, the existing Fase 38 external
artifacts were re-registered as metadata-only records against the local Fase
39 execution policy before evaluation; no files were copied and no new
training run was executed for this evaluation.
