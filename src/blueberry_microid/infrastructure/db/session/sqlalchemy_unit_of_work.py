from types import TracebackType
from typing import Optional

from sqlalchemy.orm import Session, sessionmaker

from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_analysis_run_repository import (
    SqlAlchemyAnalysisRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_annotation_bundle_file_repository import (
    SqlAlchemyAnnotationBundleFileRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_annotation_bundle_run_repository import (
    SqlAlchemyAnnotationBundleRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_annotation_quality_gate_issue_repository import (
    SqlAlchemyAnnotationQualityGateIssueRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_annotation_quality_gate_run_repository import (
    SqlAlchemyAnnotationQualityGateRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_dataset_item_repository import (
    SqlAlchemyDatasetItemRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_dataset_curation_repository import (
    SqlAlchemyDatasetCurationItemRepository,
    SqlAlchemyDatasetCurationRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_dataset_release_repository import (
    SqlAlchemyDatasetReleaseRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_dataset_snapshot_repository import (
    SqlAlchemyDatasetSnapshotRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_dataset_split_item_repository import (
    SqlAlchemyDatasetSplitItemRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_detection_training_artifact_issue_repository import (
    SqlAlchemyDetectionTrainingArtifactIssueRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_detection_training_artifact_policy_repository import (
    SqlAlchemyDetectionTrainingArtifactPolicyRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_detection_training_artifact_record_repository import (
    SqlAlchemyDetectionTrainingArtifactRecordRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_detection_training_environment_issue_repository import (
    SqlAlchemyDetectionTrainingEnvironmentIssueRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_detection_training_environment_spec_repository import (
    SqlAlchemyDetectionTrainingEnvironmentSpecRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_detection_training_execution_issue_repository import (
    SqlAlchemyDetectionTrainingExecutionIssueRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_detection_training_execution_run_repository import (
    SqlAlchemyDetectionTrainingExecutionRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_detection_training_issue_repository import (
    SqlAlchemyDetectionTrainingIssueRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_detection_training_readiness_issue_repository import (
    SqlAlchemyDetectionTrainingReadinessIssueRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_detection_training_readiness_report_repository import (
    SqlAlchemyDetectionTrainingReadinessReportRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_detection_training_run_repository import (
    SqlAlchemyDetectionTrainingRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_human_review_repository import (
    SqlAlchemyHumanReviewRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_image_dataset_audit_issue_repository import (
    SqlAlchemyImageDatasetAuditIssueRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_image_dataset_audit_run_repository import (
    SqlAlchemyImageDatasetAuditRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_image_feature_extraction_run_repository import (
    SqlAlchemyImageFeatureExtractionRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_image_feature_vector_repository import (
    SqlAlchemyImageFeatureVectorRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_petri_region_review_repository import (
    SqlAlchemyPetriRegionReviewRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_model_evaluation_repository import (
    SqlAlchemyModelCandidateRepository,
    SqlAlchemyModelEvaluationIssueRepository,
    SqlAlchemyModelEvaluationRunRepository,
    SqlAlchemyModelPromotionGateRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_petri_annotation_export_item_repository import (
    SqlAlchemyPetriAnnotationExportItemRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_petri_annotation_export_run_repository import (
    SqlAlchemyPetriAnnotationExportRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_petri_segmentation_region_repository import (
    SqlAlchemyPetriSegmentationRegionRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_petri_segmentation_run_repository import (
    SqlAlchemyPetriSegmentationRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_prediction_repository import (
    SqlAlchemyPredictionRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_training_preflight_issue_repository import (
    SqlAlchemyTrainingPreflightIssueRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_training_preflight_run_repository import (
    SqlAlchemyTrainingPreflightRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_training_prediction_repository import (
    SqlAlchemyTrainingPredictionRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_training_run_comparison_entry_repository import (
    SqlAlchemyTrainingRunComparisonEntryRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_training_run_comparison_repository import (
    SqlAlchemyTrainingRunComparisonRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_training_run_repository import (
    SqlAlchemyTrainingRunRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWorkPort):
    """Wraps one SQLAlchemy Session as a single commit/rollback boundary.

    Usage::

        uow = SqlAlchemyUnitOfWork(session_factory)
        with uow:
            uow.prediction_repository.add(prediction)
            uow.analysis_run_repository.update(analysis_run)
            uow.commit()
        # falling out of the `with` block without an explicit commit(), or
        # raising inside it, rolls back everything.

    `analysis_run_repository`/`prediction_repository` are constructed with
    `auto_commit=False` — they only `flush()` on writes, so their changes
    become visible to this transaction (constraint violations still raise
    immediately) without being made durable until `commit()` is called here.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self.session: Optional[Session] = None

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = self._session_factory()
        self.analysis_run_repository = SqlAlchemyAnalysisRunRepository(self.session, auto_commit=False)
        self.annotation_bundle_file_repository = SqlAlchemyAnnotationBundleFileRepository(self.session, auto_commit=False)
        self.annotation_bundle_run_repository = SqlAlchemyAnnotationBundleRunRepository(self.session, auto_commit=False)
        self.annotation_quality_gate_issue_repository = SqlAlchemyAnnotationQualityGateIssueRepository(
            self.session, auto_commit=False
        )
        self.annotation_quality_gate_run_repository = SqlAlchemyAnnotationQualityGateRunRepository(
            self.session, auto_commit=False
        )
        self.dataset_item_repository = SqlAlchemyDatasetItemRepository(self.session, auto_commit=False)
        self.dataset_curation_item_repository = SqlAlchemyDatasetCurationItemRepository(
            self.session, auto_commit=False
        )
        self.dataset_curation_run_repository = SqlAlchemyDatasetCurationRunRepository(
            self.session, auto_commit=False
        )
        self.dataset_release_repository = SqlAlchemyDatasetReleaseRepository(self.session, auto_commit=False)
        self.dataset_snapshot_repository = SqlAlchemyDatasetSnapshotRepository(self.session, auto_commit=False)
        self.dataset_split_item_repository = SqlAlchemyDatasetSplitItemRepository(self.session, auto_commit=False)
        self.detection_training_issue_repository = SqlAlchemyDetectionTrainingIssueRepository(
            self.session, auto_commit=False
        )
        self.detection_training_run_repository = SqlAlchemyDetectionTrainingRunRepository(
            self.session, auto_commit=False
        )
        self.detection_training_readiness_issue_repository = SqlAlchemyDetectionTrainingReadinessIssueRepository(
            self.session, auto_commit=False
        )
        self.detection_training_readiness_report_repository = SqlAlchemyDetectionTrainingReadinessReportRepository(
            self.session, auto_commit=False
        )
        self.detection_training_environment_issue_repository = SqlAlchemyDetectionTrainingEnvironmentIssueRepository(
            self.session, auto_commit=False
        )
        self.detection_training_environment_spec_repository = SqlAlchemyDetectionTrainingEnvironmentSpecRepository(
            self.session, auto_commit=False
        )
        self.detection_training_artifact_policy_repository = SqlAlchemyDetectionTrainingArtifactPolicyRepository(
            self.session, auto_commit=False
        )
        self.detection_training_artifact_record_repository = SqlAlchemyDetectionTrainingArtifactRecordRepository(
            self.session, auto_commit=False
        )
        self.detection_training_artifact_issue_repository = SqlAlchemyDetectionTrainingArtifactIssueRepository(
            self.session, auto_commit=False
        )
        self.detection_training_execution_run_repository = SqlAlchemyDetectionTrainingExecutionRunRepository(
            self.session, auto_commit=False
        )
        self.detection_training_execution_issue_repository = SqlAlchemyDetectionTrainingExecutionIssueRepository(
            self.session, auto_commit=False
        )
        self.human_review_repository = SqlAlchemyHumanReviewRepository(self.session, auto_commit=False)
        self.image_dataset_audit_issue_repository = SqlAlchemyImageDatasetAuditIssueRepository(
            self.session, auto_commit=False
        )
        self.image_dataset_audit_run_repository = SqlAlchemyImageDatasetAuditRunRepository(
            self.session, auto_commit=False
        )
        self.image_feature_extraction_run_repository = SqlAlchemyImageFeatureExtractionRunRepository(
            self.session, auto_commit=False
        )
        self.image_feature_vector_repository = SqlAlchemyImageFeatureVectorRepository(
            self.session, auto_commit=False
        )
        self.model_candidate_repository = SqlAlchemyModelCandidateRepository(self.session, auto_commit=False)
        self.model_evaluation_issue_repository = SqlAlchemyModelEvaluationIssueRepository(
            self.session, auto_commit=False
        )
        self.model_evaluation_run_repository = SqlAlchemyModelEvaluationRunRepository(
            self.session, auto_commit=False
        )
        self.model_promotion_gate_run_repository = SqlAlchemyModelPromotionGateRunRepository(
            self.session, auto_commit=False
        )
        self.petri_annotation_export_item_repository = SqlAlchemyPetriAnnotationExportItemRepository(
            self.session, auto_commit=False
        )
        self.petri_annotation_export_run_repository = SqlAlchemyPetriAnnotationExportRunRepository(
            self.session, auto_commit=False
        )
        self.petri_region_review_repository = SqlAlchemyPetriRegionReviewRepository(
            self.session, auto_commit=False
        )
        self.petri_segmentation_region_repository = SqlAlchemyPetriSegmentationRegionRepository(
            self.session, auto_commit=False
        )
        self.petri_segmentation_run_repository = SqlAlchemyPetriSegmentationRunRepository(
            self.session, auto_commit=False
        )
        self.prediction_repository = SqlAlchemyPredictionRepository(self.session, auto_commit=False)
        self.training_preflight_issue_repository = SqlAlchemyTrainingPreflightIssueRepository(
            self.session, auto_commit=False
        )
        self.training_preflight_run_repository = SqlAlchemyTrainingPreflightRunRepository(
            self.session, auto_commit=False
        )
        self.training_prediction_repository = SqlAlchemyTrainingPredictionRepository(self.session, auto_commit=False)
        self.training_run_comparison_entry_repository = SqlAlchemyTrainingRunComparisonEntryRepository(
            self.session, auto_commit=False
        )
        self.training_run_comparison_repository = SqlAlchemyTrainingRunComparisonRepository(
            self.session, auto_commit=False
        )
        self.training_run_repository = SqlAlchemyTrainingRunRepository(self.session, auto_commit=False)
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        assert self.session is not None
        try:
            # Roll back anything not already committed, whether or not an
            # exception occurred. If the caller already called commit()
            # explicitly inside the `with` block, this is a no-op.
            self.rollback()
        finally:
            self.session.close()
            self.session = None

    def commit(self) -> None:
        assert self.session is not None
        self.session.commit()

    def rollback(self) -> None:
        assert self.session is not None
        self.session.rollback()
