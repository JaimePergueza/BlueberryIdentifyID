from abc import ABC, abstractmethod
from types import TracebackType
from typing import Optional

from blueberry_microid.application.ports.analysis_run_repository import AnalysisRunRepositoryPort
from blueberry_microid.application.ports.annotation_bundle_file_repository import AnnotationBundleFileRepositoryPort
from blueberry_microid.application.ports.annotation_bundle_run_repository import AnnotationBundleRunRepositoryPort
from blueberry_microid.application.ports.annotation_quality_gate_issue_repository import (
    AnnotationQualityGateIssueRepositoryPort,
)
from blueberry_microid.application.ports.annotation_quality_gate_run_repository import (
    AnnotationQualityGateRunRepositoryPort,
)
from blueberry_microid.application.ports.dataset_item_repository import DatasetItemRepositoryPort
from blueberry_microid.application.ports.detection_training_environment_issue_repository import (
    DetectionTrainingEnvironmentIssueRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_environment_spec_repository import (
    DetectionTrainingEnvironmentSpecRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_issue_repository import (
    DetectionTrainingIssueRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_readiness_issue_repository import (
    DetectionTrainingReadinessIssueRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_readiness_report_repository import (
    DetectionTrainingReadinessReportRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_run_repository import DetectionTrainingRunRepositoryPort
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.application.ports.dataset_snapshot_repository import DatasetSnapshotRepositoryPort
from blueberry_microid.application.ports.dataset_split_item_repository import DatasetSplitItemRepositoryPort
from blueberry_microid.application.ports.human_review_repository import HumanReviewRepositoryPort
from blueberry_microid.application.ports.image_dataset_audit_issue_repository import (
    ImageDatasetAuditIssueRepositoryPort,
)
from blueberry_microid.application.ports.image_dataset_audit_run_repository import (
    ImageDatasetAuditRunRepositoryPort,
)
from blueberry_microid.application.ports.image_feature_extraction_run_repository import (
    ImageFeatureExtractionRunRepositoryPort,
)
from blueberry_microid.application.ports.image_feature_vector_repository import ImageFeatureVectorRepositoryPort
from blueberry_microid.application.ports.petri_region_review_repository import PetriRegionReviewRepositoryPort
from blueberry_microid.application.ports.petri_annotation_export_item_repository import (
    PetriAnnotationExportItemRepositoryPort,
)
from blueberry_microid.application.ports.petri_annotation_export_run_repository import (
    PetriAnnotationExportRunRepositoryPort,
)
from blueberry_microid.application.ports.petri_segmentation_region_repository import (
    PetriSegmentationRegionRepositoryPort,
)
from blueberry_microid.application.ports.petri_segmentation_run_repository import PetriSegmentationRunRepositoryPort
from blueberry_microid.application.ports.prediction_repository import PredictionRepositoryPort
from blueberry_microid.application.ports.training_preflight_issue_repository import TrainingPreflightIssueRepositoryPort
from blueberry_microid.application.ports.training_preflight_run_repository import TrainingPreflightRunRepositoryPort
from blueberry_microid.application.ports.training_prediction_repository import TrainingPredictionRepositoryPort
from blueberry_microid.application.ports.training_run_comparison_entry_repository import (
    TrainingRunComparisonEntryRepositoryPort,
)
from blueberry_microid.application.ports.training_run_comparison_repository import TrainingRunComparisonRepositoryPort
from blueberry_microid.application.ports.training_run_repository import TrainingRunRepositoryPort


class UnitOfWorkPort(ABC):
    """Application-level transaction boundary, independent of SQLAlchemy.

    First real consumer: `ProcessAnalysisRunUseCase` (Fase 4), which must
    create a `Prediction` and move its `AnalysisRun` to a final status
    (`completed`/`needs_review`) as a single atomic write — if either half
    fails, neither should persist. `analysis_run_repository` and
    `prediction_repository` are only valid for use inside a `with` block
    (populated by `__enter__`); they are bound to the transaction's own
    session and must not auto-commit individually — only `commit()` on this
    object should make their writes durable.

    Since Fase 5, `human_review_repository` is also exposed so a new final
    HumanReview can demote the previous final review and insert the new one
    in a single commit.
    """

    analysis_run_repository: AnalysisRunRepositoryPort
    annotation_bundle_file_repository: AnnotationBundleFileRepositoryPort
    annotation_bundle_run_repository: AnnotationBundleRunRepositoryPort
    annotation_quality_gate_issue_repository: AnnotationQualityGateIssueRepositoryPort
    annotation_quality_gate_run_repository: AnnotationQualityGateRunRepositoryPort
    dataset_item_repository: DatasetItemRepositoryPort
    dataset_release_repository: DatasetReleaseRepositoryPort
    dataset_snapshot_repository: DatasetSnapshotRepositoryPort
    dataset_split_item_repository: DatasetSplitItemRepositoryPort
    detection_training_environment_issue_repository: DetectionTrainingEnvironmentIssueRepositoryPort
    detection_training_environment_spec_repository: DetectionTrainingEnvironmentSpecRepositoryPort
    detection_training_issue_repository: DetectionTrainingIssueRepositoryPort
    detection_training_readiness_issue_repository: DetectionTrainingReadinessIssueRepositoryPort
    detection_training_readiness_report_repository: DetectionTrainingReadinessReportRepositoryPort
    detection_training_run_repository: DetectionTrainingRunRepositoryPort
    human_review_repository: HumanReviewRepositoryPort
    image_dataset_audit_issue_repository: ImageDatasetAuditIssueRepositoryPort
    image_dataset_audit_run_repository: ImageDatasetAuditRunRepositoryPort
    image_feature_extraction_run_repository: ImageFeatureExtractionRunRepositoryPort
    image_feature_vector_repository: ImageFeatureVectorRepositoryPort
    petri_annotation_export_item_repository: PetriAnnotationExportItemRepositoryPort
    petri_annotation_export_run_repository: PetriAnnotationExportRunRepositoryPort
    petri_region_review_repository: PetriRegionReviewRepositoryPort
    petri_segmentation_region_repository: PetriSegmentationRegionRepositoryPort
    petri_segmentation_run_repository: PetriSegmentationRunRepositoryPort
    prediction_repository: PredictionRepositoryPort
    training_preflight_issue_repository: TrainingPreflightIssueRepositoryPort
    training_preflight_run_repository: TrainingPreflightRunRepositoryPort
    training_prediction_repository: TrainingPredictionRepositoryPort
    training_run_comparison_entry_repository: TrainingRunComparisonEntryRepositoryPort
    training_run_comparison_repository: TrainingRunComparisonRepositoryPort
    training_run_repository: TrainingRunRepositoryPort

    @abstractmethod
    def __enter__(self) -> "UnitOfWorkPort":
        raise NotImplementedError

    @abstractmethod
    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError
