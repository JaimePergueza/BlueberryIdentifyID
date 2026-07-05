# Dataset Curation from Human Reviews

`DatasetCurationRun` records an auditable pass over human-reviewed two-image
analyses. It stores one `DatasetCurationItem` per candidate, including the
reason an item was included or excluded.

Eligibility for an included item requires:

- an `AnalysisRun`;
- a `Prediction`;
- a final `HumanReview`;
- one Petri image;
- one microscopy image;
- an allowed preliminary visual label derived from the final review.

`Prediction` is never ground truth on its own. It can become the final label
only when a human review confirms it. Corrected reviews use
`HumanReview.corrected_label`; inconclusive reviews use `inconclusive`;
invalid samples are excluded from trainable data.

Fase 44 adds a separate freeze step:

```http
POST /api/v1/datasets/snapshots/from-curation-run
```

That endpoint creates a `DatasetSnapshot` from already-included curation
items and writes provenance onto each `DatasetItem`. It does not create a
`DatasetRelease`, does not split data, does not train, does not run YOLO, does
not copy images, does not store binaries, and does not add taxonomy or
diagnostic claims.
