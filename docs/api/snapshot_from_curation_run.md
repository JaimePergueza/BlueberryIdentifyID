# Snapshot from Dataset Curation Run

Fase 44 adds an explicit API path to freeze a reviewed `DatasetCurationRun`
into a `DatasetSnapshot`:

```http
POST /api/v1/datasets/snapshots/from-curation-run
```

The curation run must already exist and be completed. Only
`DatasetCurationItem` rows with `curation_status=included` are eligible.
Each included item must keep references to `Sample`, `AnalysisRun`,
`PetriImage`, `MicroImage`, `Prediction`, and final `HumanReview`.

The created `DatasetItem` stores `curation_run_id`, `curation_item_id`, and
metadata-only `provenance` so auditors can trace:

`DatasetSnapshot -> DatasetItem -> DatasetCurationItem -> DatasetCurationRun -> final HumanReview`.

Ground truth remains derived from the final human review policy established
for curation. `Prediction` alone is never ground truth.

This endpoint is intentionally narrow:

- it does not create a `DatasetRelease`;
- it does not create train/validation/test splits;
- it does not copy images;
- it does not train, evaluate, or run YOLO;
- it does not store binaries in the database;
- it does not add taxonomy or diagnostic claims.

The older `create_snapshot=true` option on `POST /api/v1/datasets/curation-runs`
is preserved for compatibility. New callers should prefer the explicit
snapshot endpoint after inspecting the curation run and its items.
