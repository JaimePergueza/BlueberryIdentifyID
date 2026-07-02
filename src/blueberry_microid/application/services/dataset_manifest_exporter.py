from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from blueberry_microid.application.exceptions import DatasetSnapshotNotFoundError
from blueberry_microid.application.ports.dataset_item_repository import DatasetItemRepositoryPort
from blueberry_microid.application.ports.dataset_snapshot_repository import DatasetSnapshotRepositoryPort
from blueberry_microid.application.ports.micro_image_repository import MicroImageRepositoryPort
from blueberry_microid.application.ports.petri_image_repository import PetriImageRepositoryPort
from blueberry_microid.application.ports.prediction_repository import PredictionRepositoryPort
from blueberry_microid.application.ports.sample_repository import SampleRepositoryPort


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


class DatasetManifestExporter:
    """Build a deterministic manifest for a curated DatasetSnapshot."""

    def __init__(
        self,
        dataset_snapshot_repository: DatasetSnapshotRepositoryPort,
        dataset_item_repository: DatasetItemRepositoryPort,
        sample_repository: SampleRepositoryPort,
        petri_image_repository: PetriImageRepositoryPort,
        micro_image_repository: MicroImageRepositoryPort,
        prediction_repository: PredictionRepositoryPort,
    ) -> None:
        self._dataset_snapshot_repository = dataset_snapshot_repository
        self._dataset_item_repository = dataset_item_repository
        self._sample_repository = sample_repository
        self._petri_image_repository = petri_image_repository
        self._micro_image_repository = micro_image_repository
        self._prediction_repository = prediction_repository

    def export(self, dataset_snapshot_id: UUID) -> dict[str, Any]:
        snapshot = self._dataset_snapshot_repository.get_by_id(dataset_snapshot_id)
        if snapshot is None:
            raise DatasetSnapshotNotFoundError(f"dataset_snapshot '{dataset_snapshot_id}' does not exist")

        manifest_items: list[dict[str, Any]] = []
        items = self._dataset_item_repository.list_by_dataset_snapshot_id(dataset_snapshot_id)
        for item in sorted(items, key=lambda value: (str(value.analysis_run_id), str(value.id))):
            if not item.included:
                continue
            sample = self._sample_repository.get_by_id(item.sample_id)
            petri_image = self._petri_image_repository.get_by_id(item.petri_image_id)
            micro_image = self._micro_image_repository.get_by_id(item.micro_image_id)
            prediction = self._prediction_repository.get_by_id(item.prediction_id)
            if sample is None or petri_image is None or micro_image is None or prediction is None:
                continue

            manifest_items.append(
                {
                    "analysis_run_id": str(item.analysis_run_id),
                    "sample_code": sample.sample_code,
                    "petri_image_path": petri_image.file_path,
                    "micro_image_path": micro_image.file_path,
                    "ground_truth_label": item.ground_truth_label.value if item.ground_truth_label else None,
                    "source_review_decision": item.source_review_decision.value,
                    "prediction_label": prediction.predicted_label.value,
                    "final_review_id": str(item.final_review_id),
                    "petri_metadata": {
                        "file_name": petri_image.file_name,
                        "mime_type": petri_image.mime_type,
                        "file_size_bytes": petri_image.file_size_bytes,
                        "width": petri_image.width,
                        "height": petri_image.height,
                        "captured_at": _iso(petri_image.captured_at),
                        "culture_medium": petri_image.culture_medium,
                        "incubation_temperature_c": petri_image.incubation_temperature_c,
                        "incubation_time_hours": petri_image.incubation_time_hours,
                        "seeding_date": _iso(petri_image.seeding_date),
                        "observed_colony_color": petri_image.observed_colony_color,
                        "observed_colony_shape": petri_image.observed_colony_shape,
                        "observed_colony_margin": petri_image.observed_colony_margin,
                        "observed_colony_texture": petri_image.observed_colony_texture,
                    },
                    "micro_metadata": {
                        "file_name": micro_image.file_name,
                        "mime_type": micro_image.mime_type,
                        "file_size_bytes": micro_image.file_size_bytes,
                        "width": micro_image.width,
                        "height": micro_image.height,
                        "captured_at": _iso(micro_image.captured_at),
                        "magnification": micro_image.magnification,
                        "microscope_type": micro_image.microscope_type,
                        "staining_method": micro_image.staining_method,
                        "preparation_method": micro_image.preparation_method,
                        "observed_structures": micro_image.observed_structures,
                    },
                }
            )

        return {
            "dataset_snapshot_id": str(snapshot.id),
            "name": snapshot.name,
            "version": snapshot.version,
            "created_at": _iso(snapshot.created_at),
            "item_count": snapshot.item_count,
            "label_distribution": snapshot.label_distribution or {},
            "items": manifest_items,
        }

