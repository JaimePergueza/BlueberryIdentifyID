from __future__ import annotations

from collections import Counter

from blueberry_microid.application.dto.dataset_dto import (
    CreateDatasetSnapshotRequest,
    DatasetSnapshotDTO,
)
from blueberry_microid.application.ports.analysis_run_repository import AnalysisRunRepositoryPort
from blueberry_microid.application.ports.human_review_repository import HumanReviewRepositoryPort
from blueberry_microid.application.ports.micro_image_repository import MicroImageRepositoryPort
from blueberry_microid.application.ports.petri_image_repository import PetriImageRepositoryPort
from blueberry_microid.application.ports.prediction_repository import PredictionRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.dataset_ground_truth import derive_ground_truth_label
from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.domain.entities.dataset_snapshot import DatasetSnapshot
from blueberry_microid.domain.enums.analysis_status import AnalysisStatus


class CreateDatasetSnapshotUseCase:
    """Create a frozen curated dataset snapshot from final human reviews."""

    def __init__(
        self,
        analysis_run_repository: AnalysisRunRepositoryPort,
        prediction_repository: PredictionRepositoryPort,
        human_review_repository: HumanReviewRepositoryPort,
        petri_image_repository: PetriImageRepositoryPort,
        micro_image_repository: MicroImageRepositoryPort,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._analysis_run_repository = analysis_run_repository
        self._prediction_repository = prediction_repository
        self._human_review_repository = human_review_repository
        self._petri_image_repository = petri_image_repository
        self._micro_image_repository = micro_image_repository
        self._unit_of_work = unit_of_work

    def execute(self, request: CreateDatasetSnapshotRequest) -> DatasetSnapshotDTO:
        criteria = {
            "requires_prediction": True,
            "requires_final_human_review": True,
            "requires_petri_image": True,
            "requires_micro_image": True,
            "excluded_statuses": [AnalysisStatus.PENDING.value, AnalysisStatus.PROCESSING.value],
            "include_inconclusive": request.include_inconclusive,
            "include_rejected": request.include_rejected,
            "ground_truth_source": "final_human_review",
        }

        candidates = self._analysis_run_repository.list_all()
        included_items: list[DatasetItem] = []
        exclusion_items: list[DatasetItem] = []

        snapshot = DatasetSnapshot(
            name=request.name,
            version=request.version,
            description=request.description,
            created_by=request.created_by,
            selection_criteria=criteria,
            notes=request.notes,
        )

        for analysis_run in candidates:
            if analysis_run.status in {AnalysisStatus.PENDING, AnalysisStatus.PROCESSING}:
                continue

            prediction = self._prediction_repository.get_by_analysis_run_id(analysis_run.id)
            if prediction is None:
                continue

            final_review = self._human_review_repository.get_final_by_analysis_run_id(analysis_run.id)
            if final_review is None:
                continue

            petri_image = self._petri_image_repository.get_by_id(analysis_run.petri_image_id)
            micro_image = self._micro_image_repository.get_by_id(analysis_run.micro_image_id)
            if petri_image is None or micro_image is None:
                continue

            decision = derive_ground_truth_label(
                prediction=prediction,
                final_review=final_review,
                include_inconclusive=request.include_inconclusive,
                include_rejected=request.include_rejected,
            )
            item = DatasetItem(
                dataset_snapshot_id=snapshot.id,
                analysis_run_id=analysis_run.id,
                sample_id=analysis_run.sample_id,
                petri_image_id=analysis_run.petri_image_id,
                micro_image_id=analysis_run.micro_image_id,
                prediction_id=prediction.id,
                final_review_id=final_review.id,
                ground_truth_label=decision.ground_truth_label,
                source_review_decision=final_review.review_decision,
                included=decision.included,
                exclusion_reason=decision.exclusion_reason,
            )
            if item.included:
                included_items.append(item)
            elif request.include_rejected and item.exclusion_reason == "rejected_invalid_sample":
                exclusion_items.append(item)

        label_distribution = Counter(item.ground_truth_label.value for item in included_items if item.ground_truth_label)
        snapshot = DatasetSnapshot(
            id=snapshot.id,
            name=snapshot.name,
            version=snapshot.version,
            description=snapshot.description,
            created_at=snapshot.created_at,
            created_by=snapshot.created_by,
            selection_criteria=snapshot.selection_criteria,
            item_count=len(included_items),
            label_distribution=dict(sorted(label_distribution.items())),
            notes=snapshot.notes,
        )

        with self._unit_of_work as uow:
            created = uow.dataset_snapshot_repository.add(snapshot)
            uow.dataset_item_repository.add_many(included_items + exclusion_items)
            uow.commit()

        return DatasetSnapshotDTO.from_entity(created)

