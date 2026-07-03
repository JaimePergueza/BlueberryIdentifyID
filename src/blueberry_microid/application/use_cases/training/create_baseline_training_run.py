from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from blueberry_microid.application.dto.training_run_dto import (
    CreateBaselineTrainingRunRequest,
    TrainingRunDTO,
    training_config_to_dict,
)
from blueberry_microid.application.exceptions import BaselineTrainingNotAllowedError, DatasetReleaseNotFoundError
from blueberry_microid.application.ports.dataset_item_repository import DatasetItemRepositoryPort
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.application.ports.dataset_split_item_repository import DatasetSplitItemRepositoryPort
from blueberry_microid.application.ports.training_preflight_run_repository import TrainingPreflightRunRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.dataset_release_manifest_exporter import DatasetReleaseManifestExporter
from blueberry_microid.domain.entities.training_prediction import TrainingPrediction
from blueberry_microid.domain.entities.training_run import TrainingRun
from blueberry_microid.domain.enums.baseline_model_type import BaselineModelType
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.training_preflight_status import TrainingPreflightStatus
from blueberry_microid.domain.enums.training_run_kind import TrainingRunKind
from blueberry_microid.domain.enums.training_run_status import TrainingRunStatus
from blueberry_microid.ml.contracts.training_manifest import TrainingManifest
from blueberry_microid.ml.training.majority_class_baseline import BaselineTrainingItem, MajorityClassBaselineTrainer
from blueberry_microid.ml.validation.manifest_validator import ManifestValidator


class CreateBaselineTrainingRunUseCase:
    def __init__(
        self,
        dataset_release_repository: DatasetReleaseRepositoryPort,
        preflight_run_repository: TrainingPreflightRunRepositoryPort,
        dataset_split_item_repository: DatasetSplitItemRepositoryPort,
        dataset_item_repository: DatasetItemRepositoryPort,
        manifest_exporter: DatasetReleaseManifestExporter,
        manifest_validator: ManifestValidator,
        trainer: MajorityClassBaselineTrainer,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._dataset_release_repository = dataset_release_repository
        self._preflight_run_repository = preflight_run_repository
        self._dataset_split_item_repository = dataset_split_item_repository
        self._dataset_item_repository = dataset_item_repository
        self._manifest_exporter = manifest_exporter
        self._manifest_validator = manifest_validator
        self._trainer = trainer
        self._unit_of_work = unit_of_work

    def execute(self, request: CreateBaselineTrainingRunRequest) -> TrainingRunDTO:
        if request.baseline_model_type != BaselineModelType.MAJORITY_CLASS:
            raise BaselineTrainingNotAllowedError("only majority_class baseline is available")
        release = self._dataset_release_repository.get_by_id(request.dataset_release_id)
        if release is None:
            raise DatasetReleaseNotFoundError(f"dataset_release '{request.dataset_release_id}' does not exist")
        preflight = self._preflight_run_repository.get_by_id(request.preflight_run_id)
        if preflight is None:
            raise BaselineTrainingNotAllowedError(f"preflight_run '{request.preflight_run_id}' does not exist")
        if preflight.dataset_release_id != request.dataset_release_id:
            raise BaselineTrainingNotAllowedError("preflight_run does not belong to dataset_release")
        if preflight.status == TrainingPreflightStatus.FAILED:
            raise BaselineTrainingNotAllowedError("cannot run baseline from a failed preflight")

        manifest = TrainingManifest.from_dict(self._manifest_exporter.export(request.dataset_release_id))
        report = self._manifest_validator.validate(manifest, request.training_config)
        started_at = datetime.now(timezone.utc)
        config = training_config_to_dict(request.training_config)
        if not report.is_valid:
            failed_run = TrainingRun(
                dataset_release_id=request.dataset_release_id,
                preflight_run_id=request.preflight_run_id,
                run_kind=TrainingRunKind.BASELINE,
                baseline_model_type=BaselineModelType.MAJORITY_CLASS,
                status=TrainingRunStatus.FAILED,
                experiment_name=request.experiment_name,
                config=config,
                baseline_state={},
                metrics={},
                summary={"validation_errors": report.errors, "contains_deep_learning": False},
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                created_by=request.created_by,
                notes=request.notes,
                error_message="manifest validation failed before baseline execution",
            )
            with self._unit_of_work as uow:
                created = uow.training_run_repository.add(failed_run)
                uow.commit()
            return TrainingRunDTO.from_entity(created)

        training_items = self._build_training_items(release.dataset_snapshot_id, request.dataset_release_id)
        result = self._trainer.fit_predict(training_items)
        run = TrainingRun(
            dataset_release_id=request.dataset_release_id,
            preflight_run_id=request.preflight_run_id,
            run_kind=TrainingRunKind.BASELINE,
            baseline_model_type=BaselineModelType.MAJORITY_CLASS,
            status=TrainingRunStatus.COMPLETED,
            experiment_name=request.experiment_name,
            config=config,
            baseline_state=result.baseline_state,
            metrics=result.metrics,
            summary=result.summary,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            created_by=request.created_by,
            notes=request.notes,
        )
        predictions = [
            TrainingPrediction(
                training_run_id=run.id,
                dataset_split_item_id=prediction.dataset_split_item_id,
                dataset_item_id=prediction.dataset_item_id,
                split=prediction.split,
                ground_truth_label=prediction.ground_truth_label,
                predicted_label=prediction.predicted_label,
                is_correct=prediction.is_correct,
            )
            for prediction in result.predictions
        ]
        with self._unit_of_work as uow:
            created = uow.training_run_repository.add(run)
            uow.training_prediction_repository.add_many(predictions)
            uow.commit()
        return TrainingRunDTO.from_entity(created)

    def _build_training_items(self, dataset_snapshot_id: UUID, dataset_release_id: UUID) -> list[BaselineTrainingItem]:
        dataset_items_by_id = {
            item.id: item for item in self._dataset_item_repository.list_by_dataset_snapshot_id(dataset_snapshot_id)
        }
        training_items = []
        for split_item in self._dataset_split_item_repository.list_by_dataset_release_id(dataset_release_id):
            dataset_item = dataset_items_by_id[split_item.dataset_item_id]
            if split_item.ground_truth_label is None:
                raise BaselineTrainingNotAllowedError("dataset split item has no ground_truth_label")
            training_items.append(
                BaselineTrainingItem(
                    dataset_split_item_id=split_item.id,
                    dataset_item_id=dataset_item.id,
                    split=split_item.split,
                    ground_truth_label=PredictedLabel(split_item.ground_truth_label.value),
                )
            )
        return training_items
