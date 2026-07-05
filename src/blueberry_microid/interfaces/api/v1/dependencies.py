"""Composition root for the API layer.

This module is the one sanctioned place where `interfaces/api` is allowed to
import SQLAlchemy repositories and filesystem/Pillow-backed infrastructure
directly (see CLAUDE.md, "Arquitectura obligatoria"): every dependency
below is built here and handed to a use case through its constructor. The
routers only ever import use case classes and these factory functions —
never a repository or storage class directly.

`application/` never imports FastAPI, and no `Depends(...)` ever appears
outside `interfaces/`.
"""

from typing import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker
from celery import Celery

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
from blueberry_microid.application.ports.dataset_release_repository import DatasetReleaseRepositoryPort
from blueberry_microid.application.ports.detection_training_artifact_issue_repository import (
    DetectionTrainingArtifactIssueRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_artifact_policy_repository import (
    DetectionTrainingArtifactPolicyRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_artifact_record_repository import (
    DetectionTrainingArtifactRecordRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_environment_issue_repository import (
    DetectionTrainingEnvironmentIssueRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_environment_spec_repository import (
    DetectionTrainingEnvironmentSpecRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_execution_issue_repository import (
    DetectionTrainingExecutionIssueRepositoryPort,
)
from blueberry_microid.application.ports.detection_training_execution_run_repository import (
    DetectionTrainingExecutionRunRepositoryPort,
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
from blueberry_microid.application.ports.object_detection_trainer import ObjectDetectionTrainerPort
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
from blueberry_microid.application.ports.image_storage import ImageStoragePort
from blueberry_microid.application.ports.image_validator import ImageValidatorPort
from blueberry_microid.application.ports.inference_engine import InferenceEnginePort
from blueberry_microid.application.ports.micro_image_repository import MicroImageRepositoryPort
from blueberry_microid.application.ports.model_version_repository import ModelVersionRepositoryPort
from blueberry_microid.application.ports.petri_image_repository import PetriImageRepositoryPort
from blueberry_microid.application.ports.petri_annotation_export_item_repository import (
    PetriAnnotationExportItemRepositoryPort,
)
from blueberry_microid.application.ports.petri_annotation_export_run_repository import (
    PetriAnnotationExportRunRepositoryPort,
)
from blueberry_microid.application.ports.petri_region_review_repository import PetriRegionReviewRepositoryPort
from blueberry_microid.application.ports.petri_segmentation_region_repository import (
    PetriSegmentationRegionRepositoryPort,
)
from blueberry_microid.application.ports.petri_segmentation_run_repository import PetriSegmentationRunRepositoryPort
from blueberry_microid.application.ports.prediction_repository import PredictionRepositoryPort
from blueberry_microid.application.ports.sample_repository import SampleRepositoryPort
from blueberry_microid.application.ports.training_preflight_issue_repository import TrainingPreflightIssueRepositoryPort
from blueberry_microid.application.ports.training_preflight_run_repository import TrainingPreflightRunRepositoryPort
from blueberry_microid.application.ports.training_prediction_repository import TrainingPredictionRepositoryPort
from blueberry_microid.application.ports.training_run_comparison_entry_repository import (
    TrainingRunComparisonEntryRepositoryPort,
)
from blueberry_microid.application.ports.training_run_comparison_repository import (
    TrainingRunComparisonRepositoryPort,
)
from blueberry_microid.application.ports.training_run_repository import TrainingRunRepositoryPort
from blueberry_microid.application.ports.unit_of_work import UnitOfWorkPort
from blueberry_microid.application.services.image_intake_service import ImageIntakeService
from blueberry_microid.application.services.annotation_bundle_validator import AnnotationBundleValidator
from blueberry_microid.application.services.annotation_bundle_writer import AnnotationBundleWriter
from blueberry_microid.application.services.annotation_quality_gate_validator import AnnotationQualityGateValidator
from blueberry_microid.application.services.dataset_manifest_exporter import DatasetManifestExporter
from blueberry_microid.application.services.detection_training_artifact_policy_evaluator import (
    DetectionTrainingArtifactPolicyEvaluator,
)
from blueberry_microid.application.services.detection_training_environment_evaluator import (
    DetectionTrainingEnvironmentEvaluator,
)
from blueberry_microid.application.services.detection_training_execution_gate_evaluator import (
    DetectionTrainingExecutionGateEvaluator,
)
from blueberry_microid.application.services.manual_yolo_training_runner_scaffold import (
    ManualYoloTrainingRunnerScaffold,
)
from blueberry_microid.application.services.detection_training_readiness_evaluator import (
    DetectionTrainingReadinessEvaluator,
)
from blueberry_microid.application.services.dataset_release_manifest_exporter import DatasetReleaseManifestExporter
from blueberry_microid.application.services.dataset_splitter import DatasetSplitter
from blueberry_microid.application.services.petri_reviewed_annotation_manifest_exporter import (
    PetriReviewedAnnotationManifestExporter,
)
from blueberry_microid.application.services.petri_annotation_exporter import PetriAnnotationExporter
from blueberry_microid.application.services.training_run_comparator import TrainingRunComparator
from blueberry_microid.application.use_cases.annotation_bundle.create_annotation_bundle_run import (
    CreateAnnotationBundleRunUseCase,
)
from blueberry_microid.application.use_cases.annotation_bundle.get_annotation_bundle_run import (
    GetAnnotationBundleRunUseCase,
)
from blueberry_microid.application.use_cases.annotation_bundle.list_annotation_bundle_files import (
    ListAnnotationBundleFilesUseCase,
)
from blueberry_microid.application.use_cases.annotation_bundle.list_annotation_bundle_runs import (
    ListAnnotationBundleRunsUseCase,
)
from blueberry_microid.application.use_cases.annotation_quality_gate.create_annotation_quality_gate_run import (
    CreateAnnotationQualityGateRunUseCase,
)
from blueberry_microid.application.use_cases.annotation_quality_gate.get_annotation_quality_gate_run import (
    GetAnnotationQualityGateRunUseCase,
)
from blueberry_microid.application.use_cases.annotation_quality_gate.list_annotation_quality_gate_issues import (
    ListAnnotationQualityGateIssuesUseCase,
)
from blueberry_microid.application.use_cases.annotation_quality_gate.list_annotation_quality_gate_runs import (
    ListAnnotationQualityGateRunsUseCase,
)
from blueberry_microid.application.use_cases.detection_training.create_detection_training_run import (
    CreateDetectionTrainingRunUseCase,
)
from blueberry_microid.application.use_cases.detection_training.get_detection_training_run import (
    GetDetectionTrainingRunUseCase,
)
from blueberry_microid.application.use_cases.detection_training.list_detection_training_issues import (
    ListDetectionTrainingIssuesUseCase,
)
from blueberry_microid.application.use_cases.detection_training.list_detection_training_runs import (
    ListDetectionTrainingRunsUseCase,
)
from blueberry_microid.application.use_cases.detection_training_readiness.create_detection_training_readiness_report import (
    CreateDetectionTrainingReadinessReportUseCase,
)
from blueberry_microid.application.use_cases.detection_training_readiness.get_detection_training_readiness_report import (
    GetDetectionTrainingReadinessReportUseCase,
)
from blueberry_microid.application.use_cases.detection_training_readiness.list_detection_training_readiness_issues import (
    ListDetectionTrainingReadinessIssuesUseCase,
)
from blueberry_microid.application.use_cases.detection_training_readiness.list_detection_training_readiness_reports import (
    ListDetectionTrainingReadinessReportsUseCase,
)
from blueberry_microid.application.use_cases.detection_training_environment.create_detection_training_environment_spec import (
    CreateDetectionTrainingEnvironmentSpecUseCase,
)
from blueberry_microid.application.use_cases.detection_training_environment.get_detection_training_environment_spec import (
    GetDetectionTrainingEnvironmentSpecUseCase,
)
from blueberry_microid.application.use_cases.detection_training_environment.list_detection_training_environment_issues import (
    ListDetectionTrainingEnvironmentIssuesUseCase,
)
from blueberry_microid.application.use_cases.detection_training_environment.list_detection_training_environment_specs import (
    ListDetectionTrainingEnvironmentSpecsUseCase,
)
from blueberry_microid.application.use_cases.detection_training_artifacts.create_detection_training_artifact_policy import (
    CreateDetectionTrainingArtifactPolicyUseCase,
)
from blueberry_microid.application.use_cases.detection_training_artifacts.get_detection_training_artifact_policy import (
    GetDetectionTrainingArtifactPolicyUseCase,
)
from blueberry_microid.application.use_cases.detection_training_artifacts.list_detection_training_artifact_issues import (
    ListDetectionTrainingArtifactIssuesUseCase,
)
from blueberry_microid.application.use_cases.detection_training_artifacts.list_detection_training_artifact_policies import (
    ListDetectionTrainingArtifactPoliciesUseCase,
)
from blueberry_microid.application.use_cases.detection_training_artifacts.list_detection_training_artifact_records import (
    ListDetectionTrainingArtifactRecordsUseCase,
)
from blueberry_microid.application.use_cases.detection_training_execution.create_detection_training_execution_run import (
    CreateDetectionTrainingExecutionRunUseCase,
)
from blueberry_microid.application.use_cases.detection_training_execution.get_detection_training_execution_run import (
    GetDetectionTrainingExecutionRunUseCase,
)
from blueberry_microid.application.use_cases.detection_training_execution.list_detection_training_execution_issues import (
    ListDetectionTrainingExecutionIssuesUseCase,
)
from blueberry_microid.application.use_cases.detection_training_execution.list_detection_training_execution_runs import (
    ListDetectionTrainingExecutionRunsUseCase,
)
from blueberry_microid.application.use_cases.dataset.create_dataset_release import CreateDatasetReleaseUseCase
from blueberry_microid.application.use_cases.dataset.create_dataset_snapshot import CreateDatasetSnapshotUseCase
from blueberry_microid.application.use_cases.dataset.get_dataset_release import GetDatasetReleaseUseCase
from blueberry_microid.application.use_cases.dataset.get_dataset_snapshot import GetDatasetSnapshotUseCase
from blueberry_microid.application.use_cases.dataset.list_dataset_items import ListDatasetItemsUseCase
from blueberry_microid.application.use_cases.dataset.list_dataset_releases import ListDatasetReleasesUseCase
from blueberry_microid.application.use_cases.dataset.list_dataset_snapshots import ListDatasetSnapshotsUseCase
from blueberry_microid.application.use_cases.dataset.list_dataset_split_items import ListDatasetSplitItemsUseCase
from blueberry_microid.application.use_cases.inference.create_analysis_run import CreateAnalysisRunUseCase
from blueberry_microid.application.use_cases.inference.get_analysis_run import GetAnalysisRunUseCase
from blueberry_microid.application.use_cases.inference.get_prediction import GetPredictionForAnalysisRunUseCase
from blueberry_microid.application.use_cases.inference.process_analysis_run import ProcessAnalysisRunUseCase
from blueberry_microid.application.use_cases.image_audit.create_image_dataset_audit_run import (
    CreateImageDatasetAuditRunUseCase,
)
from blueberry_microid.application.use_cases.image_audit.get_image_dataset_audit_run import (
    GetImageDatasetAuditRunUseCase,
)
from blueberry_microid.application.use_cases.image_audit.list_image_dataset_audit_issues import (
    ListImageDatasetAuditIssuesUseCase,
)
from blueberry_microid.application.use_cases.image_audit.list_image_dataset_audit_runs import (
    ListImageDatasetAuditRunsUseCase,
)
from blueberry_microid.application.use_cases.image_feature_extraction.create_image_feature_extraction_run import (
    CreateImageFeatureExtractionRunUseCase,
)
from blueberry_microid.application.use_cases.image_feature_extraction.get_image_feature_extraction_run import (
    GetImageFeatureExtractionRunUseCase,
)
from blueberry_microid.application.use_cases.image_feature_extraction.list_image_feature_extraction_runs import (
    ListImageFeatureExtractionRunsUseCase,
)
from blueberry_microid.application.use_cases.image_feature_extraction.list_image_feature_vectors import (
    ListImageFeatureVectorsUseCase,
)
from blueberry_microid.application.use_cases.ml_preflight.create_training_preflight_run import (
    CreateTrainingPreflightRunUseCase,
)
from blueberry_microid.application.use_cases.ml_preflight.get_training_preflight_run import (
    GetTrainingPreflightRunUseCase,
)
from blueberry_microid.application.use_cases.ml_preflight.list_training_preflight_issues import (
    ListTrainingPreflightIssuesUseCase,
)
from blueberry_microid.application.use_cases.ml_preflight.list_training_preflight_runs import (
    ListTrainingPreflightRunsUseCase,
)
from blueberry_microid.application.use_cases.training.create_baseline_training_run import (
    CreateBaselineTrainingRunUseCase,
)
from blueberry_microid.application.use_cases.training.create_classical_baseline_training_run import (
    CreateClassicalBaselineTrainingRunUseCase,
)
from blueberry_microid.application.use_cases.training.create_training_run_comparison import (
    CreateTrainingRunComparisonUseCase,
)
from blueberry_microid.application.use_cases.training.get_training_run import GetTrainingRunUseCase
from blueberry_microid.application.use_cases.training.get_training_run_comparison import (
    GetTrainingRunComparisonUseCase,
)
from blueberry_microid.application.use_cases.training.list_training_run_comparison_entries import (
    ListTrainingRunComparisonEntriesUseCase,
)
from blueberry_microid.application.use_cases.training.list_training_run_comparisons import (
    ListTrainingRunComparisonsUseCase,
)
from blueberry_microid.application.use_cases.training.list_training_predictions import ListTrainingPredictionsUseCase
from blueberry_microid.application.use_cases.training.list_training_runs import ListTrainingRunsUseCase
from blueberry_microid.application.use_cases.micro_image.register_micro_image import RegisterMicroImageUseCase
from blueberry_microid.application.use_cases.model_version.create_model_version import CreateModelVersionUseCase
from blueberry_microid.application.use_cases.model_version.list_model_versions import ListModelVersionsUseCase
from blueberry_microid.application.use_cases.petri_image.register_petri_image import RegisterPetriImageUseCase
from blueberry_microid.application.use_cases.petri_annotation_export.create_petri_annotation_export_run import (
    CreatePetriAnnotationExportRunUseCase,
)
from blueberry_microid.application.use_cases.petri_annotation_export.get_petri_annotation_export_run import (
    GetPetriAnnotationExportRunUseCase,
)
from blueberry_microid.application.use_cases.petri_annotation_export.list_petri_annotation_export_items import (
    ListPetriAnnotationExportItemsUseCase,
)
from blueberry_microid.application.use_cases.petri_annotation_export.list_petri_annotation_export_runs import (
    ListPetriAnnotationExportRunsUseCase,
)
from blueberry_microid.application.use_cases.petri_region_review.get_final_petri_region_review import (
    GetFinalPetriRegionReviewUseCase,
)
from blueberry_microid.application.use_cases.petri_region_review.get_petri_region_review import (
    GetPetriRegionReviewUseCase,
)
from blueberry_microid.application.use_cases.petri_region_review.list_petri_region_reviews import (
    ListPetriRegionReviewsUseCase,
)
from blueberry_microid.application.use_cases.petri_region_review.submit_petri_region_review import (
    SubmitPetriRegionReviewUseCase,
)
from blueberry_microid.application.use_cases.petri_segmentation.create_petri_segmentation_run import (
    CreatePetriSegmentationRunUseCase,
)
from blueberry_microid.application.use_cases.petri_segmentation.get_petri_segmentation_run import (
    GetPetriSegmentationRunUseCase,
)
from blueberry_microid.application.use_cases.petri_segmentation.list_petri_segmentation_regions import (
    ListPetriSegmentationRegionsUseCase,
)
from blueberry_microid.application.use_cases.petri_segmentation.list_petri_segmentation_runs import (
    ListPetriSegmentationRunsUseCase,
)
from blueberry_microid.application.use_cases.review.get_final_human_review import GetFinalHumanReviewUseCase
from blueberry_microid.application.use_cases.review.list_human_reviews import ListHumanReviewsUseCase
from blueberry_microid.application.use_cases.review.submit_human_review import SubmitHumanReviewUseCase
from blueberry_microid.application.use_cases.sample.create_sample import CreateSampleUseCase
from blueberry_microid.application.use_cases.sample.get_sample import (
    GetSampleByIdUseCase,
    GetSampleBySampleCodeUseCase,
)
from blueberry_microid.infrastructure.config.settings import Settings
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
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_detection_training_execution_issue_repository import (
    SqlAlchemyDetectionTrainingExecutionIssueRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_detection_training_execution_run_repository import (
    SqlAlchemyDetectionTrainingExecutionRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_detection_training_environment_issue_repository import (
    SqlAlchemyDetectionTrainingEnvironmentIssueRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_detection_training_environment_spec_repository import (
    SqlAlchemyDetectionTrainingEnvironmentSpecRepository,
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
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_micro_image_repository import (
    SqlAlchemyMicroImageRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_model_version_repository import (
    SqlAlchemyModelVersionRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_petri_image_repository import (
    SqlAlchemyPetriImageRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_petri_annotation_export_item_repository import (
    SqlAlchemyPetriAnnotationExportItemRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_petri_annotation_export_run_repository import (
    SqlAlchemyPetriAnnotationExportRunRepository,
)
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_petri_region_review_repository import (
    SqlAlchemyPetriRegionReviewRepository,
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
from blueberry_microid.infrastructure.db.repositories.sqlalchemy_sample_repository import SqlAlchemySampleRepository
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
from blueberry_microid.infrastructure.db.session.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
from blueberry_microid.infrastructure.storage.local_image_storage import LocalImageStorage
from blueberry_microid.infrastructure.storage.local_upload_storage import LocalUploadStorage
from blueberry_microid.infrastructure.storage.pillow_image_validator import PillowImageValidator
from blueberry_microid.infrastructure.tasks.analysis_tasks import process_analysis_run_task
from blueberry_microid.infrastructure.tasks.celery_app import celery_app
from blueberry_microid.ml.inference_engine.mock_inference_engine import MockInferenceEngine
from blueberry_microid.ml.inference_engine.preliminary_two_image_analysis_engine import (
    PreliminaryTwoImageAnalysisEngine,
)
from blueberry_microid.application.use_cases.analysis.analyze_two_uploaded_images import (
    AnalyzeTwoUploadedImagesUseCase,
)
from blueberry_microid.application.use_cases.analysis.get_final_analysis_result import (
    GetFinalAnalysisResultUseCase,
)
from blueberry_microid.application.use_cases.analysis.get_preliminary_result_with_review import (
    GetPreliminaryResultWithReviewUseCase,
)
from blueberry_microid.ml.preprocessing.classical_petri_segmenter import ClassicalPetriSegmenter
from blueberry_microid.ml.preprocessing.image_feature_extractor import ImageFeatureExtractor
from blueberry_microid.ml.training.classical_tabular_baseline import ClassicalTabularBaselineTrainer
from blueberry_microid.ml.training.feature_matrix_builder import FeatureMatrixBuilder
from blueberry_microid.ml.training.majority_class_baseline import MajorityClassBaselineTrainer
from blueberry_microid.ml.training.yolo_dry_run_trainer import YoloDryRunTrainer
from blueberry_microid.ml.validation.image_dataset_auditor import ImageDatasetAuditor
from blueberry_microid.ml.validation.image_path_validator import ImagePathValidator
from blueberry_microid.ml.validation.manifest_validator import ManifestValidator

# --- settings & database session -----------------------------------------


def get_settings_dependency(request: Request) -> Settings:
    """Read from `request.app.state`, not a module-level global, so tests
    can swap in a different Settings instance per-app (see tests/api/conftest.py).
    """
    return request.app.state.settings


def get_db_session(request: Request) -> Iterator[Session]:
    """One Session per request, closed when the request finishes.

    The session factory lives on `app.state` (set once in `create_app()`),
    not imported as a module-level global, for the same testability reason.
    """
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_session_factory(request: Request) -> sessionmaker[Session]:
    """Exposes the raw session factory (not a single Session) for
    `UnitOfWorkPort`, which needs to open its own, separate transaction —
    see `get_unit_of_work` below.
    """
    return request.app.state.session_factory


def get_unit_of_work(session_factory: sessionmaker[Session] = Depends(get_session_factory)) -> UnitOfWorkPort:
    return SqlAlchemyUnitOfWork(session_factory)


def get_celery_app(request: Request) -> Celery:
    return getattr(request.app.state, "celery_app", celery_app)


def get_process_analysis_run_task():
    return process_analysis_run_task


# --- infrastructure: storage & validation ---------------------------------


def get_image_storage(settings: Settings = Depends(get_settings_dependency)) -> ImageStoragePort:
    return LocalImageStorage(settings.storage_root)


def get_image_validator() -> ImageValidatorPort:
    return PillowImageValidator()


def get_image_intake_service(
    settings: Settings = Depends(get_settings_dependency),
    image_validator: ImageValidatorPort = Depends(get_image_validator),
    image_storage: ImageStoragePort = Depends(get_image_storage),
) -> ImageIntakeService:
    # The upload size ceiling always comes from Settings (MAX_UPLOAD_SIZE_MB)
    # — never hardcoded in a router — so it is one source of truth and one
    # environment variable to change it.
    return ImageIntakeService(image_validator, image_storage, settings.max_upload_size_bytes)


def get_upload_storage(settings: Settings = Depends(get_settings_dependency)) -> ImageStoragePort:
    return LocalUploadStorage(settings.upload_storage_path)


# --- repositories ----------------------------------------------------------


def get_sample_repository(session: Session = Depends(get_db_session)) -> SampleRepositoryPort:
    return SqlAlchemySampleRepository(session)


def get_petri_image_repository(session: Session = Depends(get_db_session)) -> PetriImageRepositoryPort:
    return SqlAlchemyPetriImageRepository(session)


def get_micro_image_repository(session: Session = Depends(get_db_session)) -> MicroImageRepositoryPort:
    return SqlAlchemyMicroImageRepository(session)


def get_model_version_repository(session: Session = Depends(get_db_session)) -> ModelVersionRepositoryPort:
    return SqlAlchemyModelVersionRepository(session)


def get_analyze_two_uploaded_images_use_case(
    settings: Settings = Depends(get_settings_dependency),
    image_validator: ImageValidatorPort = Depends(get_image_validator),
    upload_storage: ImageStoragePort = Depends(get_upload_storage),
    sample_repository: SampleRepositoryPort = Depends(get_sample_repository),
    petri_image_repository: PetriImageRepositoryPort = Depends(get_petri_image_repository),
    micro_image_repository: MicroImageRepositoryPort = Depends(get_micro_image_repository),
    model_version_repository: ModelVersionRepositoryPort = Depends(get_model_version_repository),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> AnalyzeTwoUploadedImagesUseCase:
    engine = PreliminaryTwoImageAnalysisEngine()
    return AnalyzeTwoUploadedImagesUseCase(
        image_validator=image_validator,
        upload_storage=upload_storage,
        engine=engine,
        sample_repository=sample_repository,
        petri_image_repository=petri_image_repository,
        micro_image_repository=micro_image_repository,
        model_version_repository=model_version_repository,
        unit_of_work=unit_of_work,
        max_upload_size_bytes=settings.max_upload_size_bytes,
    )


def get_analysis_run_repository(session: Session = Depends(get_db_session)) -> AnalysisRunRepositoryPort:
    return SqlAlchemyAnalysisRunRepository(session)


def get_human_review_repository(session: Session = Depends(get_db_session)) -> HumanReviewRepositoryPort:
    return SqlAlchemyHumanReviewRepository(session)


def get_prediction_repository(session: Session = Depends(get_db_session)) -> PredictionRepositoryPort:
    return SqlAlchemyPredictionRepository(session)


def get_dataset_snapshot_repository(session: Session = Depends(get_db_session)) -> DatasetSnapshotRepositoryPort:
    return SqlAlchemyDatasetSnapshotRepository(session)


def get_dataset_item_repository(session: Session = Depends(get_db_session)) -> DatasetItemRepositoryPort:
    return SqlAlchemyDatasetItemRepository(session)


def get_dataset_release_repository(session: Session = Depends(get_db_session)) -> DatasetReleaseRepositoryPort:
    return SqlAlchemyDatasetReleaseRepository(session)


def get_dataset_split_item_repository(session: Session = Depends(get_db_session)) -> DatasetSplitItemRepositoryPort:
    return SqlAlchemyDatasetSplitItemRepository(session)


def get_training_preflight_run_repository(
    session: Session = Depends(get_db_session),
) -> TrainingPreflightRunRepositoryPort:
    return SqlAlchemyTrainingPreflightRunRepository(session)


def get_training_preflight_issue_repository(
    session: Session = Depends(get_db_session),
) -> TrainingPreflightIssueRepositoryPort:
    return SqlAlchemyTrainingPreflightIssueRepository(session)


def get_training_run_repository(session: Session = Depends(get_db_session)) -> TrainingRunRepositoryPort:
    return SqlAlchemyTrainingRunRepository(session)


def get_training_prediction_repository(
    session: Session = Depends(get_db_session),
) -> TrainingPredictionRepositoryPort:
    return SqlAlchemyTrainingPredictionRepository(session)


def get_training_run_comparison_repository(
    session: Session = Depends(get_db_session),
) -> TrainingRunComparisonRepositoryPort:
    return SqlAlchemyTrainingRunComparisonRepository(session)


def get_training_run_comparison_entry_repository(
    session: Session = Depends(get_db_session),
) -> TrainingRunComparisonEntryRepositoryPort:
    return SqlAlchemyTrainingRunComparisonEntryRepository(session)


def get_image_dataset_audit_run_repository(
    session: Session = Depends(get_db_session),
) -> ImageDatasetAuditRunRepositoryPort:
    return SqlAlchemyImageDatasetAuditRunRepository(session)


def get_image_dataset_audit_issue_repository(
    session: Session = Depends(get_db_session),
) -> ImageDatasetAuditIssueRepositoryPort:
    return SqlAlchemyImageDatasetAuditIssueRepository(session)


def get_image_feature_extraction_run_repository(
    session: Session = Depends(get_db_session),
) -> ImageFeatureExtractionRunRepositoryPort:
    return SqlAlchemyImageFeatureExtractionRunRepository(session)


def get_image_feature_vector_repository(
    session: Session = Depends(get_db_session),
) -> ImageFeatureVectorRepositoryPort:
    return SqlAlchemyImageFeatureVectorRepository(session)


def get_petri_segmentation_run_repository(
    session: Session = Depends(get_db_session),
) -> PetriSegmentationRunRepositoryPort:
    return SqlAlchemyPetriSegmentationRunRepository(session)


def get_petri_segmentation_region_repository(
    session: Session = Depends(get_db_session),
) -> PetriSegmentationRegionRepositoryPort:
    return SqlAlchemyPetriSegmentationRegionRepository(session)


def get_petri_region_review_repository(
    session: Session = Depends(get_db_session),
) -> PetriRegionReviewRepositoryPort:
    return SqlAlchemyPetriRegionReviewRepository(session)


def get_petri_annotation_export_run_repository(
    session: Session = Depends(get_db_session),
) -> PetriAnnotationExportRunRepositoryPort:
    return SqlAlchemyPetriAnnotationExportRunRepository(session)


def get_petri_annotation_export_item_repository(
    session: Session = Depends(get_db_session),
) -> PetriAnnotationExportItemRepositoryPort:
    return SqlAlchemyPetriAnnotationExportItemRepository(session)


def get_annotation_bundle_run_repository(
    session: Session = Depends(get_db_session),
) -> AnnotationBundleRunRepositoryPort:
    return SqlAlchemyAnnotationBundleRunRepository(session)


def get_annotation_bundle_file_repository(
    session: Session = Depends(get_db_session),
) -> AnnotationBundleFileRepositoryPort:
    return SqlAlchemyAnnotationBundleFileRepository(session)


def get_annotation_quality_gate_run_repository(
    session: Session = Depends(get_db_session),
) -> AnnotationQualityGateRunRepositoryPort:
    return SqlAlchemyAnnotationQualityGateRunRepository(session)


def get_annotation_quality_gate_issue_repository(
    session: Session = Depends(get_db_session),
) -> AnnotationQualityGateIssueRepositoryPort:
    return SqlAlchemyAnnotationQualityGateIssueRepository(session)


def get_detection_training_run_repository(
    session: Session = Depends(get_db_session),
) -> DetectionTrainingRunRepositoryPort:
    return SqlAlchemyDetectionTrainingRunRepository(session)


def get_detection_training_issue_repository(
    session: Session = Depends(get_db_session),
) -> DetectionTrainingIssueRepositoryPort:
    return SqlAlchemyDetectionTrainingIssueRepository(session)


def get_detection_training_readiness_report_repository(
    session: Session = Depends(get_db_session),
) -> DetectionTrainingReadinessReportRepositoryPort:
    return SqlAlchemyDetectionTrainingReadinessReportRepository(session)


def get_detection_training_readiness_issue_repository(
    session: Session = Depends(get_db_session),
) -> DetectionTrainingReadinessIssueRepositoryPort:
    return SqlAlchemyDetectionTrainingReadinessIssueRepository(session)


def get_detection_training_environment_spec_repository(
    session: Session = Depends(get_db_session),
) -> DetectionTrainingEnvironmentSpecRepositoryPort:
    return SqlAlchemyDetectionTrainingEnvironmentSpecRepository(session)


def get_detection_training_environment_issue_repository(
    session: Session = Depends(get_db_session),
) -> DetectionTrainingEnvironmentIssueRepositoryPort:
    return SqlAlchemyDetectionTrainingEnvironmentIssueRepository(session)


def get_detection_training_artifact_policy_repository(
    session: Session = Depends(get_db_session),
) -> DetectionTrainingArtifactPolicyRepositoryPort:
    return SqlAlchemyDetectionTrainingArtifactPolicyRepository(session)


def get_detection_training_artifact_record_repository(
    session: Session = Depends(get_db_session),
) -> DetectionTrainingArtifactRecordRepositoryPort:
    return SqlAlchemyDetectionTrainingArtifactRecordRepository(session)


def get_detection_training_artifact_issue_repository(
    session: Session = Depends(get_db_session),
) -> DetectionTrainingArtifactIssueRepositoryPort:
    return SqlAlchemyDetectionTrainingArtifactIssueRepository(session)


def get_detection_training_execution_run_repository(
    session: Session = Depends(get_db_session),
) -> DetectionTrainingExecutionRunRepositoryPort:
    return SqlAlchemyDetectionTrainingExecutionRunRepository(session)


def get_detection_training_execution_issue_repository(
    session: Session = Depends(get_db_session),
) -> DetectionTrainingExecutionIssueRepositoryPort:
    return SqlAlchemyDetectionTrainingExecutionIssueRepository(session)


# --- dataset splitting service ------------------------------------------------


def get_dataset_splitter() -> DatasetSplitter:
    return DatasetSplitter()


def get_manifest_validator() -> ManifestValidator:
    return ManifestValidator()


def get_image_path_validator() -> ImagePathValidator:
    return ImagePathValidator()


def get_image_dataset_auditor() -> ImageDatasetAuditor:
    return ImageDatasetAuditor()


def get_petri_annotation_exporter() -> PetriAnnotationExporter:
    return PetriAnnotationExporter()


def get_annotation_bundle_validator() -> AnnotationBundleValidator:
    return AnnotationBundleValidator()


def get_annotation_bundle_writer() -> AnnotationBundleWriter:
    return AnnotationBundleWriter()


def get_annotation_quality_gate_validator() -> AnnotationQualityGateValidator:
    return AnnotationQualityGateValidator()


def get_yolo_dry_run_trainer() -> ObjectDetectionTrainerPort:
    return YoloDryRunTrainer()


def get_detection_training_readiness_evaluator() -> DetectionTrainingReadinessEvaluator:
    return DetectionTrainingReadinessEvaluator()


def get_detection_training_environment_evaluator() -> DetectionTrainingEnvironmentEvaluator:
    return DetectionTrainingEnvironmentEvaluator()


def get_detection_training_artifact_policy_evaluator() -> DetectionTrainingArtifactPolicyEvaluator:
    return DetectionTrainingArtifactPolicyEvaluator()


def get_detection_training_execution_gate_evaluator() -> DetectionTrainingExecutionGateEvaluator:
    return DetectionTrainingExecutionGateEvaluator()


def get_manual_yolo_training_runner_scaffold() -> ManualYoloTrainingRunnerScaffold:
    return ManualYoloTrainingRunnerScaffold()


def get_image_feature_extractor() -> ImageFeatureExtractor:
    return ImageFeatureExtractor()


def get_classical_petri_segmenter() -> ClassicalPetriSegmenter:
    return ClassicalPetriSegmenter()


def get_majority_class_baseline_trainer() -> MajorityClassBaselineTrainer:
    return MajorityClassBaselineTrainer()


def get_feature_matrix_builder() -> FeatureMatrixBuilder:
    return FeatureMatrixBuilder()


def get_classical_tabular_baseline_trainer() -> ClassicalTabularBaselineTrainer:
    return ClassicalTabularBaselineTrainer()


def get_training_run_comparator() -> TrainingRunComparator:
    return TrainingRunComparator()


# --- inference engine --------------------------------------------------------


def get_inference_engine() -> InferenceEnginePort:
    """Selects which InferenceEnginePort implementation the API uses.

    Currently always `MockInferenceEngine` — a deterministic simulation,
    not real image analysis (see its docstring and ARCHITECTURE.md). This
    is the single place that would change to plug in a real/trained model
    later; nothing else in `application/` or `interfaces/` refers to
    `MockInferenceEngine` by name.
    """
    return MockInferenceEngine()


# --- use cases ---------------------------------------------------------------


def get_create_sample_use_case(
    sample_repository: SampleRepositoryPort = Depends(get_sample_repository),
) -> CreateSampleUseCase:
    return CreateSampleUseCase(sample_repository)


def get_get_sample_by_id_use_case(
    sample_repository: SampleRepositoryPort = Depends(get_sample_repository),
) -> GetSampleByIdUseCase:
    return GetSampleByIdUseCase(sample_repository)


def get_get_sample_by_code_use_case(
    sample_repository: SampleRepositoryPort = Depends(get_sample_repository),
) -> GetSampleBySampleCodeUseCase:
    return GetSampleBySampleCodeUseCase(sample_repository)


def get_register_petri_image_use_case(
    sample_repository: SampleRepositoryPort = Depends(get_sample_repository),
    petri_image_repository: PetriImageRepositoryPort = Depends(get_petri_image_repository),
    image_intake: ImageIntakeService = Depends(get_image_intake_service),
) -> RegisterPetriImageUseCase:
    return RegisterPetriImageUseCase(sample_repository, petri_image_repository, image_intake)


def get_register_micro_image_use_case(
    sample_repository: SampleRepositoryPort = Depends(get_sample_repository),
    micro_image_repository: MicroImageRepositoryPort = Depends(get_micro_image_repository),
    image_intake: ImageIntakeService = Depends(get_image_intake_service),
) -> RegisterMicroImageUseCase:
    return RegisterMicroImageUseCase(sample_repository, micro_image_repository, image_intake)


def get_create_model_version_use_case(
    model_version_repository: ModelVersionRepositoryPort = Depends(get_model_version_repository),
) -> CreateModelVersionUseCase:
    return CreateModelVersionUseCase(model_version_repository)


def get_list_model_versions_use_case(
    model_version_repository: ModelVersionRepositoryPort = Depends(get_model_version_repository),
) -> ListModelVersionsUseCase:
    return ListModelVersionsUseCase(model_version_repository)


def get_create_analysis_run_use_case(
    sample_repository: SampleRepositoryPort = Depends(get_sample_repository),
    petri_image_repository: PetriImageRepositoryPort = Depends(get_petri_image_repository),
    micro_image_repository: MicroImageRepositoryPort = Depends(get_micro_image_repository),
    model_version_repository: ModelVersionRepositoryPort = Depends(get_model_version_repository),
    analysis_run_repository: AnalysisRunRepositoryPort = Depends(get_analysis_run_repository),
) -> CreateAnalysisRunUseCase:
    return CreateAnalysisRunUseCase(
        sample_repository,
        petri_image_repository,
        micro_image_repository,
        model_version_repository,
        analysis_run_repository,
    )


def get_get_analysis_run_use_case(
    analysis_run_repository: AnalysisRunRepositoryPort = Depends(get_analysis_run_repository),
) -> GetAnalysisRunUseCase:
    return GetAnalysisRunUseCase(analysis_run_repository)


def get_process_analysis_run_use_case(
    analysis_run_repository: AnalysisRunRepositoryPort = Depends(get_analysis_run_repository),
    petri_image_repository: PetriImageRepositoryPort = Depends(get_petri_image_repository),
    micro_image_repository: MicroImageRepositoryPort = Depends(get_micro_image_repository),
    model_version_repository: ModelVersionRepositoryPort = Depends(get_model_version_repository),
    inference_engine: InferenceEnginePort = Depends(get_inference_engine),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> ProcessAnalysisRunUseCase:
    return ProcessAnalysisRunUseCase(
        analysis_run_repository,
        petri_image_repository,
        micro_image_repository,
        model_version_repository,
        inference_engine,
        unit_of_work,
    )


def get_get_prediction_use_case(
    prediction_repository: PredictionRepositoryPort = Depends(get_prediction_repository),
) -> GetPredictionForAnalysisRunUseCase:
    return GetPredictionForAnalysisRunUseCase(prediction_repository)


def get_submit_human_review_use_case(
    analysis_run_repository: AnalysisRunRepositoryPort = Depends(get_analysis_run_repository),
    prediction_repository: PredictionRepositoryPort = Depends(get_prediction_repository),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> SubmitHumanReviewUseCase:
    return SubmitHumanReviewUseCase(analysis_run_repository, prediction_repository, unit_of_work)


def get_get_final_human_review_use_case(
    analysis_run_repository: AnalysisRunRepositoryPort = Depends(get_analysis_run_repository),
    human_review_repository: HumanReviewRepositoryPort = Depends(get_human_review_repository),
) -> GetFinalHumanReviewUseCase:
    return GetFinalHumanReviewUseCase(analysis_run_repository, human_review_repository)


def get_list_human_reviews_use_case(
    analysis_run_repository: AnalysisRunRepositoryPort = Depends(get_analysis_run_repository),
    human_review_repository: HumanReviewRepositoryPort = Depends(get_human_review_repository),
) -> ListHumanReviewsUseCase:
    return ListHumanReviewsUseCase(analysis_run_repository, human_review_repository)


def get_get_preliminary_result_with_review_use_case(
    analysis_run_repository: AnalysisRunRepositoryPort = Depends(get_analysis_run_repository),
    prediction_repository: PredictionRepositoryPort = Depends(get_prediction_repository),
    human_review_repository: HumanReviewRepositoryPort = Depends(get_human_review_repository),
) -> GetPreliminaryResultWithReviewUseCase:
    return GetPreliminaryResultWithReviewUseCase(
        analysis_run_repository, prediction_repository, human_review_repository
    )


def get_get_final_analysis_result_use_case(
    analysis_run_repository: AnalysisRunRepositoryPort = Depends(get_analysis_run_repository),
    prediction_repository: PredictionRepositoryPort = Depends(get_prediction_repository),
    human_review_repository: HumanReviewRepositoryPort = Depends(get_human_review_repository),
) -> GetFinalAnalysisResultUseCase:
    return GetFinalAnalysisResultUseCase(
        analysis_run_repository, prediction_repository, human_review_repository
    )


def get_create_dataset_snapshot_use_case(
    analysis_run_repository: AnalysisRunRepositoryPort = Depends(get_analysis_run_repository),
    prediction_repository: PredictionRepositoryPort = Depends(get_prediction_repository),
    human_review_repository: HumanReviewRepositoryPort = Depends(get_human_review_repository),
    petri_image_repository: PetriImageRepositoryPort = Depends(get_petri_image_repository),
    micro_image_repository: MicroImageRepositoryPort = Depends(get_micro_image_repository),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> CreateDatasetSnapshotUseCase:
    return CreateDatasetSnapshotUseCase(
        analysis_run_repository,
        prediction_repository,
        human_review_repository,
        petri_image_repository,
        micro_image_repository,
        unit_of_work,
    )


def get_get_dataset_snapshot_use_case(
    dataset_snapshot_repository: DatasetSnapshotRepositoryPort = Depends(get_dataset_snapshot_repository),
) -> GetDatasetSnapshotUseCase:
    return GetDatasetSnapshotUseCase(dataset_snapshot_repository)


def get_list_dataset_snapshots_use_case(
    dataset_snapshot_repository: DatasetSnapshotRepositoryPort = Depends(get_dataset_snapshot_repository),
) -> ListDatasetSnapshotsUseCase:
    return ListDatasetSnapshotsUseCase(dataset_snapshot_repository)


def get_list_dataset_items_use_case(
    dataset_snapshot_repository: DatasetSnapshotRepositoryPort = Depends(get_dataset_snapshot_repository),
    dataset_item_repository: DatasetItemRepositoryPort = Depends(get_dataset_item_repository),
) -> ListDatasetItemsUseCase:
    return ListDatasetItemsUseCase(dataset_snapshot_repository, dataset_item_repository)


def get_dataset_manifest_exporter(
    dataset_snapshot_repository: DatasetSnapshotRepositoryPort = Depends(get_dataset_snapshot_repository),
    dataset_item_repository: DatasetItemRepositoryPort = Depends(get_dataset_item_repository),
    sample_repository: SampleRepositoryPort = Depends(get_sample_repository),
    petri_image_repository: PetriImageRepositoryPort = Depends(get_petri_image_repository),
    micro_image_repository: MicroImageRepositoryPort = Depends(get_micro_image_repository),
    prediction_repository: PredictionRepositoryPort = Depends(get_prediction_repository),
) -> DatasetManifestExporter:
    return DatasetManifestExporter(
        dataset_snapshot_repository,
        dataset_item_repository,
        sample_repository,
        petri_image_repository,
        micro_image_repository,
        prediction_repository,
    )


def get_create_dataset_release_use_case(
    dataset_snapshot_repository: DatasetSnapshotRepositoryPort = Depends(get_dataset_snapshot_repository),
    dataset_item_repository: DatasetItemRepositoryPort = Depends(get_dataset_item_repository),
    sample_repository: SampleRepositoryPort = Depends(get_sample_repository),
    dataset_splitter: DatasetSplitter = Depends(get_dataset_splitter),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> CreateDatasetReleaseUseCase:
    return CreateDatasetReleaseUseCase(
        dataset_snapshot_repository,
        dataset_item_repository,
        sample_repository,
        dataset_splitter,
        unit_of_work,
    )


def get_get_dataset_release_use_case(
    dataset_release_repository: DatasetReleaseRepositoryPort = Depends(get_dataset_release_repository),
) -> GetDatasetReleaseUseCase:
    return GetDatasetReleaseUseCase(dataset_release_repository)


def get_list_dataset_releases_use_case(
    dataset_release_repository: DatasetReleaseRepositoryPort = Depends(get_dataset_release_repository),
) -> ListDatasetReleasesUseCase:
    return ListDatasetReleasesUseCase(dataset_release_repository)


def get_list_dataset_split_items_use_case(
    dataset_release_repository: DatasetReleaseRepositoryPort = Depends(get_dataset_release_repository),
    dataset_split_item_repository: DatasetSplitItemRepositoryPort = Depends(get_dataset_split_item_repository),
) -> ListDatasetSplitItemsUseCase:
    return ListDatasetSplitItemsUseCase(dataset_release_repository, dataset_split_item_repository)


def get_dataset_release_manifest_exporter(
    dataset_release_repository: DatasetReleaseRepositoryPort = Depends(get_dataset_release_repository),
    dataset_split_item_repository: DatasetSplitItemRepositoryPort = Depends(get_dataset_split_item_repository),
    dataset_item_repository: DatasetItemRepositoryPort = Depends(get_dataset_item_repository),
    sample_repository: SampleRepositoryPort = Depends(get_sample_repository),
    petri_image_repository: PetriImageRepositoryPort = Depends(get_petri_image_repository),
    micro_image_repository: MicroImageRepositoryPort = Depends(get_micro_image_repository),
    prediction_repository: PredictionRepositoryPort = Depends(get_prediction_repository),
) -> DatasetReleaseManifestExporter:
    return DatasetReleaseManifestExporter(
        dataset_release_repository,
        dataset_split_item_repository,
        dataset_item_repository,
        sample_repository,
        petri_image_repository,
        micro_image_repository,
        prediction_repository,
    )


def get_create_training_preflight_run_use_case(
    manifest_exporter: DatasetReleaseManifestExporter = Depends(get_dataset_release_manifest_exporter),
    manifest_validator: ManifestValidator = Depends(get_manifest_validator),
    image_path_validator: ImagePathValidator = Depends(get_image_path_validator),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> CreateTrainingPreflightRunUseCase:
    return CreateTrainingPreflightRunUseCase(
        manifest_exporter,
        manifest_validator,
        image_path_validator,
        unit_of_work,
    )


def get_get_training_preflight_run_use_case(
    preflight_run_repository: TrainingPreflightRunRepositoryPort = Depends(get_training_preflight_run_repository),
    preflight_issue_repository: TrainingPreflightIssueRepositoryPort = Depends(
        get_training_preflight_issue_repository
    ),
) -> GetTrainingPreflightRunUseCase:
    return GetTrainingPreflightRunUseCase(preflight_run_repository, preflight_issue_repository)


def get_list_training_preflight_runs_use_case(
    preflight_run_repository: TrainingPreflightRunRepositoryPort = Depends(get_training_preflight_run_repository),
    dataset_release_repository: DatasetReleaseRepositoryPort = Depends(get_dataset_release_repository),
) -> ListTrainingPreflightRunsUseCase:
    return ListTrainingPreflightRunsUseCase(preflight_run_repository, dataset_release_repository)


def get_list_training_preflight_issues_use_case(
    preflight_run_repository: TrainingPreflightRunRepositoryPort = Depends(get_training_preflight_run_repository),
    preflight_issue_repository: TrainingPreflightIssueRepositoryPort = Depends(
        get_training_preflight_issue_repository
    ),
) -> ListTrainingPreflightIssuesUseCase:
    return ListTrainingPreflightIssuesUseCase(preflight_run_repository, preflight_issue_repository)


def get_create_baseline_training_run_use_case(
    dataset_release_repository: DatasetReleaseRepositoryPort = Depends(get_dataset_release_repository),
    preflight_run_repository: TrainingPreflightRunRepositoryPort = Depends(get_training_preflight_run_repository),
    dataset_split_item_repository: DatasetSplitItemRepositoryPort = Depends(get_dataset_split_item_repository),
    dataset_item_repository: DatasetItemRepositoryPort = Depends(get_dataset_item_repository),
    manifest_exporter: DatasetReleaseManifestExporter = Depends(get_dataset_release_manifest_exporter),
    manifest_validator: ManifestValidator = Depends(get_manifest_validator),
    trainer: MajorityClassBaselineTrainer = Depends(get_majority_class_baseline_trainer),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> CreateBaselineTrainingRunUseCase:
    return CreateBaselineTrainingRunUseCase(
        dataset_release_repository,
        preflight_run_repository,
        dataset_split_item_repository,
        dataset_item_repository,
        manifest_exporter,
        manifest_validator,
        trainer,
        unit_of_work,
    )


def get_create_classical_baseline_training_run_use_case(
    dataset_release_repository: DatasetReleaseRepositoryPort = Depends(get_dataset_release_repository),
    preflight_run_repository: TrainingPreflightRunRepositoryPort = Depends(get_training_preflight_run_repository),
    image_feature_extraction_run_repository: ImageFeatureExtractionRunRepositoryPort = Depends(
        get_image_feature_extraction_run_repository
    ),
    image_feature_vector_repository: ImageFeatureVectorRepositoryPort = Depends(get_image_feature_vector_repository),
    dataset_split_item_repository: DatasetSplitItemRepositoryPort = Depends(get_dataset_split_item_repository),
    feature_matrix_builder: FeatureMatrixBuilder = Depends(get_feature_matrix_builder),
    trainer: ClassicalTabularBaselineTrainer = Depends(get_classical_tabular_baseline_trainer),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> CreateClassicalBaselineTrainingRunUseCase:
    return CreateClassicalBaselineTrainingRunUseCase(
        dataset_release_repository,
        preflight_run_repository,
        image_feature_extraction_run_repository,
        image_feature_vector_repository,
        dataset_split_item_repository,
        feature_matrix_builder,
        trainer,
        unit_of_work,
    )


def get_get_training_run_use_case(
    training_run_repository: TrainingRunRepositoryPort = Depends(get_training_run_repository),
) -> GetTrainingRunUseCase:
    return GetTrainingRunUseCase(training_run_repository)


def get_list_training_runs_use_case(
    training_run_repository: TrainingRunRepositoryPort = Depends(get_training_run_repository),
) -> ListTrainingRunsUseCase:
    return ListTrainingRunsUseCase(training_run_repository)


def get_list_training_predictions_use_case(
    training_run_repository: TrainingRunRepositoryPort = Depends(get_training_run_repository),
    training_prediction_repository: TrainingPredictionRepositoryPort = Depends(get_training_prediction_repository),
) -> ListTrainingPredictionsUseCase:
    return ListTrainingPredictionsUseCase(training_run_repository, training_prediction_repository)


def get_create_training_run_comparison_use_case(
    dataset_release_repository: DatasetReleaseRepositoryPort = Depends(get_dataset_release_repository),
    training_run_repository: TrainingRunRepositoryPort = Depends(get_training_run_repository),
    comparator: TrainingRunComparator = Depends(get_training_run_comparator),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> CreateTrainingRunComparisonUseCase:
    return CreateTrainingRunComparisonUseCase(
        dataset_release_repository,
        training_run_repository,
        comparator,
        unit_of_work,
    )


def get_get_training_run_comparison_use_case(
    comparison_repository: TrainingRunComparisonRepositoryPort = Depends(get_training_run_comparison_repository),
    entry_repository: TrainingRunComparisonEntryRepositoryPort = Depends(
        get_training_run_comparison_entry_repository
    ),
) -> GetTrainingRunComparisonUseCase:
    return GetTrainingRunComparisonUseCase(comparison_repository, entry_repository)


def get_list_training_run_comparisons_use_case(
    comparison_repository: TrainingRunComparisonRepositoryPort = Depends(get_training_run_comparison_repository),
    entry_repository: TrainingRunComparisonEntryRepositoryPort = Depends(
        get_training_run_comparison_entry_repository
    ),
    dataset_release_repository: DatasetReleaseRepositoryPort = Depends(get_dataset_release_repository),
) -> ListTrainingRunComparisonsUseCase:
    return ListTrainingRunComparisonsUseCase(comparison_repository, entry_repository, dataset_release_repository)


def get_list_training_run_comparison_entries_use_case(
    comparison_repository: TrainingRunComparisonRepositoryPort = Depends(get_training_run_comparison_repository),
    entry_repository: TrainingRunComparisonEntryRepositoryPort = Depends(
        get_training_run_comparison_entry_repository
    ),
) -> ListTrainingRunComparisonEntriesUseCase:
    return ListTrainingRunComparisonEntriesUseCase(comparison_repository, entry_repository)


def get_create_image_dataset_audit_run_use_case(
    manifest_exporter: DatasetReleaseManifestExporter = Depends(get_dataset_release_manifest_exporter),
    image_dataset_auditor: ImageDatasetAuditor = Depends(get_image_dataset_auditor),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> CreateImageDatasetAuditRunUseCase:
    return CreateImageDatasetAuditRunUseCase(manifest_exporter, image_dataset_auditor, unit_of_work)


def get_get_image_dataset_audit_run_use_case(
    audit_run_repository: ImageDatasetAuditRunRepositoryPort = Depends(get_image_dataset_audit_run_repository),
    audit_issue_repository: ImageDatasetAuditIssueRepositoryPort = Depends(get_image_dataset_audit_issue_repository),
) -> GetImageDatasetAuditRunUseCase:
    return GetImageDatasetAuditRunUseCase(audit_run_repository, audit_issue_repository)


def get_list_image_dataset_audit_runs_use_case(
    audit_run_repository: ImageDatasetAuditRunRepositoryPort = Depends(get_image_dataset_audit_run_repository),
    dataset_release_repository: DatasetReleaseRepositoryPort = Depends(get_dataset_release_repository),
) -> ListImageDatasetAuditRunsUseCase:
    return ListImageDatasetAuditRunsUseCase(audit_run_repository, dataset_release_repository)


def get_list_image_dataset_audit_issues_use_case(
    audit_run_repository: ImageDatasetAuditRunRepositoryPort = Depends(get_image_dataset_audit_run_repository),
    audit_issue_repository: ImageDatasetAuditIssueRepositoryPort = Depends(get_image_dataset_audit_issue_repository),
) -> ListImageDatasetAuditIssuesUseCase:
    return ListImageDatasetAuditIssuesUseCase(audit_run_repository, audit_issue_repository)


def get_create_image_feature_extraction_run_use_case(
    dataset_release_repository: DatasetReleaseRepositoryPort = Depends(get_dataset_release_repository),
    image_dataset_audit_run_repository: ImageDatasetAuditRunRepositoryPort = Depends(
        get_image_dataset_audit_run_repository
    ),
    manifest_exporter: DatasetReleaseManifestExporter = Depends(get_dataset_release_manifest_exporter),
    image_feature_extractor: ImageFeatureExtractor = Depends(get_image_feature_extractor),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> CreateImageFeatureExtractionRunUseCase:
    return CreateImageFeatureExtractionRunUseCase(
        dataset_release_repository,
        image_dataset_audit_run_repository,
        manifest_exporter,
        image_feature_extractor,
        unit_of_work,
    )


def get_get_image_feature_extraction_run_use_case(
    extraction_run_repository: ImageFeatureExtractionRunRepositoryPort = Depends(
        get_image_feature_extraction_run_repository
    ),
    feature_vector_repository: ImageFeatureVectorRepositoryPort = Depends(get_image_feature_vector_repository),
) -> GetImageFeatureExtractionRunUseCase:
    return GetImageFeatureExtractionRunUseCase(extraction_run_repository, feature_vector_repository)


def get_list_image_feature_extraction_runs_use_case(
    extraction_run_repository: ImageFeatureExtractionRunRepositoryPort = Depends(
        get_image_feature_extraction_run_repository
    ),
    dataset_release_repository: DatasetReleaseRepositoryPort = Depends(get_dataset_release_repository),
    image_dataset_audit_run_repository: ImageDatasetAuditRunRepositoryPort = Depends(
        get_image_dataset_audit_run_repository
    ),
) -> ListImageFeatureExtractionRunsUseCase:
    return ListImageFeatureExtractionRunsUseCase(
        extraction_run_repository, dataset_release_repository, image_dataset_audit_run_repository
    )


def get_list_image_feature_vectors_use_case(
    extraction_run_repository: ImageFeatureExtractionRunRepositoryPort = Depends(
        get_image_feature_extraction_run_repository
    ),
    feature_vector_repository: ImageFeatureVectorRepositoryPort = Depends(get_image_feature_vector_repository),
) -> ListImageFeatureVectorsUseCase:
    return ListImageFeatureVectorsUseCase(extraction_run_repository, feature_vector_repository)


def get_create_petri_segmentation_run_use_case(
    dataset_release_repository: DatasetReleaseRepositoryPort = Depends(get_dataset_release_repository),
    image_dataset_audit_run_repository: ImageDatasetAuditRunRepositoryPort = Depends(
        get_image_dataset_audit_run_repository
    ),
    manifest_exporter: DatasetReleaseManifestExporter = Depends(get_dataset_release_manifest_exporter),
    segmenter: ClassicalPetriSegmenter = Depends(get_classical_petri_segmenter),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> CreatePetriSegmentationRunUseCase:
    return CreatePetriSegmentationRunUseCase(
        dataset_release_repository,
        image_dataset_audit_run_repository,
        manifest_exporter,
        segmenter,
        unit_of_work,
    )


def get_get_petri_segmentation_run_use_case(
    run_repository: PetriSegmentationRunRepositoryPort = Depends(get_petri_segmentation_run_repository),
    region_repository: PetriSegmentationRegionRepositoryPort = Depends(get_petri_segmentation_region_repository),
) -> GetPetriSegmentationRunUseCase:
    return GetPetriSegmentationRunUseCase(run_repository, region_repository)


def get_list_petri_segmentation_runs_use_case(
    run_repository: PetriSegmentationRunRepositoryPort = Depends(get_petri_segmentation_run_repository),
) -> ListPetriSegmentationRunsUseCase:
    return ListPetriSegmentationRunsUseCase(run_repository)


def get_list_petri_segmentation_regions_use_case(
    run_repository: PetriSegmentationRunRepositoryPort = Depends(get_petri_segmentation_run_repository),
    region_repository: PetriSegmentationRegionRepositoryPort = Depends(get_petri_segmentation_region_repository),
) -> ListPetriSegmentationRegionsUseCase:
    return ListPetriSegmentationRegionsUseCase(run_repository, region_repository)


def get_submit_petri_region_review_use_case(
    region_repository: PetriSegmentationRegionRepositoryPort = Depends(get_petri_segmentation_region_repository),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> SubmitPetriRegionReviewUseCase:
    return SubmitPetriRegionReviewUseCase(region_repository, unit_of_work)


def get_get_petri_region_review_use_case(
    review_repository: PetriRegionReviewRepositoryPort = Depends(get_petri_region_review_repository),
) -> GetPetriRegionReviewUseCase:
    return GetPetriRegionReviewUseCase(review_repository)


def get_get_final_petri_region_review_use_case(
    region_repository: PetriSegmentationRegionRepositoryPort = Depends(get_petri_segmentation_region_repository),
    review_repository: PetriRegionReviewRepositoryPort = Depends(get_petri_region_review_repository),
) -> GetFinalPetriRegionReviewUseCase:
    return GetFinalPetriRegionReviewUseCase(region_repository, review_repository)


def get_list_petri_region_reviews_use_case(
    region_repository: PetriSegmentationRegionRepositoryPort = Depends(get_petri_segmentation_region_repository),
    segmentation_run_repository: PetriSegmentationRunRepositoryPort = Depends(get_petri_segmentation_run_repository),
    dataset_release_repository: DatasetReleaseRepositoryPort = Depends(get_dataset_release_repository),
    review_repository: PetriRegionReviewRepositoryPort = Depends(get_petri_region_review_repository),
) -> ListPetriRegionReviewsUseCase:
    return ListPetriRegionReviewsUseCase(
        region_repository, segmentation_run_repository, dataset_release_repository, review_repository
    )


def get_petri_reviewed_annotation_manifest_exporter(
    segmentation_run_repository: PetriSegmentationRunRepositoryPort = Depends(get_petri_segmentation_run_repository),
    region_repository: PetriSegmentationRegionRepositoryPort = Depends(get_petri_segmentation_region_repository),
    review_repository: PetriRegionReviewRepositoryPort = Depends(get_petri_region_review_repository),
) -> PetriReviewedAnnotationManifestExporter:
    return PetriReviewedAnnotationManifestExporter(segmentation_run_repository, region_repository, review_repository)


def get_create_petri_annotation_export_run_use_case(
    dataset_release_repository: DatasetReleaseRepositoryPort = Depends(get_dataset_release_repository),
    segmentation_run_repository: PetriSegmentationRunRepositoryPort = Depends(get_petri_segmentation_run_repository),
    region_repository: PetriSegmentationRegionRepositoryPort = Depends(get_petri_segmentation_region_repository),
    review_repository: PetriRegionReviewRepositoryPort = Depends(get_petri_region_review_repository),
    exporter: PetriAnnotationExporter = Depends(get_petri_annotation_exporter),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> CreatePetriAnnotationExportRunUseCase:
    return CreatePetriAnnotationExportRunUseCase(
        dataset_release_repository,
        segmentation_run_repository,
        region_repository,
        review_repository,
        exporter,
        unit_of_work,
    )


def get_get_petri_annotation_export_run_use_case(
    run_repository: PetriAnnotationExportRunRepositoryPort = Depends(get_petri_annotation_export_run_repository),
) -> GetPetriAnnotationExportRunUseCase:
    return GetPetriAnnotationExportRunUseCase(run_repository)


def get_list_petri_annotation_export_runs_use_case(
    run_repository: PetriAnnotationExportRunRepositoryPort = Depends(get_petri_annotation_export_run_repository),
) -> ListPetriAnnotationExportRunsUseCase:
    return ListPetriAnnotationExportRunsUseCase(run_repository)


def get_list_petri_annotation_export_items_use_case(
    run_repository: PetriAnnotationExportRunRepositoryPort = Depends(get_petri_annotation_export_run_repository),
    item_repository: PetriAnnotationExportItemRepositoryPort = Depends(get_petri_annotation_export_item_repository),
) -> ListPetriAnnotationExportItemsUseCase:
    return ListPetriAnnotationExportItemsUseCase(run_repository, item_repository)


def get_create_annotation_bundle_run_use_case(
    export_run_repository: PetriAnnotationExportRunRepositoryPort = Depends(get_petri_annotation_export_run_repository),
    export_item_repository: PetriAnnotationExportItemRepositoryPort = Depends(
        get_petri_annotation_export_item_repository
    ),
    validator: AnnotationBundleValidator = Depends(get_annotation_bundle_validator),
    writer: AnnotationBundleWriter = Depends(get_annotation_bundle_writer),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> CreateAnnotationBundleRunUseCase:
    return CreateAnnotationBundleRunUseCase(
        export_run_repository,
        export_item_repository,
        validator,
        writer,
        unit_of_work,
    )


def get_get_annotation_bundle_run_use_case(
    run_repository: AnnotationBundleRunRepositoryPort = Depends(get_annotation_bundle_run_repository),
) -> GetAnnotationBundleRunUseCase:
    return GetAnnotationBundleRunUseCase(run_repository)


def get_list_annotation_bundle_runs_use_case(
    run_repository: AnnotationBundleRunRepositoryPort = Depends(get_annotation_bundle_run_repository),
) -> ListAnnotationBundleRunsUseCase:
    return ListAnnotationBundleRunsUseCase(run_repository)


def get_list_annotation_bundle_files_use_case(
    run_repository: AnnotationBundleRunRepositoryPort = Depends(get_annotation_bundle_run_repository),
    file_repository: AnnotationBundleFileRepositoryPort = Depends(get_annotation_bundle_file_repository),
) -> ListAnnotationBundleFilesUseCase:
    return ListAnnotationBundleFilesUseCase(run_repository, file_repository)


def get_create_annotation_quality_gate_run_use_case(
    bundle_run_repository: AnnotationBundleRunRepositoryPort = Depends(get_annotation_bundle_run_repository),
    bundle_file_repository: AnnotationBundleFileRepositoryPort = Depends(get_annotation_bundle_file_repository),
    validator: AnnotationQualityGateValidator = Depends(get_annotation_quality_gate_validator),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> CreateAnnotationQualityGateRunUseCase:
    return CreateAnnotationQualityGateRunUseCase(
        bundle_run_repository,
        bundle_file_repository,
        validator,
        unit_of_work,
    )


def get_get_annotation_quality_gate_run_use_case(
    run_repository: AnnotationQualityGateRunRepositoryPort = Depends(get_annotation_quality_gate_run_repository),
) -> GetAnnotationQualityGateRunUseCase:
    return GetAnnotationQualityGateRunUseCase(run_repository)


def get_list_annotation_quality_gate_runs_use_case(
    run_repository: AnnotationQualityGateRunRepositoryPort = Depends(get_annotation_quality_gate_run_repository),
) -> ListAnnotationQualityGateRunsUseCase:
    return ListAnnotationQualityGateRunsUseCase(run_repository)


def get_list_annotation_quality_gate_issues_use_case(
    run_repository: AnnotationQualityGateRunRepositoryPort = Depends(get_annotation_quality_gate_run_repository),
    issue_repository: AnnotationQualityGateIssueRepositoryPort = Depends(
        get_annotation_quality_gate_issue_repository
    ),
) -> ListAnnotationQualityGateIssuesUseCase:
    return ListAnnotationQualityGateIssuesUseCase(run_repository, issue_repository)


def get_create_detection_training_run_use_case(
    bundle_run_repository: AnnotationBundleRunRepositoryPort = Depends(get_annotation_bundle_run_repository),
    bundle_file_repository: AnnotationBundleFileRepositoryPort = Depends(get_annotation_bundle_file_repository),
    quality_gate_run_repository: AnnotationQualityGateRunRepositoryPort = Depends(
        get_annotation_quality_gate_run_repository
    ),
    trainer: ObjectDetectionTrainerPort = Depends(get_yolo_dry_run_trainer),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> CreateDetectionTrainingRunUseCase:
    return CreateDetectionTrainingRunUseCase(
        bundle_run_repository,
        bundle_file_repository,
        quality_gate_run_repository,
        trainer,
        unit_of_work,
    )


def get_get_detection_training_run_use_case(
    run_repository: DetectionTrainingRunRepositoryPort = Depends(get_detection_training_run_repository),
) -> GetDetectionTrainingRunUseCase:
    return GetDetectionTrainingRunUseCase(run_repository)


def get_list_detection_training_runs_use_case(
    run_repository: DetectionTrainingRunRepositoryPort = Depends(get_detection_training_run_repository),
) -> ListDetectionTrainingRunsUseCase:
    return ListDetectionTrainingRunsUseCase(run_repository)


def get_create_detection_training_readiness_report_use_case(
    detection_training_run_repository: DetectionTrainingRunRepositoryPort = Depends(
        get_detection_training_run_repository
    ),
    detection_training_issue_repository: DetectionTrainingIssueRepositoryPort = Depends(
        get_detection_training_issue_repository
    ),
    bundle_run_repository: AnnotationBundleRunRepositoryPort = Depends(get_annotation_bundle_run_repository),
    bundle_file_repository: AnnotationBundleFileRepositoryPort = Depends(get_annotation_bundle_file_repository),
    quality_gate_run_repository: AnnotationQualityGateRunRepositoryPort = Depends(
        get_annotation_quality_gate_run_repository
    ),
    quality_gate_issue_repository: AnnotationQualityGateIssueRepositoryPort = Depends(
        get_annotation_quality_gate_issue_repository
    ),
    evaluator: DetectionTrainingReadinessEvaluator = Depends(get_detection_training_readiness_evaluator),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> CreateDetectionTrainingReadinessReportUseCase:
    return CreateDetectionTrainingReadinessReportUseCase(
        detection_training_run_repository,
        detection_training_issue_repository,
        bundle_run_repository,
        bundle_file_repository,
        quality_gate_run_repository,
        quality_gate_issue_repository,
        evaluator,
        unit_of_work,
    )


def get_get_detection_training_readiness_report_use_case(
    report_repository: DetectionTrainingReadinessReportRepositoryPort = Depends(
        get_detection_training_readiness_report_repository
    ),
) -> GetDetectionTrainingReadinessReportUseCase:
    return GetDetectionTrainingReadinessReportUseCase(report_repository)


def get_list_detection_training_readiness_reports_use_case(
    report_repository: DetectionTrainingReadinessReportRepositoryPort = Depends(
        get_detection_training_readiness_report_repository
    ),
) -> ListDetectionTrainingReadinessReportsUseCase:
    return ListDetectionTrainingReadinessReportsUseCase(report_repository)


def get_list_detection_training_readiness_issues_use_case(
    report_repository: DetectionTrainingReadinessReportRepositoryPort = Depends(
        get_detection_training_readiness_report_repository
    ),
    issue_repository: DetectionTrainingReadinessIssueRepositoryPort = Depends(
        get_detection_training_readiness_issue_repository
    ),
) -> ListDetectionTrainingReadinessIssuesUseCase:
    return ListDetectionTrainingReadinessIssuesUseCase(report_repository, issue_repository)


def get_create_detection_training_environment_spec_use_case(
    detection_training_run_repository: DetectionTrainingRunRepositoryPort = Depends(
        get_detection_training_run_repository
    ),
    readiness_report_repository: DetectionTrainingReadinessReportRepositoryPort = Depends(
        get_detection_training_readiness_report_repository
    ),
    bundle_run_repository: AnnotationBundleRunRepositoryPort = Depends(get_annotation_bundle_run_repository),
    bundle_file_repository: AnnotationBundleFileRepositoryPort = Depends(get_annotation_bundle_file_repository),
    evaluator: DetectionTrainingEnvironmentEvaluator = Depends(get_detection_training_environment_evaluator),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> CreateDetectionTrainingEnvironmentSpecUseCase:
    return CreateDetectionTrainingEnvironmentSpecUseCase(
        detection_training_run_repository,
        readiness_report_repository,
        bundle_run_repository,
        bundle_file_repository,
        evaluator,
        unit_of_work,
    )


def get_get_detection_training_environment_spec_use_case(
    spec_repository: DetectionTrainingEnvironmentSpecRepositoryPort = Depends(
        get_detection_training_environment_spec_repository
    ),
) -> GetDetectionTrainingEnvironmentSpecUseCase:
    return GetDetectionTrainingEnvironmentSpecUseCase(spec_repository)


def get_list_detection_training_environment_specs_use_case(
    spec_repository: DetectionTrainingEnvironmentSpecRepositoryPort = Depends(
        get_detection_training_environment_spec_repository
    ),
) -> ListDetectionTrainingEnvironmentSpecsUseCase:
    return ListDetectionTrainingEnvironmentSpecsUseCase(spec_repository)


def get_list_detection_training_environment_issues_use_case(
    spec_repository: DetectionTrainingEnvironmentSpecRepositoryPort = Depends(
        get_detection_training_environment_spec_repository
    ),
    issue_repository: DetectionTrainingEnvironmentIssueRepositoryPort = Depends(
        get_detection_training_environment_issue_repository
    ),
) -> ListDetectionTrainingEnvironmentIssuesUseCase:
    return ListDetectionTrainingEnvironmentIssuesUseCase(spec_repository, issue_repository)


def get_create_detection_training_artifact_policy_use_case(
    detection_training_run_repository: DetectionTrainingRunRepositoryPort = Depends(
        get_detection_training_run_repository
    ),
    readiness_report_repository: DetectionTrainingReadinessReportRepositoryPort = Depends(
        get_detection_training_readiness_report_repository
    ),
    environment_spec_repository: DetectionTrainingEnvironmentSpecRepositoryPort = Depends(
        get_detection_training_environment_spec_repository
    ),
    bundle_run_repository: AnnotationBundleRunRepositoryPort = Depends(get_annotation_bundle_run_repository),
    bundle_file_repository: AnnotationBundleFileRepositoryPort = Depends(get_annotation_bundle_file_repository),
    evaluator: DetectionTrainingArtifactPolicyEvaluator = Depends(get_detection_training_artifact_policy_evaluator),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> CreateDetectionTrainingArtifactPolicyUseCase:
    return CreateDetectionTrainingArtifactPolicyUseCase(
        detection_training_run_repository,
        readiness_report_repository,
        environment_spec_repository,
        bundle_run_repository,
        bundle_file_repository,
        evaluator,
        unit_of_work,
    )


def get_get_detection_training_artifact_policy_use_case(
    policy_repository: DetectionTrainingArtifactPolicyRepositoryPort = Depends(
        get_detection_training_artifact_policy_repository
    ),
) -> GetDetectionTrainingArtifactPolicyUseCase:
    return GetDetectionTrainingArtifactPolicyUseCase(policy_repository)


def get_list_detection_training_artifact_policies_use_case(
    policy_repository: DetectionTrainingArtifactPolicyRepositoryPort = Depends(
        get_detection_training_artifact_policy_repository
    ),
) -> ListDetectionTrainingArtifactPoliciesUseCase:
    return ListDetectionTrainingArtifactPoliciesUseCase(policy_repository)


def get_list_detection_training_artifact_records_use_case(
    policy_repository: DetectionTrainingArtifactPolicyRepositoryPort = Depends(
        get_detection_training_artifact_policy_repository
    ),
    record_repository: DetectionTrainingArtifactRecordRepositoryPort = Depends(
        get_detection_training_artifact_record_repository
    ),
) -> ListDetectionTrainingArtifactRecordsUseCase:
    return ListDetectionTrainingArtifactRecordsUseCase(policy_repository, record_repository)


def get_list_detection_training_artifact_issues_use_case(
    policy_repository: DetectionTrainingArtifactPolicyRepositoryPort = Depends(
        get_detection_training_artifact_policy_repository
    ),
    issue_repository: DetectionTrainingArtifactIssueRepositoryPort = Depends(
        get_detection_training_artifact_issue_repository
    ),
) -> ListDetectionTrainingArtifactIssuesUseCase:
    return ListDetectionTrainingArtifactIssuesUseCase(policy_repository, issue_repository)


def get_create_detection_training_execution_run_use_case(
    detection_training_run_repository: DetectionTrainingRunRepositoryPort = Depends(
        get_detection_training_run_repository
    ),
    readiness_report_repository: DetectionTrainingReadinessReportRepositoryPort = Depends(
        get_detection_training_readiness_report_repository
    ),
    environment_spec_repository: DetectionTrainingEnvironmentSpecRepositoryPort = Depends(
        get_detection_training_environment_spec_repository
    ),
    artifact_policy_repository: DetectionTrainingArtifactPolicyRepositoryPort = Depends(
        get_detection_training_artifact_policy_repository
    ),
    evaluator: DetectionTrainingExecutionGateEvaluator = Depends(get_detection_training_execution_gate_evaluator),
    scaffold: ManualYoloTrainingRunnerScaffold = Depends(get_manual_yolo_training_runner_scaffold),
    unit_of_work: UnitOfWorkPort = Depends(get_unit_of_work),
) -> CreateDetectionTrainingExecutionRunUseCase:
    return CreateDetectionTrainingExecutionRunUseCase(
        detection_training_run_repository,
        readiness_report_repository,
        environment_spec_repository,
        artifact_policy_repository,
        evaluator,
        scaffold,
        unit_of_work,
    )


def get_get_detection_training_execution_run_use_case(
    execution_run_repository: DetectionTrainingExecutionRunRepositoryPort = Depends(
        get_detection_training_execution_run_repository
    ),
) -> GetDetectionTrainingExecutionRunUseCase:
    return GetDetectionTrainingExecutionRunUseCase(execution_run_repository)


def get_list_detection_training_execution_runs_use_case(
    execution_run_repository: DetectionTrainingExecutionRunRepositoryPort = Depends(
        get_detection_training_execution_run_repository
    ),
) -> ListDetectionTrainingExecutionRunsUseCase:
    return ListDetectionTrainingExecutionRunsUseCase(execution_run_repository)


def get_list_detection_training_execution_issues_use_case(
    execution_run_repository: DetectionTrainingExecutionRunRepositoryPort = Depends(
        get_detection_training_execution_run_repository
    ),
    execution_issue_repository: DetectionTrainingExecutionIssueRepositoryPort = Depends(
        get_detection_training_execution_issue_repository
    ),
) -> ListDetectionTrainingExecutionIssuesUseCase:
    return ListDetectionTrainingExecutionIssuesUseCase(execution_run_repository, execution_issue_repository)


def get_list_detection_training_issues_use_case(
    run_repository: DetectionTrainingRunRepositoryPort = Depends(get_detection_training_run_repository),
    issue_repository: DetectionTrainingIssueRepositoryPort = Depends(get_detection_training_issue_repository),
) -> ListDetectionTrainingIssuesUseCase:
    return ListDetectionTrainingIssuesUseCase(run_repository, issue_repository)
