from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from blueberry_microid.ml.configs.training_config import TrainingConfig
from blueberry_microid.ml.data.json_manifest_dataset_loader import JsonManifestDatasetLoader


def _load_config(path: str | None) -> TrainingConfig:
    if path is None:
        return TrainingConfig(experiment_name="manifest-validation", output_dir="training-output")
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return TrainingConfig.from_dict(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a DatasetRelease training manifest without training a model."
    )
    parser.add_argument("manifest_path", help="Path to the DatasetRelease manifest JSON.")
    parser.add_argument("--config", help="Optional TrainingConfig JSON path.", default=None)
    args = parser.parse_args(argv)

    loader = JsonManifestDatasetLoader()
    try:
        config = _load_config(args.config)
        manifest = loader.load_manifest(args.manifest_path)
        report = loader.validate_manifest(manifest, config)
    except Exception as exc:
        print(json.dumps({"is_valid": False, "errors": [str(exc)]}, indent=2), file=sys.stderr)
        return 2

    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.is_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

