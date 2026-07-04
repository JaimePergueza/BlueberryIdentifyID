# Manual Training Runbook

## 1. Purpose

This runbook defines the human procedure for a future manual object-detection training attempt for BlueberryMicroID. It is preventive documentation only. It does not authorize, execute, automate, or validate real YOLO training in this phase.

The target use case is Petri candidate-region detection for blueberry-related lab imagery. `candidate_region` is an annotation category, not a microbiological diagnosis, not a species, and not a genus.

## 2. Scope

The runbook covers the operator checks that must happen after the existing planning gates have already produced persisted records. It explains how to review those records, how to keep artifacts outside the repository, how to handle evidence, and how to stop safely when a prerequisite is not met.

It applies only to a future manual execution outside CI. It does not apply to FastAPI request handling, Celery mock processing, Redis operations, PostgreSQL migrations, or any automated CI job.

## 3. What This Document Does Not Permit

This document does not permit training YOLO, executing YOLO, installing `ultralytics`, installing or importing `torch`, using PyTorch, using TensorFlow, creating CNN/ViT/deep-learning code, downloading weights, downloading datasets, creating model binaries, or replacing `MockInferenceEngine`.

It also does not permit modifying original images, copying images into the repository, storing binary artifacts in the database, training in CI, adding taxonomy, or making microbiological diagnosis claims.

## 4. Mandatory Prerequisites

Before a future operator may consider manual training, the repository must be on the intended branch, the working tree must be clean, CI must be green for the latest commit, and the `.gitignore` must include model-weight and training-output patterns.

The operator must have an approved external `artifact_root_dir` that is outside the Git repository. The directory must have enough free space and must not be a path that Git can stage by accident.

The approved dataset must come from the existing annotation workflow. External datasets are out of scope unless a later phase creates a formal review path for them.

## 5. Gates That Must Be Approved

All of these persisted gates must exist and be reviewed before a future manual training attempt:

- `AnnotationBundleRun` status must be `completed`.
- `AnnotationQualityGateRun` status must be `passed`.
- `DetectionTrainingRun` status must be `planned`.
- `DetectionTrainingReadinessReport` status must be `ready`.
- `DetectionTrainingEnvironmentSpec` status must be `ready`.
- `DetectionTrainingArtifactPolicy` status must be `ready`.
- `RepositorySafetyValidator` must report `passed`/safe for the repository and candidate artifact paths.
- `DetectionTrainingExecutionRun` status must be `manual_required` or `ready_to_execute`.

`ready_to_execute` means the manual gate is satisfied. It does not mean training already occurred, and it does not mean the command may be copied blindly.

## 6. Environment Validation

The operator must confirm that the future execution environment matches the persisted `DetectionTrainingEnvironmentSpec`. The environment review must include Python version, operating system, CI detection, dependency policy, GPU/CUDA policy if any, base-weights policy, and artifact storage policy.

This phase does not install any dependency. Do not install `ultralytics`, `torch`, TensorFlow, CUDA packages, or GPU tooling from this runbook.

## 7. Repository Validation

Run the repository safety check in read-only mode before any future manual training step. The check must verify `.gitignore` coverage for weight extensions and output directories, and it must reject candidate weight paths inside the repository.

The repository must remain clean before and after the future manual attempt. If Git sees weights, checkpoints, run directories, or generated predictions under the repository, stop and follow the rollback protocol.

## 8. External artifact_root_dir Validation

The `artifact_root_dir` must be an absolute path outside the repository. It must be reserved for generated training outputs and must not be a symlink or nested directory that resolves back into the repository.

The operator must record the resolved artifact root path, free-space check, and policy decision. Do not create or copy artifacts into `docs/`, `src/`, `tests/`, `storage/`, or any other tracked repository path.

## 9. Interpreting command_preview

`command_preview` is a persisted JSON preview of a possible future command. It is not an executable instruction in this phase. It must be treated as documentation that a human reviews against the approved gates.

If a command is shown in project records or documentation, it must be labeled as `command_preview`. Do not run it directly without a later phase explicitly authorizing real execution.

Example, not executable in this phase:

```text
command_preview: yolo detect train data=<approved_dataset_yaml> project=<external_artifact_root_dir>
```

## 10. Pre-Training Checklist

Use `docs/training/operator_checklist.md`. Every required checkbox must be completed before a future training attempt. Any unchecked critical item is a stop condition.

## 11. Evidence Registration

The operator must preserve human-readable evidence: gate IDs, statuses, timestamps, repository commit hash, CI run URL, resolved `artifact_root_dir`, safety report, planned command preview, and any incident notes.

Evidence should be small text or JSON records. Do not store images, labels in bulk, model weights, checkpoints, or generated binaries in the database or repository.

## 12. Post-Training Artifact Registration

Real artifact registration is a future phase. The future registration record should store metadata such as artifact kind, path or external URI, size, `checksum_sha256`, state, creation time, related training run, and artifact policy.

Do not copy artifacts into the repository for registration. Do not store binaries in PostgreSQL.

## 13. Error Handling

If any gate is missing, blocked, warning-only where ready is required, or inconsistent with another gate, stop. Record the reason and do not attempt to patch the training command manually.

If future training fails, preserve the minimum text evidence needed for traceability, mark generated outputs according to the future artifact protocol, and follow `docs/training/rollback_protocol.md`.

## 14. Rollback

Rollback is a human procedure in this phase. It means stopping the attempt, preventing invalid artifacts from being used, keeping traceability records, and confirming the repository is clean.

No automatic deletion or cleanup script is introduced here.

## 15. Prohibited Actions

The full prohibited action list is in `docs/training/prohibited_actions.md`. The short version: do not train in CI, do not upload weights to Git, do not store weights in DB, do not modify original images, do not change labels after the quality gate without a new bundle, do not add taxonomy, and do not execute `command_preview` directly in this phase.

## 16. Procedure Closure

At closure, the operator must record whether the future manual attempt was not started, stopped before training, failed, or completed in a later authorized phase. The repository must remain clean, CI must remain green for code changes, and any artifact metadata must point outside the repository.

This runbook is complete for Fase 30 when it can guide a human review without executing any training.
