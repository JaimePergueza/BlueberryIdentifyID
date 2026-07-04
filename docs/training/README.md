# Training Operations Documentation

This folder was created in Fase 30 as preventive operational documentation for a future manual object-detection training attempt. It does not enable real training.

## Reading Order

1. `manual_training_runbook.md` explains the end-to-end human procedure and required upstream gates.
2. `operator_checklist.md` gives the checkbox list an operator must complete before any future attempt.
3. `artifact_registration_protocol.md` describes future metadata-only registration of artifacts.
4. `rollback_protocol.md` explains how to stop and preserve traceability after a failed or unsafe attempt.
5. `prohibited_actions.md` lists actions that remain forbidden.

## Current Boundary

There is no real YOLO training in this phase. The project does not install `ultralytics`, does not import `torch`, does not use PyTorch/TensorFlow, does not download weights, does not generate weights, and does not train in CI.

Any future training must happen outside CI, under a later approved phase, with artifacts stored under an external `artifact_root_dir`. Weights and generated training outputs must not enter the Git repository or PostgreSQL.
