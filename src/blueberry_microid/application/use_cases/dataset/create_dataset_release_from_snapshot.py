from __future__ import annotations

from blueberry_microid.application.dto.dataset_dto import (
    CreateDatasetReleaseFromSnapshotRequest,
    DatasetReleaseDTO,
)
from blueberry_microid.application.exceptions import (
    DatasetSnapshotNotFoundError,
    DuplicateDatasetReleaseError,
    EmptyDatasetSnapshotError,
)
from blueberry_microid.application.ports.dataset_item_repository import DatasetItemRepositoryPort
from blueberry_microid.application.ports.dataset_snapshot_repository import DatasetSnapshotRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.dataset_release_from_snapshot_evaluator import (
    DatasetReleaseFromSnapshotEvaluator,
)
from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.domain.entities.dataset_release import DatasetRelease
from blueberry_microid.domain.entities.dataset_snapshot import DatasetSnapshot
from blueberry_microid.domain.enums.dataset_release_kind import DatasetReleaseKind


class CreateDatasetReleaseFromSnapshotUseCase:
    """Create a metadata-only release from a curated DatasetSnapshot."""

    def __init__(
        self,
        dataset_snapshot_repository: DatasetSnapshotRepositoryPort,
        dataset_item_repository: DatasetItemRepositoryPort,
        dataset_release_from_snapshot_evaluator: DatasetReleaseFromSnapshotEvaluator,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._dataset_snapshot_repository = dataset_snapshot_repository
        self._dataset_item_repository = dataset_item_repository
        self._dataset_release_from_snapshot_evaluator = dataset_release_from_snapshot_evaluator
        self._unit_of_work = unit_of_work

    def execute(self, request: CreateDatasetReleaseFromSnapshotRequest) -> DatasetReleaseDTO:
        snapshot = self._dataset_snapshot_repository.get_by_id(request.dataset_snapshot_id)
        if snapshot is None:
            raise DatasetSnapshotNotFoundError(
                f"dataset_snapshot '{request.dataset_snapshot_id}' does not exist"
            )

        items = self._dataset_item_repository.list_by_dataset_snapshot_id(request.dataset_snapshot_id)
        evaluation = self._dataset_release_from_snapshot_evaluator.evaluate(
            snapshot,
            items,
            include_inconclusive=request.include_inconclusive,
        )
        if not evaluation.eligible_items and not request.allow_empty_release:
            raise EmptyDatasetSnapshotError(
                f"dataset_snapshot '{request.dataset_snapshot_id}' has no eligible items to release"
            )

        manifest = self._build_manifest(snapshot, request, evaluation.eligible_items)
        release = DatasetRelease(
            dataset_snapshot_id=request.dataset_snapshot_id,
            name=request.name,
            version=request.version,
            release_kind=DatasetReleaseKind.SNAPSHOT_RELEASE,
            status="completed",
            description=request.description,
            item_count=len(evaluation.eligible_items),
            train_count=0,
            validation_count=0,
            test_count=0,
            label_distribution=evaluation.label_distribution,
            split_distribution=None,
            manifest=manifest,
            provenance={
                "source": "dataset_snapshot",
                "dataset_snapshot_id": str(snapshot.id),
                "eligible_item_count": len(evaluation.eligible_items),
                "skipped_item_count": len(evaluation.skipped_items),
                "warnings": evaluation.warnings,
                "split_oriented": False,
            },
            created_by=request.created_by,
            notes=request.notes,
        )
        release.manifest["dataset_release_id"] = str(release.id)

        with self._unit_of_work as uow:
            existing_releases = uow.dataset_release_repository.list_by_dataset_snapshot_id(
                request.dataset_snapshot_id
            )
            for existing_release in existing_releases:
                if existing_release.name == request.name and existing_release.version == request.version:
                    raise DuplicateDatasetReleaseError(
                        "dataset release name/version already exists for this dataset snapshot"
                    )
            created_release = uow.dataset_release_repository.add(release)
            uow.commit()

        return DatasetReleaseDTO.from_entity(created_release)

    def _build_manifest(
        self,
        snapshot: DatasetSnapshot,
        request: CreateDatasetReleaseFromSnapshotRequest,
        items: list[DatasetItem],
    ) -> dict:
        return {
            "dataset_release_id": None,
            "dataset_snapshot_id": str(snapshot.id),
            "name": request.name,
            "version": request.version,
            "release_kind": DatasetReleaseKind.SNAPSHOT_RELEASE.value,
            "item_count": len(items),
            "label_distribution": self._label_distribution(items),
            "items": [self._manifest_item(item) for item in sorted(items, key=lambda item: str(item.id))],
        }

    def _label_distribution(self, items: list[DatasetItem]) -> dict[str, int]:
        distribution: dict[str, int] = {}
        for item in items:
            if item.ground_truth_label is None:
                continue
            label = item.ground_truth_label.value
            distribution[label] = distribution.get(label, 0) + 1
        return dict(sorted(distribution.items()))

    def _manifest_item(self, item: DatasetItem) -> dict:
        return {
            "dataset_item_id": str(item.id),
            "sample_id": str(item.sample_id),
            "analysis_run_id": str(item.analysis_run_id),
            "petri_image_id": str(item.petri_image_id),
            "micro_image_id": str(item.micro_image_id),
            "prediction_id": str(item.prediction_id),
            "final_review_id": str(item.final_review_id),
            "ground_truth_label": item.ground_truth_label.value if item.ground_truth_label else None,
            "source_review_decision": item.source_review_decision.value,
            "curation_run_id": str(item.curation_run_id) if item.curation_run_id else None,
            "curation_item_id": str(item.curation_item_id) if item.curation_item_id else None,
            "provenance": item.provenance,
        }
