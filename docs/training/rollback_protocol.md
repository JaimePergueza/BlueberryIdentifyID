# Rollback Protocol

## Purpose

This protocol defines what a human operator should do if a future manual training attempt fails, produces unsafe artifacts, or violates a prerequisite. It does not execute cleanup automatically in Fase 30.

It covers rollback decisions and failed artifacts without preserving unsafe binaries.

## If Future Training Fails

Stop the attempt, preserve minimal text evidence, record the failed gate or runtime condition, and prevent any generated artifact from being used as an approved model.

Do not retry by changing labels, dataset splits, taxonomy, or command parameters outside the approved gate sequence.

## Incomplete Weights

If incomplete weights are generated in a future phase, keep them outside the repository, mark them as failed or ignored in future artifact metadata, and delete the binary only after recording enough traceability to explain the failure.

Do not commit `.pt`, `.onnx`, `.h5`, `.pth`, `.ckpt`, or similar files.

## Artifact Inside Repository

If any generated artifact appears inside the repository, stop immediately. Confirm whether Git can see it, record the path, remove or relocate it only according to an approved human procedure, and rerun repository safety checks.

Do not commit a cleanup that hides the incident without recording what happened.

## Broken artifact_root_dir

If `artifact_root_dir` is missing, full, unavailable, symlinked into the repo, or inconsistent with the artifact policy, stop. Create a new artifact policy in a future authorized phase rather than editing evidence after the fact.

## Dataset Mismatch

If the dataset used for future training does not match the approved `AnnotationBundleRun`, `AnnotationQualityGateRun`, `DetectionTrainingRun`, or `DetectionTrainingExecutionRun`, stop and mark the attempt invalid.

A changed bundle requires a new quality gate and downstream training gates.

## Invalid Metrics

If metrics are missing, malformed, suspicious, or inconsistent with persisted predictions, do not invent replacements. Mark the metrics artifact failed or ignored in a future registration phase and preserve the raw failure notes outside the repository.

## Incorrect Labels

If labels are discovered to be incorrect after quality approval, do not edit labels in place. Create a corrected annotation flow, generate a new bundle, run a new annotation quality gate, and create new downstream training gates.

## Deleted Or Ignored Artifacts

In a future artifact registry, invalid artifacts should be marked `deleted` or `ignored` with reason, timestamp, related training run, and policy reference. The goal is traceability without preserving unsafe binaries.

## Incident Documentation

Document the incident with small text evidence: operator, timestamp, affected gate IDs, artifact paths, checksums if available, repository status, CI status, and final decision.

Do not include images, model weights, full labels, secrets, or heavy logs in the repository or database.
