# Operator Checklist

Use this checklist before any future manual object-detection training attempt. Every item is a human confirmation. Completing this checklist does not execute training.

## Required Checks

- [ ] Confirm correct branch.
- [ ] Confirm clean working tree before any operation.
- [ ] Confirm green CI for the latest commit.
- [ ] Confirm `.gitignore` includes model-weight and training-output patterns.
- [ ] Confirm `RepositorySafetyValidator` passed.
- [ ] Confirm `AnnotationBundleRun` completed.
- [ ] Confirm `AnnotationQualityGateRun` passed.
- [ ] Confirm `DetectionTrainingRun` planned.
- [ ] Confirm `DetectionTrainingReadinessReport` ready.
- [ ] Confirm `DetectionTrainingEnvironmentSpec` ready.
- [ ] Confirm `DetectionTrainingArtifactPolicy` ready.
- [ ] Confirm `DetectionTrainingExecutionRun` exists.
- [ ] Confirm `DetectionTrainingExecutionRun` is `manual_required` or `ready_to_execute`.
- [ ] Confirm the operator is not in CI.
- [ ] Confirm `artifact_root_dir` is external to the repository.
- [ ] Confirm available disk space for the external artifact root.
- [ ] Confirm base-weights policy.
- [ ] Confirm no weights will be pushed to Git.
- [ ] Confirm rollback protocol.
- [ ] Confirm evidence registration.

## Criteria To Not Continue

Do not continue if any required gate is missing, blocked, failed, or refers to a different dataset release, annotation bundle, readiness report, environment spec, or artifact policy.

Do not continue if CI is detected, if the working tree is dirty, if `.gitignore` lacks weight patterns, if `RepositorySafetyValidator` fails, or if `artifact_root_dir` resolves inside the repository.

Do not continue if the only available instruction is an unreviewed `command_preview`. A `command_preview` is not an executable procedure in Fase 30.

Do not continue if the plan requires taxonomy, microbiological diagnosis, original-image modification, external datasets, downloaded weights, repository-stored weights, or database-stored binaries.

## Evidence To Record

- [ ] Commit hash reviewed.
- [ ] CI run URL reviewed.
- [ ] Gate IDs and statuses recorded.
- [ ] External artifact root recorded.
- [ ] Repository safety result recorded.
- [ ] Operator name or identifier recorded if policy allows it.
- [ ] Stop/go decision recorded.
