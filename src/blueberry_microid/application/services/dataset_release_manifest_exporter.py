from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from blueberry_microid.application.exceptions import DatasetReleaseNotFoundError
from blueberry_microid.application.ports.dataset_item_repository import DatasetItemRepositoryPort
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.application.ports.dataset_split_item_repository import DatasetSplitItemRepositoryPort
from blueberry_microid.application.ports.micro_image_repository import MicroImageRepositoryPort
from blueberry_microid.application.ports.petri_image_repository import PetriImageRepositoryPort
from blueberry_microid.application.ports.prediction_repository import PredictionRepositoryPort
from blueberry_microid.application.ports.sample_repository import SampleRepositoryPort


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


class DatasetReleaseManifestExporter:
    """Build a deterministic manifest for a DatasetRelease's train/validation/
    test splits.

    Pure metadata — never image bytes, secrets, model performance metrics,
    or microorganism species/genus. Ordered deterministically by (split,
    analysis_run_id, dataset_split_item id), never by incidental database
    fetch order.
    """

    def __init__(
        self,
        dataset_release_repository: DatasetReleaseRepositoryPort,
        dataset_split_item_repository: DatasetSplitItemRepositoryPort,
        dataset_item_repository: DatasetItemRepositoryPort,
        sample_repository: SampleRepositoryPort,
        petri_image_repository: PetriImageRepositoryPort,
        micro_image_repository: MicroImageRepositoryPort,
        prediction_repository: PredictionRepositoryPort,
    ) -> None:
        self._dataset_release_repository = dataset_release_repository
        self._dataset_split_item_repository = dataset_split_item_repository
        self._dataset_item_repository = dataset_item_repository
        self._sample_repository = sample_repository
        self._petri_image_repository = petri_image_repository
        self._micro_image_repository = micro_image_repository
        self._prediction_repository = prediction_repository

    def export(self, dataset_release_id: UUID) -> dict[str, Any]:
        release = self._dataset_release_repository.get_by_id(dataset_release_id)
        if release is None:
            raise DatasetReleaseNotFoundError(f"dataset_release '{dataset_release_id}' does not exist")

        split_items = self._dataset_split_item_repository.list_by_dataset_release_id(dataset_release_id)
        # DatasetItemRepositoryPort only exposes list-by-snapshot, not
        # get-by-id — fetching the snapshot's full item list once and
        # indexing it here avoids an N+1 lookup and avoids widening the
        # port's contract just for this export.
        dataset_items_by_id = {
            item.id: item
            for item in self._dataset_item_repository.list_by_dataset_snapshot_id(release.dataset_snapshot_id)
        }

        pairs = []
        for split_item in split_items:
            dataset_item = dataset_items_by_id.get(split_item.dataset_item_id)
            if dataset_item is not None:
                pairs.append((split_item, dataset_item))
        pairs.sort(key=lambda pair: (pair[0].split.value, str(pair[1].analysis_run_id), str(pair[0].id)))

        manifest_items: list[dict[str, Any]] = []
        for split_item, dataset_item in pairs:
            sample = self._sample_repository.get_by_id(dataset_item.sample_id)
            petri_image = self._petri_image_repository.get_by_id(dataset_item.petri_image_id)
            micro_image = self._micro_image_repository.get_by_id(dataset_item.micro_image_id)
            prediction = self._prediction_repository.get_by_id(dataset_item.prediction_id)
            if sample is None or petri_image is None or micro_image is None or prediction is None:
                continue

            manifest_items.append(
                {
                    "split": split_item.split.value,
                    "analysis_run_id": str(dataset_item.analysis_run_id),
                    "sample_code": sample.sample_code,
                    "petri_image_path": petri_image.file_path,
                    "micro_image_path": micro_image.file_path,
                    "ground_truth_label": (
                        split_item.ground_truth_label.value if split_item.ground_truth_label else None
                    ),
                    "source_review_decision": dataset_item.source_review_decision.value,
                    "prediction_label": prediction.predicted_label.value,
                    "final_review_id": str(dataset_item.final_review_id),
                }
            )

        return {
            "dataset_release_id": str(release.id),
            "dataset_snapshot_id": str(release.dataset_snapshot_id),
            "name": release.name,
            "version": release.version,
            "split_strategy": release.split_strategy,
            "random_seed": release.random_seed,
            "ratios": {
                "train": release.train_ratio,
                "validation": release.validation_ratio,
                "test": release.test_ratio,
            },
            "counts": {
                "total": release.item_count,
                "train": release.train_count,
                "validation": release.validation_count,
                "test": release.test_count,
            },
            "label_distribution": release.label_distribution or {},
            "split_distribution": release.split_distribution or {},
            "created_at": _iso(release.created_at),
            "items": manifest_items,
        }
