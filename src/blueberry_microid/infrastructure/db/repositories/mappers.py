"""ORM model -> domain entity mappers.

Kept separate from the repositories so the conversion logic is easy to spot
and reuse; repositories never hand a SQLAlchemy model back to the
application layer.
"""

from blueberry_microid.domain.entities.analysis_run import AnalysisRun
from blueberry_microid.domain.entities.dataset_item import DatasetItem
from blueberry_microid.domain.entities.dataset_release import DatasetRelease
from blueberry_microid.domain.entities.dataset_snapshot import DatasetSnapshot
from blueberry_microid.domain.entities.dataset_split_item import DatasetSplitItem
from blueberry_microid.domain.entities.human_review import HumanReview
from blueberry_microid.domain.entities.image_dataset_audit_issue import ImageDatasetAuditIssue
from blueberry_microid.domain.entities.image_dataset_audit_run import ImageDatasetAuditRun
from blueberry_microid.domain.entities.micro_image import MicroImage
from blueberry_microid.domain.entities.model_version import ModelVersion
from blueberry_microid.domain.entities.petri_image import PetriImage
from blueberry_microid.domain.entities.prediction import Prediction
from blueberry_microid.domain.entities.sample import Sample
from blueberry_microid.domain.entities.training_preflight_issue import TrainingPreflightIssue
from blueberry_microid.domain.entities.training_preflight_run import TrainingPreflightRun
from blueberry_microid.domain.entities.training_prediction import TrainingPrediction
from blueberry_microid.domain.entities.training_run import TrainingRun
from blueberry_microid.domain.enums.baseline_model_type import BaselineModelType
from blueberry_microid.domain.enums.dataset_split import DatasetSplit
from blueberry_microid.domain.enums.image_dataset_audit_issue_severity import ImageDatasetAuditIssueSeverity
from blueberry_microid.domain.enums.image_dataset_audit_status import ImageDatasetAuditStatus
from blueberry_microid.domain.enums.image_modality import ImageModality
from blueberry_microid.domain.enums.predicted_label import PredictedLabel
from blueberry_microid.domain.enums.split_strategy import SplitStrategy
from blueberry_microid.domain.enums.training_preflight_issue_severity import TrainingPreflightIssueSeverity
from blueberry_microid.domain.enums.training_preflight_status import TrainingPreflightStatus
from blueberry_microid.domain.enums.training_run_kind import TrainingRunKind
from blueberry_microid.domain.enums.training_run_status import TrainingRunStatus
from blueberry_microid.infrastructure.db.models.analysis_run import AnalysisRunModel
from blueberry_microid.infrastructure.db.models.dataset_item import DatasetItemModel
from blueberry_microid.infrastructure.db.models.dataset_release import DatasetReleaseModel
from blueberry_microid.infrastructure.db.models.dataset_snapshot import DatasetSnapshotModel
from blueberry_microid.infrastructure.db.models.dataset_split_item import DatasetSplitItemModel
from blueberry_microid.infrastructure.db.models.human_review import HumanReviewModel
from blueberry_microid.infrastructure.db.models.image_dataset_audit_issue import ImageDatasetAuditIssueModel
from blueberry_microid.infrastructure.db.models.image_dataset_audit_run import ImageDatasetAuditRunModel
from blueberry_microid.infrastructure.db.models.micro_image import MicroImageModel
from blueberry_microid.infrastructure.db.models.model_version import ModelVersionModel
from blueberry_microid.infrastructure.db.models.petri_image import PetriImageModel
from blueberry_microid.infrastructure.db.models.prediction import PredictionModel
from blueberry_microid.infrastructure.db.models.sample import SampleModel
from blueberry_microid.infrastructure.db.models.training_preflight_issue import TrainingPreflightIssueModel
from blueberry_microid.infrastructure.db.models.training_preflight_run import TrainingPreflightRunModel
from blueberry_microid.infrastructure.db.models.training_prediction import TrainingPredictionModel
from blueberry_microid.infrastructure.db.models.training_run import TrainingRunModel


