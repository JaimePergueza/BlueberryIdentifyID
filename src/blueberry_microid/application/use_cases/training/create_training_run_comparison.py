from __future__ import annotations

from blueberry_microid.application.dto.training_run_comparison_dto import (
    CreateTrainingRunComparisonRequest,
    TrainingRunComparisonDTO,
)
from blueberry_microid.application.exceptions import (
    DatasetReleaseNotFoundError,
    TrainingRunComparisonNotAllowedError,
)
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.application.ports.training_run_repository import TrainingRunRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.training_run_comparator import TrainingRunComparator
from blueberry_microid.domain.entities.training_run_comparison import TrainingRunComparison
from blueberry_microid.domain.entities.training_run_comparison_entry import TrainingRunComparisonEntry


class CreateTrainingRunComparisonUseCase:
    def __init__(
        self,
        dataset_release_repository: DatasetReleaseRepositoryPort,
        training_run_repository: TrainingRunRepositoryPort,
        comparator: TrainingRunComparator,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._dataset_release_repository = dataset_release_repository
        self._training_run_repository = training_run_repository
        self._comparator = comparator
        self._unit_of_work = unit_of_work

    def execute(self, request: CreateTrainingRunComparisonRequest) -> TrainingRunComparisonDTO:
        if len(request.training_run_ids) < 2:
            raise TrainingRunComparisonNotAllowedError("at least two training runs are required")
        if len(set(request.training_run_ids)) != len(request.training_run_ids):
            raise TrainingRunComparisonNotAllowedError("training_run_ids must be unique")
        release = self._dataset_release_repository.get_by_id(request.dataset_release_id)
        if release is None:
            raise DatasetReleaseNotFoundError(f"dataset_release '{request.dataset_release_id}' does not exist")

        training_runs = []
        for training_run_id in request.training_run_ids:
            run = self._training_run_repository.get_by_id(training_run_id)
            if run is None:
                raise TrainingRunComparisonNotAllowedError(f"training_run '{training_run_id}' does not exist")
            if run.dataset_release_id != request.dataset_release_id:
                raise TrainingRunComparisonNotAllowedError("training_run does not belong to dataset_release")
            training_runs.append(run)

        result = self._comparator.compare(
            training_runs,
            request.primary_metric,
            request.primary_split,
            request.selection_policy,
        )
        comparison = TrainingRunComparison(
            dataset_release_id=request.dataset_release_id,
            name=request.name,
            description=request.description,
            primary_metric=request.primary_metric,
            primary_split=request.primary_split,
            selection_policy=request.selection_policy,
            selected_training_run_id=result.selected_training_run_id,
            comparison_summary=result.summary,
            warnings=result.warnings,
            created_by=request.created_by,
            notes=request.notes,
        )
        entries = [
            TrainingRunComparisonEntry(
                comparison_id=comparison.id,
                training_run_id=entry.training_run_id,
                rank=entry.rank,
                run_kind=entry.run_kind,
                baseline_model_type=entry.baseline_model_type,
                primary_metric_value=entry.primary_metric_value,
                train_accuracy=entry.train_accuracy,
                validation_accuracy=entry.validation_accuracy,
                test_accuracy=entry.test_accuracy,
                generalization_gap=entry.generalization_gap,
                support_train=entry.support_train,
                support_validation=entry.support_validation,
                support_test=entry.support_test,
                metrics_snapshot=entry.metrics_snapshot,
                summary=entry.summary,
            )
            for entry in result.entries
        ]
        with self._unit_of_work as uow:
            created = uow.training_run_comparison_repository.add(comparison)
            created_entries = uow.training_run_comparison_entry_repository.add_many(entries)
            uow.commit()
        return TrainingRunComparisonDTO.from_entity(created, created_entries)
