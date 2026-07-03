from __future__ import annotations

from datetime import datetime, timezone

from blueberry_microid.application.dto.training_run_dto import (
    CreateClassicalBaselineTrainingRunRequest,
    TrainingRunDTO,
)
from blueberry_microid.application.exceptions import BaselineTrainingNotAllowedError, DatasetReleaseNotFoundError
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.application.ports.dataset_split_item_repository import DatasetSplitItemRepositoryPort
from blueberry_microid.application.ports.image_feature_extraction_run_repository import (
    ImageFeatureExtractionRunRepositoryPort,
)
from blueberry_microid.application.ports.image_feature_vector_repository import ImageFeatureVectorRepositoryPort
from blueberry_microid.application.ports.training_preflight_run_repository import TrainingPreflightRunRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.domain.entities.training_prediction import TrainingPrediction
from blueberry_microid.domain.entities.training_run import TrainingRun
from blueberry_microid.domain.enums.baseline_model_type import BaselineModelType
from blueberry_microid.domain.enums.image_feature_extraction_status import ImageFeatureExtractionStatus
from blueberry_microid.domain.enums.training_preflight_status import TrainingPreflightStatus
from blueberry_microid.domain.enums.training_run_kind import TrainingRunKind
from blueberry_microid.domain.enums.training_run_status import TrainingRunStatus
from blueberry_microid.ml.training.classical_tabular_baseline import ClassicalTabularBaselineTrainer
from blueberry_microid.ml.training.feature_matrix_builder import FeatureMatrixBuilder


class CreateClassicalBaselineTrainingRunUseCase:
    def __init__(
        self,
        dataset_release_repository: DatasetReleaseRepositoryPort,
        preflight_run_repository: TrainingPreflightRunRepositoryPort,
        image_feature_extraction_run_repository: ImageFeatureExtractionRunRepositoryPort,
        image_feature_vector_repository: ImageFeatureVectorRepositoryPort,
        dataset_split_item_repository: DatasetSplitItemRepositoryPort,
        feature_matrix_builder: FeatureMatrixBuilder,
        trainer: ClassicalTabularBaselineTrainer,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        self._dataset_release_repository = dataset_release_repository
        self._preflight_run_repository = preflight_run_repository
        self._image_feature_extraction_run_repository = image_feature_extraction_run_repository
        self._image_feature_vector_repository = image_feature_vector_repository
        self._dataset_split_item_repository = dataset_split_item_repository
        self._feature_matrix_builder = feature_matrix_builder
        self._trainer = trainer
        self._unit_of_work = unit_of_work

    def execute(self, request: CreateClassicalBaselineTrainingRunRequest) -> TrainingRunDTO:
        if request.tabular_training_config.model_type != BaselineModelType.LOGISTIC_REGRESSION_TABULAR:
            raise BaselineTrainingNotAllowedError("only logistic_regression_tabular classical baseline is available")
        if request.tabular_training_config.feature_extraction_run_id != request.image_feature_extraction_run_id:
            raise BaselineTrainingNotAllowedError("config feature_extraction_run_id does not match request")

        release = self._dataset_release_repository.get_by_id(request.dataset_release_id)
        if release is None:
            raise DatasetReleaseNotFoundError(f"dataset_release '{request.dataset_release_id}' does not exist")
        preflight = self._preflight_run_repository.get_by_id(request.preflight_run_id)
        if preflight is None:
            raise BaselineTrainingNotAllowedError(f"preflight_run '{request.preflight_run_id}' does not exist")
        if preflight.dataset_release_id != request.dataset_release_id:
            raise BaselineTrainingNotAllowedError("preflight_run does not belong to dataset_release")
        if preflight.status == TrainingPreflightStatus.FAILED:
            raise BaselineTrainingNotAllowedError("cannot run classical baseline from a failed preflight")

        extraction = self._image_feature_extraction_run_repository.get_by_id(request.image_feature_extraction_run_id)
        if extraction is None:
            raise BaselineTrainingNotAllowedError(
                f"image_feature_extraction_run '{request.image_feature_extraction_run_id}' does not exist"
            )
        if extraction.dataset_release_id != request.dataset_release_id:
            raise BaselineTrainingNotAllowedError("image_feature_extraction_run does not belong to dataset_release")
        if extraction.status != ImageFeatureExtractionStatus.COMPLETED:
            raise BaselineTrainingNotAllowedError("image_feature_extraction_run must be completed")

        feature_vectors = self._image_feature_vector_repository.list_by_feature_extraction_run_id(extraction.id)
        split_items = self._dataset_split_item_repository.list_by_dataset_release_id(request.dataset_release_id)
        started_at = datetime.now(timezone.utc)
        config = request.tabular_training_config.to_dict()

        try:
            matrix = self._feature_matrix_builder.build(feature_vectors, split_items, request.tabular_training_config)
            result = self._trainer.fit_predict(matrix, request.tabular_training_config)
        except ValueError as exc:
            failed_run = TrainingRun(
                dataset_release_id=request.dataset_release_id,
                preflight_run_id=request.preflight_run_id,
                run_kind=TrainingRunKind.BASELINE,
                baseline_model_type=BaselineModelType.LOGISTIC_REGRESSION_TABULAR,
                status=TrainingRunStatus.FAILED,
                experiment_name=request.experiment_name,
                config=config,
                baseline_state={
                    "feature_extraction_run_id": str(request.image_feature_extraction_run_id),
                    "model_type": BaselineModelType.LOGISTIC_REGRESSION_TABULAR.value,
                },
                metrics={},
                summary={"contains_deep_learning": False, "uses_image_pixels": False},
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                created_by=request.created_by,
                notes=request.notes,
                error_message=str(exc),
            )
            with self._unit_of_work as uow:
                created = uow.training_run_repository.add(failed_run)
                uow.commit()
            return TrainingRunDTO.from_entity(created)

        run = TrainingRun(
            dataset_release_id=request.dataset_release_id,
            preflight_run_id=request.preflight_run_id,
            run_kind=TrainingRunKind.BASELINE,
            baseline_model_type=BaselineModelType.LOGISTIC_REGRESSION_TABULAR,
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