def sample_to_entity(model: SampleModel) -> Sample:
    return Sample(
        sample_code=model.sample_code,
        id=model.id,
        product=model.product,
        lot_code=model.lot_code,
        origin=model.origin,
        collection_date=model.collection_date,
        notes=model.notes,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def petri_image_to_entity(model: PetriImageModel) -> PetriImage:
    return PetriImage(
        sample_id=model.sample_id,
        file_path=model.file_path,
        file_name=model.file_name,
        mime_type=model.mime_type,
        file_size_bytes=model.file_size_bytes,
        id=model.id,
        width=model.width,
        height=model.height,
        captured_at=model.captured_at,
        culture_medium=model.culture_medium,
        incubation_temperature_c=model.incubation_temperature_c,
        incubation_time_hours=model.incubation_time_hours,
        seeding_date=model.seeding_date,
        observed_colony_color=model.observed_colony_color,
        observed_colony_shape=model.observed_colony_shape,
        observed_colony_margin=model.observed_colony_margin,
        observed_colony_texture=model.observed_colony_texture,
        notes=model.notes,
        created_at=model.created_at,
    )


def micro_image_to_entity(model: MicroImageModel) -> MicroImage:
    return MicroImage(
        sample_id=model.sample_id,
        file_path=model.file_path,
        file_name=model.file_name,
        mime_type=model.mime_type,
        file_size_bytes=model.file_size_bytes,
        id=model.id,
        width=model.width,
        height=model.height,
        captured_at=model.captured_at,
        magnification=model.magnification,
        microscope_type=model.microscope_type,
        staining_method=model.staining_method,
        preparation_method=model.preparation_method,
        observed_structures=model.observed_structures,
        notes=model.notes,
        created_at=model.created_at,
    )


def model_version_to_entity(model: ModelVersionModel) -> ModelVersion:
    return ModelVersion(
        name=model.name,
        version=model.version,
        model_type=model.model_type,
        id=model.id,
        description=model.description,
        is_active=model.is_active,
        created_at=model.created_at,
    )


def analysis_run_to_entity(model: AnalysisRunModel) -> AnalysisRun:
    return AnalysisRun(
        sample_id=model.sample_id,
        petri_image_id=model.petri_image_id,
        micro_image_id=model.micro_image_id,
        model_version_id=model.model_version_id,
        id=model.id,
        status=model.status,
        created_at=model.created_at,
        started_at=model.started_at,
        completed_at=model.completed_at,
        error_message=model.error_message,
    )


def prediction_to_entity(model: PredictionModel) -> Prediction:
    return Prediction(
        analysis_run_id=model.analysis_run_id,
        predicted_label=model.predicted_label,
        id=model.id,
        confidence_score=model.confidence_score,
        class_probabilities=model.class_probabilities,
        technical_observation=model.technical_observation,
        requires_human_review=model.requires_human_review,
        created_at=model.created_at,
    )


def human_review_to_entity(model: HumanReviewModel) -> HumanReview:
    return HumanReview(
        analysis_run_id=model.analysis_run_id,
        reviewer_name=model.reviewer_name,
        review_decision=model.review_decision,
        id=model.id,
        corrected_label=model.corrected_label,
        comments=model.comments,
        is_final=model.is_final,
        created_at=model.created_at,
    )


def dataset_snapshot_to_entity(model: DatasetSnapshotModel) -> DatasetSnapshot:
    return DatasetSnapshot(
        name=model.name,
        version=model.version,
        id=model.id,
        description=model.description,
        created_at=model.created_at,
        created_by=model.created_by,
        selection_criteria=model.selection_criteria,
        item_count=model.item_count,
        label_distribution=model.label_distribution,
        notes=model.notes,
    )


def dataset_item_to_entity(model: DatasetItemModel) -> DatasetItem:
    return DatasetItem(
        dataset_snapshot_id=model.dataset_snapshot_id,
        analysis_run_id=model.analysis_run_id,
        sample_id=model.sample_id,
        petri_image_id=model.petri_image_id,
        micro_image_id=model.micro_image_id,
        prediction_id=model.prediction_id,
        final_review_id=model.final_review_id,
        source_review_decision=model.source_review_decision,
        id=model.id,
        ground_truth_label=model.ground_truth_label,
        included=model.included,
        exclusion_reason=model.exclusion_reason,
        created_at=model.created_at,
    )


def dataset_release_to_entity(model: DatasetReleaseModel) -> DatasetRelease:
    return DatasetRelease(
        dataset_snapshot_id=model.dataset_snapshot_id,
        name=model.name,
        version=model.version,
        split_strategy=SplitStrategy(model.split_strategy),
        random_seed=model.random_seed,
        train_ratio=model.train_ratio,
        validation_ratio=model.validation_ratio,
        test_ratio=model.test_ratio,
        id=model.id,
        item_count=model.item_count,
        train_count=model.train_count,
        validation_count=model.validation_count,
        test_count=model.test_count,
        label_distribution=model.label_distribution,
        split_distribution=model.split_distribution,
        created_at=model.created_at,
        created_by=model.created_by,
        notes=model.notes,
    )


def dataset_split_item_to_entity(model: DatasetSplitItemModel) -> DatasetSplitItem:
    return DatasetSplitItem(
        dataset_release_id=model.dataset_release_id,
        dataset_item_id=model.dataset_item_id,
        sample_id=model.sample_id,
        split=model.split,
        id=model.id,
        ground_truth_label=model.ground_truth_label,
        created_at=model.created_at,
    )


def training_preflight_run_to_entity(model: TrainingPreflightRunModel) -> TrainingPreflightRun:
    return TrainingPreflightRun(
        dataset_release_id=model.dataset_release_id,
        status=TrainingPreflightStatus(model.status),
        is_valid=model.is_valid,
        config=model.config,
        summary=model.summary,
        item_count=model.item_count,
        train_count=model.train_count,
        validation_count=model.validation_count,
        test_count=model.test_count,
        label_counts=model.label_counts,
        split_counts=model.split_counts,
        split_label_counts=model.split_label_counts,
        leakage_checks=model.leakage_checks,
        id=model.id,
        recommendation_summary=model.recommendation_summary,
        created_at=model.created_at,
        created_by=model.created_by,
        notes=model.notes,
    )


def training_preflight_issue_to_entity(model: TrainingPreflightIssueModel) -> TrainingPreflightIssue:
    return TrainingPreflightIssue(
        preflight_run_id=model.preflight_run_id,
        severity=TrainingPreflightIssueSeverity(model.severity),
        code=model.code,
        message=model.message,
        id=model.id,
        field=model.field,
        item_ref=model.item_ref,
        created_at=model.created_at,
    )


def training_run_to_entity(model: TrainingRunModel) -> TrainingRun:
    return TrainingRun(
        dataset_release_id=model.dataset_release_id,
        preflight_run_id=model.preflight_run_id,
        run_kind=TrainingRunKind(model.run_kind),
        baseline_model_type=BaselineModelType(model.baseline_model_type),
        status=TrainingRunStatus(model.status),
        experiment_name=model.experiment_name,
        config=model.config,
        baseline_state=model.baseline_state,
        metrics=model.metrics,
        summary=model.summary,
        started_at=model.started_at,
        id=model.id,
        completed_at=model.completed_at,
        created_at=model.created_at,
        created_by=model.created_by,
        notes=model.notes,
        error_message=model.error_message,
    )


def training_prediction_to_entity(model: TrainingPredictionModel) -> TrainingPrediction:
    return TrainingPrediction(
        training_run_id=model.training_run_id,
        dataset_split_item_id=model.dataset_split_item_id,
        dataset_item_id=model.dataset_item_id,
        split=DatasetSplit(model.split),
        ground_truth_label=PredictedLabel(model.ground_truth_label),
        predicted_label=PredictedLabel(model.predicted_label),
        is_correct=model.is_correct,
        id=model.id,
        created_at=model.created_at,
    )


def image_dataset_audit_run_to_entity(model: ImageDatasetAuditRunModel) -> ImageDatasetAuditRun:
    return ImageDatasetAuditRun(
        dataset_release_id=model.dataset_release_id,
        status=ImageDatasetAuditStatus(model.status),
        is_passed=model.is_passed,
        total_items=model.total_items,
        total_petri_images=model.total_petri_images,
        total_micro_images=model.total_micro_images,
        checked_petri_images=model.checked_petri_images,
        checked_micro_images=model.checked_micro_images,
        failed_petri_images=model.failed_petri_images,
        failed_micro_images=model.failed_micro_images,
        warning_count=model.warning_count,
        error_count=model.error_count,
        summary=model.summary,
        format_distribution=model.format_distribution,
        color_mode_distribution=model.color_mode_distribution,
        dimension_distribution=model.dimension_distribution,
        file_size_distribution=model.file_size_distribution,
        id=model.id,
        created_at=model.created_at,
        created_by=model.created_by,
        notes=model.notes,
    )


def image_dataset_audit_issue_to_entity(model: ImageDatasetAuditIssueModel) -> ImageDatasetAuditIssue:
    return ImageDatasetAuditIssue(
        audit_run_id=model.audit_run_id,
        severity=ImageDatasetAuditIssueSeverity(model.severity),
        modality=ImageModality(model.modality),
        code=model.code,
        message=model.message,
        id=model.id,
        dataset_item_id=model.dataset_item_id,
        dataset_split_item_id=model.dataset_split_item_id,
        image_path=model.image_path,
        details=model.details,
        created_at=model.created_at,
    )
