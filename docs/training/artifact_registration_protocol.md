# Artifact Registration Protocol

## Purpose

This protocol describes how real training artifacts could be registered in a future phase. It does not implement registration code and does not create, copy, or validate real artifact files in Fase 30.

## Future Artifact Types

A future authorized training attempt may produce:

- weights;
- metrics;
- predictions;
- logs;
- run_dir;
- config;
- manifest.

These artifacts must remain outside the Git repository unless they are tiny text metadata files explicitly approved by policy.

## Do Not Store In The Database

Do not store binary files in PostgreSQL. Do not store weights, images, complete label files, large logs, full prediction dumps, checkpoints, run directories, or any other heavy artifact in the database.

The database should record metadata and references only.

## Metadata To Store

A future artifact registration record should store:

- absolute path when local storage is approved;
- relative_path when relative to the approved external artifact root;
- external_uri when remote storage is approved;
- artifact type;
- artifact state;
- size in bytes;
- `checksum_sha256`;
- creation or registration date;
- associated training run;
- associated artifact policy;
- evidence notes when needed.

## checksum_sha256

In a future phase, `checksum_sha256` should be calculated from the final artifact bytes after the file is closed and before the artifact is marked usable. The checksum operation must be read-only and must not change the artifact.

This phase does not implement checksum calculation.

## Failed Artifacts

If future training creates incomplete or invalid artifacts, register only minimal metadata if needed for traceability. Mark the state as failed, ignored, or deleted according to the future artifact-state model.

Do not promote failed weights or metrics to any production or scientific claim.

## Deleted Artifacts

If an invalid artifact is removed from external storage, preserve a metadata record with path, previous checksum if available, deletion time, deletion reason, and associated incident notes.

Deleted does not mean forgotten. It means the binary should no longer be used while traceability is preserved.

## External Artifact Root

Every local artifact path must resolve under the approved external `artifact_root_dir` and outside the repository. A safety validator must reject any path that resolves into the repository.

Do not copy artifacts into `docs/`, `src/`, `tests/`, `.github/`, `storage/`, or any tracked repository directory.

## Git Safety

Before and after future manual training, confirm Git cannot stage weights or generated training outputs. `.gitignore` must cover `.pt`, `.pth`, `.onnx`, `.h5`, `.ckpt`, run directories, and local training scratch paths.

If Git reports generated weights, stop and follow the rollback protocol.
