from __future__ import annotations

from collections import Counter
from uuid import UUID

from blueberry_microid.application.dto.dataset_curation_dto import (
    CreateDatasetCurationRunRequest,
    DatasetCurationRunDTO,
)
from blueberry_microid.application.exceptions import (
    AnalysisRunNotFoundError,
    DatasetCurationNotAllowedError,
)
from blueberry_microid.application.ports.analysis_run_repository import AnalysisRunRepositoryPort
from blueberry_microid.application.ports.human_review_repository import HumanReviewRepositoryPort
from blueberry_microid.application.ports.micro_image_repository import MicroImageRepositoryPort
from blueberry_microid.application.ports.petri_image_repository import PetriImageRepositoryPort
from blueberry_microid.application.ports.prediction_repository import PredictionRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.dataset_curation_evaluator import DatasetCurationEvaluator
from blueberry_microid.domain.entities.dataset_curation_item import DatasetCurationItem
from blueberry_microid.domain.entities.dataset_curation_run import DatasetCurationRun
from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.domain.entities.dataset_snapshot import DatasetSnapshot
from blueberry_microid.domain.enums.dataset_curation_status import DatasetCurationStatus


class CreateDatasetCurationRunUseCase:
    def __init__(
        self,
        analysis_run_repository: AnalysisRunRepositoryPort,
        prediction_repository: PredictionRepositoryPort,
        human_review_repository: HumanReviewRepositoryPort,
        petri_image_repository: PetriImageRepositoryPort,
        micro_image_repository: MicroImageRepositoryPort,
        evaluator: DatasetCurationEvaluator,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._analysis_run_repository = analysis_run_repository
        self._prediction_repository = prediction_repository
        self._human_review_repository = human_review_repository
        self._petri_image_repository = petri_image_repository
        self._micro_image_repository = micro_image_repository
        self._evaluator = evaluator
        self._unit_of_work = unit_of_work

    def execute(self, request: CreateDatasetCurationRunRequest) -> DatasetCurationRunDTO:
        analysis_runs = self._load_candidate_runs(request)
        seen: set[UUID] = set()
        issues: list[dict] = []
        candidate_items: list[DatasetCurationItem] = []
        run_id = DatasetCurationRun().id

        for analysis_run in analysis_runs:
            if request.policy.prevent_duplicates and analysis_run.id in seen:
                issues.append({"code": "duplicate_analysis_run_id", "analysis_run_id": str(analysis_run.id)})
                continue
            seen.add(analysis_run.id)

            prediction = self._prediction_repository.get_by_analysis_run_id(analysis_run.id)
            final_review = self._human_review_repository.get_final_by_analysis_run_id(analysis_run.id)
            petri_image = self._petri_image_repository.get_by_id(analysis_run.petri_image_id)
            micro_image = self._micro_image_repository.get_by_id(analysis_run.micro_image_id)
            candidate = self._evaluator.evaluate(
                analysis_run=analysis_run,
                prediction=prediction,
                final_review=final_review,
                petri_image=petri_image,
                micro_image=micro_image,
                policy=request.policy,
            )
            candidate_items.append(
                DatasetCurationItem(
                    curation_run_id=run_id,
                    curation_status=candidate.curation_status,
                    sample_id=candidate.sample_id,
                    analysis_run_id=candidate.analysis_run_id,
                    prediction_id=candidate.prediction_id,
                    human_review_id=candidate.human_review_id,
                    petri_image_id=candidate.petri_image_id,
                    micro_image_id=candidate.micro_image_id,
                    automatic_label=candidate.automatic_label,
                    final_label=candidate.final_label,
                    review_decision=candidate.review_decision,
                    exclusion_reason=candidate.exclusion_reason,
                    provenance=candidate.provenance,
                    feature_summary=candidate.feature_summary,
                    quality_summary=candidate.quality_summary,
                )
            )

        included_items = [
            item for item in candidate_items if item.curation_status == DatasetCurationStatus.INCLUDED
        ]
        label_distribution = Counter(item.final_label.value for item in included_items if item.final_label is not None)

        snapshot = None
        snapshot_items: list[DatasetItem] = []
        if request.create_snapshot:
            snapshot = DatasetSnapshot(
                name=request.snapshot_name or f"curation-{run_id}",
                version=request.snapshot_version or "v1",
                description="Snapshot derived from a DatasetCurationRun.",
                created_by=request.created_by,
                selection_criteria={
                    "source": "dataset_curation_run",
                    "curation_run_id": str(run_id),
                    "policy": request.policy.to_dict(),
                },
                item_count=len(included_items),
                label_distribution=dict(sorted(label_distribution.items())),
                notes=request.notes,
            )
            snapshot_items = [
                DatasetItem(
                    dataset_snapshot_id=snapshot.id,
                    analysis_run_id=item.analysis_run_id,
                    sample_id=item.sample_id,
                    petri_image_id=item.petri_image_id,
                    micro_image_id=item.micro_image_id,
                    prediction_id=item.prediction_id,
                    final_review_id=item.human_review_id,
                    source_review_decision=item.review_decision,
                    ground_truth_label=item.final_label,
                    included=True,
                )
                for item in included_items
                if item.analysis_run_id
                and item.sample_id
                and item.petri_image_id
                and item.micro_image_id
                and item.prediction_id
                and item.human_review_id
                and item.review_decision
            ]

        curation_run = DatasetCurationRun(
            id=run_id,
            policy=request.policy.to_dict(),
            total_candidates_scanned=len(analysis_runs),
            included_count=len(included_items),
            excluded_count=len(candidate_items) - len(included_items),
            created_snapshot_id=snapshot.id if snapshot is not None else None,
            issues=issues or None,
            created_by=request.created_by,
            notes=request.notes,
        )

        with self._unit_of_work as uow:
            if snapshot is not None:
                uow.dataset_snapshot_repository.add(snapshot)
                if snapshot_items:
                    uow.dataset_item_repository.add_many(snapshot_items)
            saved_run = uow.dataset_curation_run_repository.add(curation_run)
            if candidate_items:
                uow.dataset_curation_item_repository.add_many(candidate_items)
            uow.commit()

        return DatasetCurationRunDTO.from_entity(saved_run)

    def _load_candidate_runs(self, request: CreateDatasetCurationRunRequest):
        if request.analysis_run_ids:
            runs = []
            for analysis_run_id in request.analysis_run_ids:
                analysis_run = self._analysis_run_repository.get_by_id(analysis_run_id)
                if analysis_run is None:
                    raise AnalysisRunNotFoundError(f"analysis_run '{analysis_run_id}' was not found")
                runs.append(analysis_run)
            return runs

        if not request.explicit_all_reviewed:
            raise DatasetCurationNotAllowedError(
                "analysis_run_ids are required unless explicit_all_reviewed=true"
            )

        return self._analysis_run_repository.list_all()

