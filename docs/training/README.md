# Training Operations Documentation

This folder was created in Fase 30 as preventive operational documentation for a future manual object-detection training attempt. Fase 31 adds an experimental local/manual runner, and Fase 32 validates the local dependency/import path plus runner dry-run validation. This folder remains the operator guidance for keeping that runner outside CI and outside the repository.

## Reading Order

1. `manual_training_runbook.md` explains the end-to-end human procedure and required upstream gates.
2. `operator_checklist.md` gives the checkbox list an operator must complete before any future attempt.
3. `artifact_registration_protocol.md` describes future metadata-only registration of artifacts.
4. `rollback_protocol.md` explains how to stop and preserve traceability after a failed or unsafe attempt.
5. `prohibited_actions.md` lists actions that remain forbidden.

## Current Boundary

Fase 31 may run real YOLO training only through the local/manual runner, after all gates pass and after the exact manual confirmation is provided. Fase 32 adds `--dry-run-validation-only` for the local CLI so an operator can validate the same persisted gates and local paths without importing `ultralytics`, training, or registering artifacts. CI still does not train, does not require `ultralytics`, does not require `torch`, does not require GPU, does not download weights, and does not generate weights.

Any local training must happen outside CI, with artifacts stored under an external `artifact_root_dir`. Weights and generated training outputs must not enter the Git repository or PostgreSQL; only metadata such as path, size, checksum, kind, state, and related execution run may be registered.

Fase 32 operational status: local installation of the `training` extra and `ultralytics` import were validated in the Codex runtime. Full real training was not executed because this workstation did not expose a usable local PostgreSQL database, persisted `DetectionTrainingExecutionRun`, ready `DetectionTrainingArtifactPolicy`, or generated `dataset.yaml` bundle. The next real smoke requires those records and an approved external artifact root before running without `--dry-run-validation-only`.
