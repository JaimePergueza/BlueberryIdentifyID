# Snapshot-Only Dataset Releases

Fase 45 adds a metadata-only release path:

```http
POST /api/v1/datasets/releases/from-snapshot
```

The endpoint reads an existing curated `DatasetSnapshot`, selects eligible
included `DatasetItem` rows, calculates `label_distribution`, and persists a
`DatasetRelease` with `release_kind=snapshot_release`.

Snapshot-only releases:

- store a deterministic metadata manifest on `DatasetRelease.manifest`;
- store release provenance on `DatasetRelease.provenance`;
- do not call `DatasetSplitter`;
- do not create `DatasetSplitItem` rows;
- do not create train/validation/test partitions;
- do not copy images;
- do not train, run YOLO, or export COCO/YOLO annotations.

`GET /api/v1/datasets/releases/{release_id}` returns either a traditional
`split_release` or a `snapshot_release`. `GET
/api/v1/datasets/releases/{release_id}/items` returns split item rows for
split releases and manifest items for snapshot releases.

The manifest contains IDs, labels, review provenance, and optional curation
references only. It never contains image bytes, model weights, secrets,
taxonomy, or diagnostic claims.
