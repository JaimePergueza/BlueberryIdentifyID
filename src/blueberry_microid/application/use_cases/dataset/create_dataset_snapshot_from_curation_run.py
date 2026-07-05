from __future__ import annotations

from uuid import UUID

from blueberry_microid.application.dto.dataset_curation_dto import (
    SnapshotCurationItemMappingDTO,
    SnapshotFromCurationPolicy,
    SnapshotFromCurationRunRequestDTO,
    SnapshotFromCurationRunResultDTO,
)
from blueberry_microid.application.exceptions import (
    DatasetCurationRunNotFoundError,
    DatasetSnapshotFromCurationNotAllowedError,
)
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.snapshot_from_curation_evaluator import (
    SnapshotFromCurationRunEvaluator,
)
from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.domain.entities.dataset_snapshot import DatasetSnapshot
from blueberry_microid.domain.enums.predicted_label import PredictedLabel


class CreateDatasetSnapshotFromCurationRunUseCase:
    """Create an explicit DatasetSnapshot from included DatasetCurationItems."""

    def __init__(
        self,
        evaluator: SnapshotFromCurationRunEvaluator,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._evaluator = evaluator
        self._unit_of_work = unit_of_work

    def execute(self, request: SnapshotFromCurationRunRequestDTO) -> SnapshotFromCurationRunResultDTO:
        with self._unit_of_work as uow:
            curation_run = uow.dataset_curation_run_repository.get_by_id(request.curation_run_id)
            if curation_run is None:
                raise DatasetCurationRunNotFoundError(
                    f"dataset curation run '{request.curation_run_id}' was not found"
                )
            if curation_run.created_snapshot_id is not None:
                raise DatasetSnapshotFromCurationNotAllowedError(
                    "dataset curation run already has a created snapshot"
                )

            curation_items = uow.dataset_curation_item_repository.list_by_curation_run_id(
                request.curation_run_id
            )
            policy = SnapshotFromCurationPolicy(
                include_inconclusive=request.include_inconclusive,
                allow_empty_snapshot=request.allow_empty_snapshot,
            )
            evaluation = self._evaluator.evaluate(
                curation_run=curation_run,
                curation_items=curation_items,
                policy=policy,
            )
            if not evaluation.included_items_for_snapshot and not request.allow_empty_snapshot:
                raise DatasetSnapshotFromCurationNotAllowedError(
                    "dataset curation run has no included items eligible for snapshot creation"
                )

            snapshot = DatasetSnapshot(
                name=request.snapshot_name or f"curation-{request.curation_run_id}",
                version="v1",
                description=request.snapshot_description,
                created_by=request.created_by,
                selection_criteria={
                    "source": "human_reviewed_curation_run",
                    "curation_run_id": str(request.curation_run_id),
                    "include_only_status": ["included"],
                    "include_inconclusive": request.include_inconclusive,
                    "allow_empty_snapshot": request.allow_empty_snapshot,
                    "allowed_labels": [label.value for label in PredictedLabel],
                },
                item_count=len(evaluation.included_items_for_snapshot),
                label_distribution=evaluation.labels_distribution,
                notes=request.notes,
            )
            dataset_items = [
                self._to_dataset_item(snapshot.id, request.curation_run_id, item)
                for item in evaluation.included_items_for_snapshot
            ]

            created_snapshot = uow.dataset_snapshot_repository.add(snapshot)
            created_items = uow.dataset_item_repository.add_many(dataset_items) if dataset_items else []
            uow.dataset_curation_run_repository.set_created_snapshot_id(
                request.curation_run_id, created_snapshot.id
            )
            uow.commit()

        mappings = [
            SnapshotCurationItemMappingDTO(
                dataset_item_id=item.id,
                curation_item_id=item.curation_item_id,  # type: ignore[arg-type]
                sample_id=item.sample_id,
                analysis_run_id=item.analysis_run_id,
                prediction_id=item.prediction_id,
                human_review_id=item.final_review_id,
                final_label=item.ground_truth_label,  # type: ignore[arg-type]
                review_decision=item.source_review_decision,
                status="included",
            )
            for item in created_items
            if item.curation_item_id is not None and item.ground_truth_label is not None
        ]
        return SnapshotFromCurationRunResultDTO(
            snapshot_id=created_snapshot.id,
            curation_run_id=request.curation_run_id,
            status="completed",
            snapshot_name=created_snapshot.name,
            total_curation_items=len(curation_items),
            included_items_scanned=len(evaluation.included_items_for_snapshot),
            dataset_items_created=len(created_items),
            excluded_items_ignored=len(evaluation.skipped_items),
            duplicate_items_skipped=evaluation.duplicate_items_skipped,
            labels_distribution=evaluation.labels_distribution,
            created_by=created_snapshot.created_by,
            created_at=created_snapshot.created_at,
            warnings=evaluation.warnings,
            provenance={
                "source": "human_reviewed_curation_run",
                "curation_run_id": str(request.curation_run_id),
            },
            mappings=mappings,
        )

    def _to_dataset_item(self, snapshot_id: UUID, curation_run_id: UUID, item) -> DatasetItem:
        provenance = {
            "source": "human_reviewed_curation_run",
            "curation_run_id": str(curation_run_id),
            "curation_item_id": str(item.id),
            "analysis_run_id": str(item.analysis_run_id),
            "prediction_id": str(item.prediction_id),
            "human_review_id": str(item.human_review_id),
            "review_decision": item.review_decision.value,
            "final_label": item.final_label.value,
            "prediction_is_ground_truth": False,
            "ground_truth_source": "final_human_review",
        }
        return DatasetItem(
            dataset_snapshot_id=snapshot_id,
            analysis_run_id=item.analysis_run_id,
            sample_id=item.sample_id,
            petri_image_id=item.petri_image_id,
            micro_image_id=item.micro_image_id,
            prediction_id=item.prediction_id,
            final_review_id=item.human_review_id,
            source_review_decision=item.review_decision,
            curation_run_id=curation_run_id,
            curation_item_id=item.id,
            ground_truth_label=item.final_label,
            included=True,
            provenance=provenance,
        )
